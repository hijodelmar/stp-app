from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db
from models import Document, LigneDocument, Client
from forms import DocumentForm

from flask_login import login_required, current_user
from utils.auth import role_required

bp = Blueprint('factures', __name__)

@bp.route('/')
@login_required
@role_required(['facture_admin', 'manager'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        documents = Document.query.join(Client).filter(
            (Document.type == 'facture') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        documents = Document.query.filter_by(type='facture').order_by(Document.date.desc()).all()
    return render_template('factures/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['facture_admin', 'manager'])
def add():
    # Similar logic to Devis but generates 'facture' type and F- number
    form = DocumentForm()
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if form.validate_on_submit():
        year = datetime.now().year
        count = Document.query.filter(Document.numero.like(f'F-{year}-%')).count()
        numero = f'F-{year}-{count + 1:04d}'

        document = Document(
            type='facture',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            client_id=form.client_id.data,
            autoliquidation=form.autoliquidation.data,
            paid=form.paid.data,
            client_reference=form.client_reference.data,
            chantier_reference=form.chantier_reference.data,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        total_ht = 0
        for ligne_form in form.lignes:
            l = LigneDocument(
                designation=ligne_form.designation.data,
                quantite=ligne_form.quantite.data,
                prix_unitaire=ligne_form.prix_unitaire.data,
                total_ligne=ligne_form.quantite.data * ligne_form.prix_unitaire.data
            )
            total_ht += l.total_ligne
            document.lignes.append(l)
        
        document.montant_ht = total_ht
        if document.autoliquidation:
            document.tva = 0
        else:
            document.tva = total_ht * 0.20
        document.montant_ttc = document.montant_ht + document.tva
        
        db.session.add(document)
        db.session.commit()
        flash(f'Facture {numero} créée avec succès.', 'success')
        return redirect(url_for('factures.index'))
    
    if not form.date.data:
        form.date.data = datetime.now().strftime('%Y-%m-%d')
        
    return render_template('factures/form.html', form=form, title="Nouvelle Facture")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['facture_admin', 'manager'])
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

    if form.validate_on_submit():
        # Supprimer l'ancien PDF car le document va être modifié
        from services.pdf_generator import delete_old_pdf
        delete_old_pdf(document)
        
        document.client_id = form.client_id.data
        document.date = datetime.strptime(form.date.data, '%Y-%m-%d')
        document.autoliquidation = form.autoliquidation.data
        
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
                total_ligne=ligne_form.quantite.data * ligne_form.prix_unitaire.data
            )
            total_ht += l.total_ligne
            document.lignes.append(l)
        
        document.montant_ht = total_ht
        if document.autoliquidation:
            document.tva = 0
        else:
            document.tva = total_ht * 0.20
        document.montant_ttc = document.montant_ht + document.tva
        
        db.session.commit()
        flash(f'Facture {document.numero} modifiée avec succès.', 'success')
        return redirect(url_for('factures.index'))

    return render_template('factures/form.html', form=form, title=f"Modifier Facture {document.numero}")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['facture_admin', 'manager'])
def delete(id):
    document = Document.query.get_or_404(id)
    if document.type != 'facture':
        abort(403)
        
    # Check if an avoir was generated from this facture
    if document.generated_documents:
        flash(f"Impossible de supprimer la facture {document.numero} car un avoir y est lié.", 'danger')
        return redirect(url_for('factures.index'))
        
    db.session.delete(document)
    db.session.commit()
    flash('Facture supprimée.', 'info')
    return redirect(url_for('factures.index'))
    
    # If there are files (PDFs), we could delete them here too, but for safety/archiving we keep them.
    # To delete:
    # if document.pdf_path and os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], document.pdf_path)):
    #    os.remove(...)
    db.session.delete(document)
    db.session.commit()
    flash('Facture supprimée.', 'info')
    return redirect(url_for('factures.index'))

@bp.route('/toggle_paid/<int:id>', methods=['POST'])
def toggle_paid(id):
    """Toggle payment status via AJAX"""
    from flask import jsonify
    document = Document.query.get_or_404(id)
    if document.type != 'facture':
        return jsonify({'success': False, 'error': 'Document invalide'}), 400
    
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
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        # Même logique de recherche que pour l'index devis
        devis_list = Document.query.join(Client).filter(
            (Document.type == 'devis') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        devis_list = Document.query.filter_by(type='devis').order_by(Document.date.desc()).all()
        
    return render_template('factures/choose_devis.html', documents=devis_list)

@bp.route('/convert/<int:id>')
@login_required
@role_required(['facture_admin', 'manager'])
def convert_from_devis(id):
    devis = Document.query.get_or_404(id)
    if devis.type != 'devis':
         flash('Document non valide pour conversion.', 'danger')
         return redirect(url_for('devis.index'))
         
    year = datetime.now().year
    count = Document.query.filter(Document.numero.like(f'F-{year}-%')).count()
    numero = f'F-{year}-{count + 1:04d}'
    
    facture = Document(
        type='facture',
        numero=numero,
        date=datetime.now(),
        client_id=devis.client_id,
        autoliquidation=devis.autoliquidation,
        montant_ht=devis.montant_ht,
        tva=devis.tva,
        montant_ttc=devis.montant_ttc,
        source_document_id=devis.id,
        client_reference=devis.client_reference,
        chantier_reference=devis.chantier_reference,
        created_by_id=current_user.id,
        updated_by_id=current_user.id
    )
    
    # Clone lines
    for ligne in devis.lignes:
        new_ligne = LigneDocument(
             designation=ligne.designation,
             quantite=ligne.quantite,
             prix_unitaire=ligne.prix_unitaire,
             total_ligne=ligne.total_ligne
        )
        facture.lignes.append(new_ligne)
    
    db.session.add(facture)
    db.session.commit()
    flash(f'Devis converti en Facture {numero}.', 'success')
    return redirect(url_for('factures.index'))
