from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db
from models import Document, LigneDocument, Client
from forms import DocumentForm

from flask_login import login_required, current_user
from utils.auth import role_required

bp = Blueprint('avoirs', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'manager', 'reporting', 'avoir_admin'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        documents = Document.query.join(Client).filter(
            (Document.type == 'avoir') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        documents = Document.query.filter_by(type='avoir').order_by(Document.date.desc()).all()
    return render_template('avoirs/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'avoir_admin'])
def add():
    form = DocumentForm()
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if form.validate_on_submit():
        if not form.client_reference.data:
            flash("La référence client est obligatoire pour un avoir.", "danger")
            return render_template('factures/form.html', form=form, title="Nouvel Avoir")

        year = datetime.now().year
        count = Document.query.filter(Document.numero.like(f'A-{year}-%')).count()
        numero = f'A-{year}-{count + 1:04d}'

        document = Document(
            type='avoir',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            client_id=form.client_id.data,
            autoliquidation=form.autoliquidation.data,
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
        flash(f'Avoir {numero} créé avec succès.', 'success')
        return redirect(url_for('avoirs.index'))
    
    if not form.date.data:
        form.date.data = datetime.now().strftime('%Y-%m-%d')
        
    return render_template('factures/form.html', form=form, title="Nouvel Avoir")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'avoir_admin'])
def edit(id):
    document = Document.query.get_or_404(id)
    if document.type != 'avoir':
        flash('Document invalide.', 'danger')
        return redirect(url_for('avoirs.index'))

    form = DocumentForm(obj=document)
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if request.method == 'GET':
        if document.date:
            form.date.data = document.date.strftime('%Y-%m-%d')

    if form.validate_on_submit():
        # Supprimer l'ancien PDF car le document va être modifié
        from services.pdf_generator import delete_old_pdf
        delete_old_pdf(document)
        
        # RESTRICTION AVOIR : On ne modifie QUE la date
        document.date = datetime.strptime(form.date.data, '%Y-%m-%d')
        
        # Les autres champs sont ignorés/commentés
        # document.client_id = form.client_id.data
        # document.autoliquidation = form.autoliquidation.data
        # document.client_reference = form.client_reference.data
        # document.chantier_reference = form.chantier_reference.data
        
        document.updated_by_id = current_user.id
        document.updated_at = datetime.utcnow()
        
        # Pas de mise à jour des lignes ni recalcule des montants
        
        db.session.commit()
        flash(f'Avoir {document.numero} modifié avec succès (Date uniquement).', 'success')
        return redirect(url_for('avoirs.index'))

    return render_template('factures/form.html', form=form, title=f"Modifier Avoir {document.numero}")


@bp.route('/convert/choose')
def choose_facture():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        facture_list = Document.query.join(Client).filter(
            (Document.type == 'facture') &
            (Document.paid == False) & # FILTRE RESTRICTION
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        # FILTRE RESTRICTION
        facture_list = Document.query.filter_by(type='facture', paid=False).order_by(Document.date.desc()).all()
        
    return render_template('avoirs/choose_facture.html', documents=facture_list)

@bp.route('/convert/<int:id>')
@login_required
@role_required(['admin', 'manager', 'avoir_admin'])
def convert_from_facture(id):
    facture = Document.query.get_or_404(id)
    if facture.type != 'facture':
         flash('Document non valide pour conversion.', 'danger')
         return redirect(url_for('factures.index'))
    
    # SECURITE ANTI-FRAUDE : Pas d'avoir sur une facture payée
    if facture.paid:
         flash("Impossible de créer un avoir sur une facture réglée.", "danger")
         return redirect(url_for('factures.index'))
         
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
        tva=facture.tva,
        montant_ttc=facture.montant_ttc,
        source_document_id=facture.id,
        client_reference=facture.client_reference,
        chantier_reference=facture.chantier_reference,
        created_by_id=current_user.id,
        updated_by_id=current_user.id
    )
    
    # Clone lines
    for ligne in facture.lignes:
        new_ligne = LigneDocument(
             designation=ligne.designation,
             quantite=ligne.quantite,
             prix_unitaire=ligne.prix_unitaire,
             total_ligne=ligne.total_ligne
        )
        avoir.lignes.append(new_ligne)
    
    db.session.add(avoir)
    db.session.commit()
    flash(f'Facture convertie en Avoir {numero}.', 'success')
    return redirect(url_for('avoirs.index'))

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'avoir_admin'])
def delete(id):
    document = Document.query.get_or_404(id)
    if document.type != 'avoir':
        flash('Opération non autorisée.', 'danger')
        return redirect(url_for('avoirs.index'))
        
    db.session.delete(document)
    db.session.commit()
    flash('Avoir supprimé.', 'info')
    return redirect(url_for('avoirs.index'))
