from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db
from models import Client
from forms import ClientForm
from sqlalchemy.exc import IntegrityError

from flask_login import login_required, current_user
from utils.auth import role_required

bp = Blueprint('clients', __name__)

@bp.route('/')
@login_required
@role_required(['client_admin', 'manager'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        clients = Client.query.filter(
            (Client.raison_sociale.ilike(search)) | 
            (Client.ville.ilike(search)) |
            (Client.email.ilike(search)) |
            (db.cast(Client.date_creation, db.String).ilike(search))
        ).order_by(Client.raison_sociale).all()
    else:
        clients = Client.query.order_by(Client.raison_sociale).all()
    return render_template('clients/index.html', clients=clients)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['client_admin', 'manager'])
def add():
    form = ClientForm()
    if form.validate_on_submit():
        client = Client()
        form.populate_obj(client)
        client.created_by_id = current_user.id
        client.updated_by_id = current_user.id
        # Ensure email is None if empty
        if not client.email:
            client.email = None
            
        db.session.add(client)
        try:
            db.session.commit()
            flash('Client ajouté avec succès.', 'success')
            return redirect(url_for('clients.index'))
        except IntegrityError:
            db.session.rollback()
            flash('Erreur : Un client avec cet email existe déjà.', 'danger')
            
    return render_template('clients/form.html', form=form, title="Nouveau Client")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['client_admin', 'manager'])
def edit(id):
    client = Client.query.get_or_404(id)
    form = ClientForm(obj=client)
    if form.validate_on_submit():
        form.populate_obj(client)
        client.updated_by_id = current_user.id
        client.updated_at = datetime.utcnow()
        # Ensure email is None if empty
        if not client.email:
            client.email = None
            
        try:
            db.session.commit()
            flash('Client modifié avec succès.', 'success')
            return redirect(url_for('clients.index'))
        except IntegrityError:
            db.session.rollback()
            flash('Erreur : Un client avec cet email existe déjà.', 'danger')
            
    return render_template('clients/form.html', form=form, title="Modifier Client")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['client_admin', 'manager'])
def delete(id):
    client = Client.query.get_or_404(id)
    
    # Check if client has documents
    if client.documents:
        flash(f"Impossible de supprimer le client '{client.raison_sociale}' car il possède des devis ou factures associés. Vous devez d'abord supprimer ses documents.", 'danger')
        return redirect(url_for('clients.index'))
    
    try:
        db.session.delete(client)
        db.session.commit()
        flash('Client supprimé.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression : {str(e)}', 'danger')
        
    return redirect(url_for('clients.index'))
