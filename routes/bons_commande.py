from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from extensions import db
from models import Document, LigneDocument, Supplier, CompanyInfo
from forms import BonCommandeForm
from flask_login import login_required, current_user
from utils.auth import role_required
from utils.document import generate_document_number

bp = Blueprint('bons_commande', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'manager', 'reporting', 'facture_admin'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        documents = Document.query.join(Supplier).filter(
            (Document.type == 'bon_de_commande') &
            ((Document.numero.ilike(search)) |
            (Supplier.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        documents = Document.query.filter_by(type='bon_de_commande').order_by(Document.date.desc()).all()
    return render_template('bons_commande/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def add():
    form = BonCommandeForm()
    form.supplier_id.choices = [(s.id, s.raison_sociale) for s in Supplier.query.order_by(Supplier.raison_sociale).all()]

    if form.validate_on_submit():
        year = datetime.now().year
        numero = generate_document_number('C', year)

        document = Document(
            type='bon_de_commande',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            supplier_id=form.supplier_id.data,
            autoliquidation=form.autoliquidation.data,
            tva_rate=form.tva_rate.data,
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
        flash(f'Bon de commande {numero} créé avec succès.', 'success')
        return redirect(url_for('bons_commande.index'))
    
    if not form.date.data:
        form.date.data = datetime.now().strftime('%Y-%m-%d')
        
    # Default TVA from Company Settings
    if request.method == 'GET' and not form.tva_rate.data:
        info = CompanyInfo.query.first()
        if info:
            form.tva_rate.data = info.tva_default
        
    return render_template('bons_commande/form.html', form=form, title="Nouveau Bon de Commande")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin'])
def edit(id):
    document = Document.query.get_or_404(id)
    if document.type != 'bon_de_commande':
        abort(403)
        
    form = BonCommandeForm(obj=document)
    form.supplier_id.choices = [(s.id, s.raison_sociale) for s in Supplier.query.order_by(Supplier.raison_sociale).all()]

    if request.method == 'GET':
        form.date.data = document.date.strftime('%Y-%m-%d')

    if form.validate_on_submit():
        document.date = datetime.strptime(form.date.data, '%Y-%m-%d')
        document.supplier_id = form.supplier_id.data
        document.autoliquidation = form.autoliquidation.data
        document.tva_rate = form.tva_rate.data
        document.client_reference = form.client_reference.data
        document.chantier_reference = form.chantier_reference.data
        document.updated_by_id = current_user.id
        
        # Update lines
        # Clear existing lines
        for ligne in document.lignes:
            db.session.delete(ligne)
        
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
        flash(f'Bon de commande {document.numero} mis à jour.', 'success')
        return redirect(url_for('bons_commande.index'))
        
    return render_template('bons_commande/form.html', form=form, title=f"Modifier {document.numero}")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete(id):
    document = Document.query.get_or_404(id)
    if document.type != 'bon_de_commande':
        abort(403)
    db.session.delete(document)
    db.session.commit()
    flash('Bon de commande supprimé.', 'success')
    return redirect(url_for('bons_commande.index'))
