from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from models import User
from extensions import db
from utils.auth import role_required

bp = Blueprint('users', __name__)

@bp.route('/')
@login_required
@role_required(['admin'])
def index():
    users = User.query.all()
    return render_template('users/index.html', users=users)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def add():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(username=username).first():
            flash('Cet identifiant existe déjà.', 'danger')
        else:
            user = User(username=username, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'Utilisateur {username} créé avec succès.', 'success')
            return redirect(url_for('users.index'))
            
    return render_template('users/form.html', title="Nouvel Utilisateur")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.role = request.form.get('role')
        
        password = request.form.get('password')
        if password:
            user.set_password(password)
            
        db.session.commit()
        flash(f'Utilisateur {user.username} mis à jour.', 'success')
        return redirect(url_for('users.index'))
        
    return render_template('users/form.html', user=user, title=f"Modifier {user.username}")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
    else:
        try:
            db.session.delete(user)
            db.session.commit()
            flash('Utilisateur supprimé.', 'info')
        except Exception:
            db.session.rollback()
            flash("Impossible de supprimer cet utilisateur car il est lié à des enregistrements historiques (Audit).", 'danger')
    return redirect(url_for('users.index'))
