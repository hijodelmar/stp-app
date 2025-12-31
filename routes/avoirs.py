from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db
from models import Document, LigneDocument, Client, CompanyInfo, ClientContact

from forms import DocumentForm
from flask_login import login_required, current_user
from utils.auth import role_required
from utils.document import generate_document_number

bp = Blueprint('avoirs', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'manager', 'reporting', 'facture_admin'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        documents = Document.query.join(Client).filter(
            (Document.type == 'avoir') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.updated_at.desc()).all()
    else:
        documents = Document.query.filter_by(type='avoir').order_by(Document.updated_at.desc()).all()
    return render_template('avoirs/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def add():
    # Typically avoirs are created from invoices, but standalone creation is possible
    form = DocumentForm()
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if form.validate_on_submit():
        year = datetime.now().year
        numero = generate_document_number('A', year)

        document = Document(
            type='avoir',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            client_id=form.client_id.data,
            autoliquidation=form.autoliquidation.data,
            tva_rate=form.tva_rate.data,
            client_reference=form.client_reference.data,
            chantier_reference=form.chantier_reference.data,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )

        # Handle optional Primary Contact - REMOVED
        # if form.contact_id.data:
        #     document.contact_id = form.contact_id.data

        # Handle CC Contacts
        if form.cc_contacts.data:
            cc_ids = form.cc_contacts.data
            if cc_ids:
                contacts = ClientContact.query.filter(ClientContact.id.in_(cc_ids)).all()
                document.cc_contacts = contacts
        
        total_ht = 0
        for ligne_form in form.lignes:
            l = LigneDocument(
                designation=ligne_form.designation.data,
                quantite=ligne_form.quantite.data,
                prix_unitaire=ligne_form.prix_unitaire.data,
                total_ligne=ligne_form.quantite.data * ligne_form.prix_unitaire.data,
                category=ligne_form.category.data
            )
            total_ht += l.total_ligne
            document.lignes.append(l)
        
        document.montant_ht = total_ht
        if document.autoliquidation:
            document.tva = 0
        else:
            document.tva = total_ht * (document.tva_rate / 100)
        document.montant_ttc = document.montant_ht + document.tva
        
        db.session.add(document)
        db.session.commit()
        flash(f'Avoir {numero} créé avec succès.', 'success')
        return redirect(url_for('avoirs.index'))
    
    if not form.date.data:
        form.date.data = datetime.now().strftime('%Y-%m-%d')
        
    # Default TVA from Company Settings
    if request.method == 'GET' and not form.tva_rate.data:
        info = CompanyInfo.query.first()
        if info:
            form.tva_rate.data = info.tva_default
        
    return render_template('factures/form.html', form=form, title="Nouvel Avoir")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def edit(id):
    document = Document.query.get_or_404(id)
    if document.type != 'avoir':
        flash('Document invalide.', 'danger')
        return redirect(url_for('avoirs.index'))

    # RESTRICTION: Only allow editing the Date for existing Avoirs
    # We essentially treat everything else as read-only in the view logic
    # But the form.populate_obj typically overrides everything.
    # So we must NOT use populate_obj blindly or we reset fields.
    
    form = DocumentForm(obj=document)
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if request.method == 'GET':
        if document.date:
            form.date.data = document.date.strftime('%Y-%m-%d')

        # Manually populate CC contacts with IDs for the form
        if document.cc_contacts:
            form.cc_contacts.data = [c.id for c in document.cc_contacts]

    if form.validate_on_submit():
        # ONLY UPDATE THE DATE
        document.date = datetime.strptime(form.date.data, '%Y-%m-%d')
        
        # Explicitly ignore other fields from form submission to enforce "ReadOnly" logic
        # Client, Refs, Rows, etc. remain unchanged.
        
        document.updated_by_id = current_user.id
        document.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Avoir {document.numero} mis à jour (Date uniquement).', 'success')
        return redirect(url_for('avoirs.index'))

    return render_template('factures/form.html', form=form, title=f"Modifier Avoir {document.numero}")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def delete(id):
    document = Document.query.get_or_404(id)
    if document.type != 'avoir':
        abort(403)
        
    db.session.delete(document)
    db.session.commit()
    flash('Avoir supprimé.', 'info')
    return redirect(url_for('avoirs.index'))

@bp.route('/convert/choose')
def choose_facture():
    # Subquery to identify converted factures (source_document_id for existing avoirs)
    converted_factures_query = db.session.query(Document.source_document_id).filter(
        Document.type == 'avoir',
        Document.source_document_id != None
    )

    # Base query: Factures that are NOT in the converted list and NOT paid
    query = Document.query.filter(
        Document.type == 'facture',
        Document.paid == False,
        ~Document.id.in_(converted_factures_query)
    )

    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        # Filter: Invoice (Facture), Not Paid
        query = query.join(Client).filter(
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        )
        
    factures_list = query.order_by(Document.date.desc()).all()
        
    return render_template('avoirs/choose_facture.html', documents=factures_list)

@bp.route('/convert/<int:id>')
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def convert_from_facture(id):
    facture = Document.query.get_or_404(id)
    if facture.type != 'facture':
         flash('Document non valide pour conversion.', 'danger')
         return redirect(url_for('factures.index'))
    
    # RESTRICTION CHECK
    if facture.paid:
        flash(f"Impossible de créer un avoir pour la facture {facture.numero} car elle est déjà payée.", "danger")
        return redirect(url_for('factures.index'))
    
    # Check if an avoir already exists for this facture
    existing_avoir = Document.query.filter_by(type='avoir', source_document_id=id).first()
    if existing_avoir:
        flash(f'Un avoir existe déjà pour cette facture (N° {existing_avoir.numero}).', 'warning')
        return redirect(url_for('avoirs.index'))
         
    year = datetime.now().year
    count = Document.query.filter(Document.numero.like(f'A-{year}-%')).count()
    numero = f'A-{year}-{count + 1:04d}'
    
    avoir = Document(
        type='avoir',
        numero=numero,
        date=datetime.now(),
        client_id=facture.client_id,
        autoliquidation=facture.autoliquidation,
        montant_ht=facture.montant_ht,
        tva_rate=facture.tva_rate if facture.tva_rate else 20.0,
        tva=facture.tva,
        montant_ttc=facture.montant_ttc,
        source_document_id=facture.id,
        client_reference=facture.client_reference,
        chantier_reference=facture.chantier_reference,
        created_by_id=current_user.id,
        updated_by_id=current_user.id
    )

    # Copy contacts from facture
    # if facture.contact_id:
    #     avoir.contact_id = facture.contact_id
    
    if facture.cc_contacts:
        avoir.cc_contacts = list(facture.cc_contacts)
    
    # Clone lines
    for ligne in facture.lignes:
        new_ligne = LigneDocument(
             designation=ligne.designation,
             quantite=ligne.quantite,
             prix_unitaire=ligne.prix_unitaire,
             total_ligne=ligne.total_ligne,
             category=ligne.category
        )
        avoir.lignes.append(new_ligne)
    
    db.session.add(avoir)
    db.session.commit()
    flash(f'Facture convertie en Avoir {numero}.', 'success')
    return redirect(url_for('avoirs.index'))
