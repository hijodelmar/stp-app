from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from extensions import db
from models import Document, LigneDocument, Client, CompanyInfo, ClientContact

from forms import DocumentForm
from flask_login import login_required, current_user
from utils.auth import role_required
from utils.document import generate_document_number

bp = Blueprint('devis', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'manager', 'reporting', 'devis_admin'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        documents = Document.query.join(Client).filter(
            (Document.type == 'devis') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.updated_at.desc()).all()
    else:
        documents = Document.query.filter_by(type='devis').order_by(Document.updated_at.desc()).all()
    return render_template('devis/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'devis_admin'])
def add():
    form = DocumentForm()
    # Populate client choices
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if form.validate_on_submit():
        year = datetime.now().year
        numero = generate_document_number('D', year)

        document = Document(
            type='devis',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            client_id=form.client_id.data,
            autoliquidation=form.autoliquidation.data,
            tva_rate=form.tva_rate.data,
            client_reference=form.client_reference.data,
            chantier_reference=form.chantier_reference.data,
            validity_duration=form.validity_duration.data,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        # Handle optional Primary Contact - REMOVED
        # if form.contact_id.data:
        #    document.contact_id = form.contact_id.data

        # Handle CC Contacts
        if form.cc_contacts.data:
            # form.cc_contacts.data is already a list of ints because coerce=int
            cc_ids = form.cc_contacts.data
            if cc_ids:
                contacts = ClientContact.query.filter(ClientContact.id.in_(cc_ids)).all()
                document.cc_contacts = contacts
        
        # Calcul des totaux et ajout des lignes
        total_ht = 0
        for ligne_form in form.lignes:
            # Handle None values
            qte = ligne_form.quantite.data if ligne_form.quantite.data is not None else 0.0
            prix = ligne_form.prix_unitaire.data if ligne_form.prix_unitaire.data is not None else 0.0
            
            l = LigneDocument(
                designation=ligne_form.designation.data,
                quantite=qte,
                prix_unitaire=prix,
                total_ligne=qte * prix,
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
        flash(f'Devis {numero} créé avec succès.', 'success')
        return redirect(url_for('devis.index'))
    
    # Default date today
    if not form.date.data:
        form.date.data = datetime.now().strftime('%Y-%m-%d')
        
    # Default TVA from Company Settings
    if request.method == 'GET' and not form.tva_rate.data:
        info = CompanyInfo.query.first()
        if info:
            form.tva_rate.data = info.tva_default
    
    if form.errors:
        flash(f"Erreur de validation: {form.errors}", 'danger')

    return render_template('devis/form.html', form=form, title="Nouveau Devis")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'devis_admin'])
def edit(id):
    document = Document.query.get_or_404(id)
    if document.type != 'devis':
        flash('Document invalide.', 'danger')
        return redirect(url_for('devis.index'))

    form = DocumentForm(obj=document)
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if request.method == 'GET':
        # Pre-populate date correctly (string format for date input)
        if document.date:
            form.date.data = document.date.strftime('%Y-%m-%d')
        
        # Manually populate CC contacts with IDs for the form
        if document.cc_contacts:
            form.cc_contacts.data = [c.id for c in document.cc_contacts]

    if form.validate_on_submit():
        # Supprimer l'ancien PDF car le document va être modifié
        from services.pdf_generator import delete_old_pdf
        delete_old_pdf(document)
        
        document.client_id = form.client_id.data
        
        # Handle optional Primary Contact - REMOVED
        # document.contact_id = form.contact_id.data if form.contact_id.data else None

        # Handle CC Contacts
        document.cc_contacts = [] # Clear old associations
        if form.cc_contacts.data:
            cc_ids = form.cc_contacts.data
            if cc_ids:
                contacts = ClientContact.query.filter(ClientContact.id.in_(cc_ids)).all()
                document.cc_contacts = contacts
        document.date = datetime.strptime(form.date.data, '%Y-%m-%d')
        document.autoliquidation = form.autoliquidation.data
        document.tva_rate = form.tva_rate.data
        document.client_reference = form.client_reference.data
        document.chantier_reference = form.chantier_reference.data
        document.validity_duration = form.validity_duration.data
        document.updated_by_id = current_user.id
        document.updated_at = datetime.utcnow()
        
        # Update lines: Clear old ones and add new ones
        document.lignes = [] 
        
        total_ht = 0
        for ligne_form in form.lignes:
            # Handle None values
            qte = ligne_form.quantite.data if ligne_form.quantite.data is not None else 0.0
            prix = ligne_form.prix_unitaire.data if ligne_form.prix_unitaire.data is not None else 0.0
            
            l = LigneDocument(
                designation=ligne_form.designation.data,
                quantite=qte,
                prix_unitaire=prix,
                total_ligne=qte * prix,
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
        
        db.session.commit()
        flash(f'Devis {document.numero} modifié avec succès.', 'success')
        return redirect(url_for('devis.index'))

    if form.errors:
        flash(f"Erreur de validation: {form.errors}", 'danger')

    return render_template('devis/form.html', form=form, title=f"Modifier Devis {document.numero}")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'devis_admin'])
def delete(id):
    document = Document.query.get_or_404(id)
    if document.type != 'devis':
        abort(403)
        
    # Check if a facture was generated from this devis
    if document.generated_documents:
        flash(f"Impossible de supprimer le devis {document.numero} car une facture ou un avoir y est lié.", 'danger')
        return redirect(url_for('devis.index'))
        
    db.session.delete(document)
    db.session.commit()
    flash('Devis supprimé.', 'info')
    return redirect(url_for('devis.index'))

@bp.route('/duplicate/<int:id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'devis_admin'])
def duplicate(id):
    source = Document.query.get_or_404(id)
    if source.type != 'devis':
        abort(403)
        
    year = datetime.now().year
    numero = generate_document_number('D', year)
    
    # Create new document copying data from source
    new_devis = Document(
        type='devis',
        numero=numero,
        date=datetime.now(),
        client_id=source.client_id,
        autoliquidation=source.autoliquidation,
        tva_rate=source.tva_rate,
        montant_ht=source.montant_ht,
        tva=source.tva,
        montant_ttc=source.montant_ttc,
        client_reference=source.client_reference,
        chantier_reference=source.chantier_reference,
        validity_duration=source.validity_duration,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        # contact_id=source.contact_id # Removed primary contact logic as per previous sesssions
    )
    
    # Clone CC contacts
    if source.cc_contacts:
        new_devis.cc_contacts = list(source.cc_contacts)
        
    # Clone lines
    for ligne in source.lignes:
        new_ligne = LigneDocument(
            designation=ligne.designation,
            quantite=ligne.quantite,
            prix_unitaire=ligne.prix_unitaire,
            total_ligne=ligne.total_ligne,
            category=ligne.category
        )
        new_devis.lignes.append(new_ligne)
        
    db.session.add(new_devis)
    db.session.commit()
    
    flash(f'Devis {source.numero} dupliqué vers {numero}. Vous pouvez maintenant le modifier.', 'success')
    return redirect(url_for('devis.edit', id=new_devis.id))
