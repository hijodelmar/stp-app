from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db
from models import Document, LigneDocument, Client
from forms import DocumentForm

from flask_login import login_required, current_user
from utils.auth import role_required

bp = Blueprint('devis', __name__)

@bp.route('/')
@login_required
@role_required(['devis_admin', 'manager'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        documents = Document.query.join(Client).filter(
            (Document.type == 'devis') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        documents = Document.query.filter_by(type='devis').order_by(Document.date.desc()).all()
    return render_template('devis/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['devis_admin', 'manager'])
def add():
    form = DocumentForm()
    # Populate client choices
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if form.validate_on_submit():
        # Génération numéro (Logique simple pour l'instant: D-{YYYY}-{Count+1})
        year = datetime.now().year
        count = Document.query.filter(Document.numero.like(f'D-{year}-%')).count()
        numero = f'D-{year}-{count + 1:04d}'

        document = Document(
            type='devis',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            client_id=form.client_id.data,
            autoliquidation=form.autoliquidation.data,
            client_reference=form.client_reference.data,
            chantier_reference=form.chantier_reference.data,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        # Calcul des totaux et ajout des lignes
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
        flash(f'Devis {numero} créé avec succès.', 'success')
        return redirect(url_for('devis.index'))
    
    # Default date today
    if not form.date.data:
        form.date.data = datetime.now().strftime('%Y-%m-%d')

    return render_template('devis/form.html', form=form, title="Nouveau Devis")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['devis_admin', 'manager'])
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

    if form.validate_on_submit():
        # Supprimer l'ancien PDF car le document va être modifié
        from services.pdf_generator import delete_old_pdf
        delete_old_pdf(document)
        
        document.client_id = form.client_id.data
        document.date = datetime.strptime(form.date.data, '%Y-%m-%d')
        document.autoliquidation = form.autoliquidation.data
        document.client_reference = form.client_reference.data
        document.chantier_reference = form.chantier_reference.data
        document.updated_by_id = current_user.id
        document.updated_at = datetime.utcnow()
        
        # Update lines: Clear old ones and add new ones
        # Because cascading delete-orphan is on, removing them from list should work, 
        # but explicit delete is safer to avoid issues.
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
        
        # Reset PDF path to trigger regeneration if needed
        # document.pdf_path = None 
        # Or keep it, user can regenerate manually. Better to keep it but maybe warn?
        # Let's keep it simple.
        
        db.session.commit()
        flash(f'Devis {document.numero} modifié avec succès.', 'success')
        return redirect(url_for('devis.index'))

    return render_template('devis/form.html', form=form, title=f"Modifier Devis {document.numero}")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['devis_admin', 'manager'])
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
