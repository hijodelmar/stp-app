from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from extensions import db
from models import Document, LigneDocument, Client, CompanyInfo, ClientContact

from forms import DocumentForm
from flask_login import login_required, current_user
from utils.auth import role_required
from utils.document import generate_document_number

bp = Blueprint('factures', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'manager', 'reporting', 'facture_admin'])
def index():
    q = request.args.get('q')
    if q:
        from sqlalchemy.orm import aliased
        SourceDocument = aliased(Document)
        search = f"%{q}%"
        documents = Document.query.join(Client).outerjoin(SourceDocument, Document.source_document_id == SourceDocument.id).filter(
            (Document.type == 'facture') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (SourceDocument.numero.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.updated_at.desc()).all()
    else:
        documents = Document.query.filter_by(type='facture').order_by(Document.updated_at.desc()).all()
    return render_template('factures/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def add():
    form = DocumentForm()
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if form.validate_on_submit():
        if not form.client_reference.data:
            flash("La référence client est obligatoire pour une facture.", "danger")
            return render_template('factures/form.html', form=form, title="Nouvelle Facture")

        year = datetime.now().year
        numero = generate_document_number('F', year)

        document = Document(
            type='facture',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            client_id=form.client_id.data,
            autoliquidation=form.autoliquidation.data,
            tva_rate=form.tva_rate.data,
            paid=form.paid.data,
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
        flash(f'Facture {numero} créée avec succès.', 'success')
        return redirect(url_for('factures.index'))
    
    if not form.date.data:
        form.date.data = datetime.now().strftime('%Y-%m-%d')
        
    # Default TVA from Company Settings
    if request.method == 'GET' and not form.tva_rate.data:
        info = CompanyInfo.query.first()
        if info:
            form.tva_rate.data = info.tva_default
        
    if form.errors:
        flash(f"Erreur de validation: {form.errors}", 'danger')

    return render_template('factures/form.html', form=form, title="Nouvelle Facture")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def edit(id):
    document = Document.query.get_or_404(id)
    if document.type != 'facture':
        flash('Document invalide.', 'danger')
        return redirect(url_for('factures.index'))

    form = DocumentForm(obj=document)
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if request.method == 'GET':
        if document.date:
            form.date.data = document.date.strftime('%Y-%m-%d')
        
        # Manually populate CC contacts with IDs for the form
        if document.cc_contacts:
            form.cc_contacts.data = [c.id for c in document.cc_contacts]

    if form.validate_on_submit():
        if not form.client_reference.data:
            flash("La référence client est obligatoire pour une facture.", "danger")
            return render_template('factures/form.html', form=form, title=f"Modifier Facture {document.numero}")

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
        
        # Accounting validation: cannot mark as paid if an avoir exists
        if form.paid.data and document.generated_documents:
             flash(f"Impossible de marquer la facture {document.numero} comme payée car elle fait l'objet d'un avoir.", "warning")
             document.paid = False # Force to false
        else:
             document.paid = form.paid.data
             
        document.client_reference = form.client_reference.data
        document.chantier_reference = form.chantier_reference.data
        document.updated_by_id = current_user.id
        document.updated_at = datetime.utcnow()
        
        document.lignes = []
        
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
        
        db.session.commit()
        flash(f'Facture {document.numero} modifiée avec succès.', 'success')
        return redirect(url_for('factures.index'))

    if form.errors:
        flash(f"Erreur de validation: {form.errors}", 'danger')

    return render_template('factures/form.html', form=form, title=f"Modifier Facture {document.numero}")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def delete(id):
    document = Document.query.get_or_404(id)
    if document.type != 'facture':
        abort(403)
        
    # Check if an avoir was generated from this facture
    if document.generated_documents and not current_user.has_role('admin'):
        flash(f"Impossible de supprimer la facture {document.numero} car un avoir y est lié.", 'danger')
        return redirect(url_for('factures.index'))

    # Check if invoice is paid or sent
    if document.paid and not current_user.has_role('admin'):
        flash(f"Impossible de supprimer la facture {document.numero} car elle est marquée comme réglée.", 'danger')
        return redirect(url_for('factures.index'))
        
    if document.sent_at and not current_user.has_role('admin'):
        flash(f"Impossible de supprimer la facture {document.numero} car elle a déjà été envoyée au client.", 'danger')
        return redirect(url_for('factures.index'))
        
    db.session.delete(document)
    db.session.commit()
    flash('Facture supprimée.', 'info')
    return redirect(url_for('factures.index'))

@bp.route('/toggle_paid/<int:id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def toggle_paid(id):
    """Toggle payment status via AJAX"""
    document = Document.query.get_or_404(id)
    if document.type != 'facture':
        return jsonify({'success': False, 'error': 'Document invalide'}), 400
    
    # Check if invoice has an avoir
    if document.generated_documents:
        return jsonify({'success': False, 'error': 'Impossible de modifier le statut : cette facture est liée à un avoir.'}), 400
    
    # Toggle the paid status
    document.paid = not document.paid
    db.session.commit()
    
    return jsonify({
        'success': True,
        'paid': document.paid,
        'message': f'Facture marquée comme {"réglée" if document.paid else "non réglée"}'
    })


@bp.route('/convert/choose')
def choose_devis():
    # Subquery to identify converted devis (source_document_id for existing invoices)
    converted_devis_query = db.session.query(Document.source_document_id).filter(
        Document.type == 'facture',
        Document.source_document_id != None
    )
    
    # Base query: Devis that are NOT in the converted list
    query = Document.query.filter(
        Document.type == 'devis',
        ~Document.id.in_(converted_devis_query)
    )

    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        query = query.join(Client).filter(
            (Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search))
        )
        
    devis_list = query.order_by(Document.date.desc()).all()
        
    return render_template('factures/choose_devis.html', documents=devis_list)

@bp.route('/convert/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def convert_from_devis(id):
    try:
        devis = Document.query.get_or_404(id)
        if devis.type != 'devis':
             flash('Document non valide pour conversion.', 'danger')
             return redirect(url_for('devis.index'))
        
        # Smart Regeneration Logic:
        # Check if an invoice already exists and if the Devis has been modified since then
        latest_facture = Document.query.filter_by(type='facture', source_document_id=id).order_by(Document.created_at.desc()).first()
        
        if latest_facture:
            # If the Devis hasn't been modified since the latest invoice, block regeneration
            # Handle None values for timestamps just in case
            devis_updated = devis.updated_at or datetime.min
            facture_created = latest_facture.created_at or datetime.min
            
            if devis_updated <= facture_created:
                flash(f'Ce devis a déjà été converti en facture (N° {latest_facture.numero}). Modifiez le devis pour pouvoir générer une nouvelle facture.', 'warning')
                return redirect(url_for('devis.index'))
            else:
                if request.method == 'GET':
                     flash(f'Note: Une facture existe déjà (N° {latest_facture.numero}), mais le devis a été modifié depuis. Vous générez une nouvelle version.', 'info')
        
        if request.method == 'GET':
            # Show form to enter client reference
            from forms import DocumentForm
            form = DocumentForm()
            form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]
            return render_template('factures/convert_form.html', form=form, devis=devis, title="Convertir Devis en Facture")
        
        # POST: Process the conversion
        # Get client reference from form
        client_reference = request.form.get('client_reference')
        if not client_reference:
            flash('La référence client est obligatoire pour générer une facture.', 'danger')
            return redirect(url_for('factures.convert_from_devis', id=id))
             
        # --- NEW: Cleanup old invoices to avoid duplicates ---
        old_invoices = Document.query.filter_by(type='facture', source_document_id=id).all()
        if old_invoices:
            import os
            for old_inv in old_invoices:
                # Skip deletion if the invoice is locked (Paid, Sent, or Linked to Avoir)
                if old_inv.paid or old_inv.sent_at or old_inv.generated_documents:
                    continue
    
                # Delete associated PDF file if it exists
                if old_inv.pdf_path and os.path.exists(old_inv.pdf_path):
                    try:
                        os.remove(old_inv.pdf_path)
                    except Exception as e:
                        print(f"Could not delete old PDF {old_inv.pdf_path}: {e}")
                db.session.delete(old_inv)
            db.session.commit()
        # ---------------------------------------------------
             
        year = datetime.now().year
        from utils.document import generate_document_number
        numero = generate_document_number('F', year)
        
        facture = Document(
            type='facture',
            numero=numero,
            date=datetime.now(),
            client_id=devis.client_id,
            autoliquidation=devis.autoliquidation,
            montant_ht=devis.montant_ht,
            tva_rate=devis.tva_rate if devis.tva_rate else 20.0,
            tva=devis.tva,
            montant_ttc=devis.montant_ttc,
            source_document_id=devis.id,
            client_reference=client_reference,
            chantier_reference=devis.chantier_reference,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        # Copy contacts from devis
        # if devis.contact_id:
        #     facture.contact_id = devis.contact_id
        
        if devis.cc_contacts:
            facture.cc_contacts = list(devis.cc_contacts)
    
        # Clone lines
        for ligne in devis.lignes:
            new_ligne = LigneDocument(
                designation=ligne.designation,
                quantite=ligne.quantite,
                prix_unitaire=ligne.prix_unitaire,
                total_ligne=ligne.total_ligne,
                category=ligne.category
            )
            facture.lignes.append(new_ligne)
        
        db.session.add(facture)
        db.session.commit()
        flash(f'Devis converti en Facture {numero}.', 'success')
        return redirect(url_for('factures.index'))

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Erreur interne lors de la conversion: {str(e)}", 'danger')
        return redirect(url_for('devis.index'))
