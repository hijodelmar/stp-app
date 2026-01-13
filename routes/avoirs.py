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
        # Alias for the source document (Facture) to enable searching by its number
        SourceDoc = db.aliased(Document)
        
        documents = Document.query.join(Client).outerjoin(SourceDoc, Document.source_document).filter(
            (Document.type == 'avoir') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)) |
            (SourceDoc.numero.ilike(search)))
        ).order_by(Document.updated_at.desc()).all()
    else:
        documents = Document.query.filter_by(type='avoir').order_by(Document.updated_at.desc()).all()
    return render_template('avoirs/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def add():
    # Enforce creation from existing invoice
    flash("Pour créer un avoir, veuillez sélectionner la facture correspondante.", "info")
    return redirect(url_for('avoirs.choose_facture'))

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def edit(id):
    document = Document.query.get_or_404(id)
    if document.type != 'avoir':
        flash('Document invalide.', 'danger')
        return redirect(url_for('avoirs.index'))

    # RESTRICTION: Cannot edit if sent OR if linked to a source document (Facture)
    if document.sent_at:
        flash(f"Impossible de modifier l'avoir {document.numero} car il a déjà été envoyé au client.", 'danger')
        return redirect(url_for('avoirs.index'))
        
    if document.source_document_id:
        flash(f"Impossible de modifier l'avoir {document.numero} car il a été généré depuis une facture.", 'danger')
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
        # Supprimer l'ancien PDF pour régénération
        from services.pdf_generator import delete_old_pdf
        delete_old_pdf(document)

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
@role_required(['admin'])
def delete(id):
    document = Document.query.get_or_404(id)
    if document.type != 'avoir':
        abort(403)
        
    # RESTRICTION: Cannot delete if sent
    if document.sent_at and not current_user.has_role('admin'):
        flash(f"Impossible de supprimer l'avoir {document.numero} car il a déjà été envoyé au client.", 'danger')
        return redirect(url_for('avoirs.index'))
        
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
