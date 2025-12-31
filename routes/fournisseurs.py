from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from extensions import db
from models import Supplier
from forms import SupplierForm
from flask_login import login_required, current_user
from utils.auth import role_required

bp = Blueprint('fournisseurs', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'manager', 'facture_admin', 'supplier_admin'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        suppliers = Supplier.query.filter(
            (Supplier.raison_sociale.ilike(search)) |
            (Supplier.ville.ilike(search)) |
            (Supplier.email.ilike(search))
        ).order_by(Supplier.raison_sociale.asc()).all()
    else:
        suppliers = Supplier.query.order_by(Supplier.raison_sociale.asc()).all()
    return render_template('fournisseurs/index.html', suppliers=suppliers)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin', 'supplier_admin'])
def add():
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            raison_sociale=form.raison_sociale.data,
            adresse=form.adresse.data,
            code_postal=form.code_postal.data,
            ville=form.ville.data,
            telephone=form.telephone.data,
            email=form.email.data,
            siret=form.siret.data,
            tva_intra=form.tva_intra.data,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        db.session.add(supplier)
        db.session.commit()
        flash('Fournisseur ajouté avec succès.', 'success')
        return redirect(url_for('fournisseurs.index'))
    return render_template('fournisseurs/form.html', form=form, title="Nouveau Fournisseur")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'facture_admin', 'supplier_admin'])
def edit(id):
    supplier = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supplier)
    if form.validate_on_submit():
        form.populate_obj(supplier)
        supplier.updated_by_id = current_user.id
        db.session.commit()
        flash('Fournisseur mis à jour avec succès.', 'success')
        return redirect(url_for('fournisseurs.index'))
    return render_template('fournisseurs/form.html', form=form, title=f"Modifier {supplier.raison_sociale}")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin', 'supplier_admin'])
def delete(id):
    supplier = Supplier.query.get_or_404(id)
    # Check if supplier has associated documents
    if supplier.documents:
        flash('Impossible de supprimer un fournisseur qui a des documents associés.', 'danger')
        return redirect(url_for('fournisseurs.index'))
    
    db.session.delete(supplier)
    db.session.commit()
    flash('Fournisseur supprimé avec succès.', 'success')
    return redirect(url_for('fournisseurs.index'))
