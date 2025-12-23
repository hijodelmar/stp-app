from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db
from models import Client, ClientContact
from forms import ClientForm
from sqlalchemy.exc import IntegrityError
from flask_login import login_required, current_user
from utils.auth import role_required

bp = Blueprint('clients', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'manager', 'client_admin'])
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
@role_required(['admin', 'manager', 'client_admin'])
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
            
            # Traitement des contacts
            process_contacts(client)
            db.session.commit()
            
            flash('Client ajouté avec succès.', 'success')
            return redirect(url_for('clients.index'))
        except IntegrityError:
            db.session.rollback()
            flash('Erreur : Un client avec cet email existe déjà.', 'danger')
            
    return render_template('clients/form.html', form=form, title="Nouveau Client")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'client_admin'])
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
            # Traitement des contacts
            process_contacts(client)
            
            db.session.commit()
            flash('Client modifié avec succès.', 'success')
            return redirect(url_for('clients.index'))
        except IntegrityError:
            db.session.rollback()
            flash('Erreur : Un client avec cet email existe déjà.', 'danger')
            
    return render_template('clients/form.html', form=form, title="Modifier Client", contacts=client.contacts)

def process_contacts(client):
    # Récupérer tous les champs du formulaire qui commencent par 'contacts-'
    # Format: contacts-INDEX-FIELD
    # On va regrouper par index
    contacts_data = {}
    
    for key, value in request.form.items():
        if key.startswith('contacts-'):
            parts = key.split('-')
            if len(parts) >= 3:
                index = parts[1]
                field = parts[2]
                if index not in contacts_data:
                    contacts_data[index] = {}
                contacts_data[index][field] = value.strip()

    # Liste des IDs actuels pour suppression si absents
    existing_ids = [c.id for c in client.contacts]
    processed_ids = []

    for index, data in contacts_data.items():
        c_id = data.get('id')
        nom = data.get('nom')
        
        if not nom: # Ignorer entrées vides
            continue
            
        if c_id == 'new':
            # Création
            new_contact = ClientContact(
                client=client,
                nom=nom,
                email=data.get('email') or None,
                telephone=data.get('telephone') or None,
                fonction=data.get('fonction') or None
            )
            db.session.add(new_contact)
        else:
            # Mise à jour
            try:
                c_id_int = int(c_id)
                contact = ClientContact.query.get(c_id_int)
                if contact and contact.client_id == client.id:
                    contact.nom = nom
                    contact.email = data.get('email') or None
                    contact.telephone = data.get('telephone') or None
                    contact.fonction = data.get('fonction') or None
                    processed_ids.append(c_id_int)
            except ValueError:
                pass
    
    # Suppression des contacts qui ne sont plus dans le formulaire
    for old_contact in client.contacts:
        if old_contact.id not in processed_ids and old_contact.id in existing_ids:
            db.session.delete(old_contact)

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'client_admin'])
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

@bp.route('/api/client/<int:client_id>/contacts')
@login_required
def get_contacts(client_id):
    client = Client.query.get_or_404(client_id)
    contacts = [{'id': c.id, 'nom': c.nom, 'email': c.email} for c in client.contacts]
    return {'contacts': contacts}
