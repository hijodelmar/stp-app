from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db
from models import Client
from forms import ClientForm
from sqlalchemy.exc import IntegrityError

bp = Blueprint('clients', __name__)

@bp.route('/')
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
def add():
    form = ClientForm()
    if form.validate_on_submit():
        # Convert empty strings to None for email to avoid unique constraint violation
        email = form.email.data if form.email.data else None
        
        client = Client(
            raison_sociale=form.raison_sociale.data,
            adresse=form.adresse.data,
            code_postal=form.code_postal.data,
            ville=form.ville.data,
            telephone=form.telephone.data,
            email=email,
            siret=form.siret.data,
            tva_intra=form.tva_intra.data
        )
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
def edit(id):
    client = Client.query.get_or_404(id)
    form = ClientForm(obj=client)
    if form.validate_on_submit():
        form.populate_obj(client)
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
def delete(id):
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    flash('Client supprimé.', 'info')
    return redirect(url_for('clients.index'))
