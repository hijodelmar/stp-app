from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from models import User, Role
from extensions import db
from utils.auth import role_required

bp = Blueprint('users', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'user_admin'])
def index():
    # Redirect to the consolidated settings page
    return redirect(url_for('settings.index', tab='user_management'))

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'user_admin'])
def add():
    roles = Role.query.all()
    if request.method == 'POST':
        username = request.form.get('username').lower()
        password = request.form.get('password')
        role_ids = request.form.getlist('roles')
        
        if User.query.filter_by(username=username).first():
            flash('Cet identifiant existe déjà.', 'danger')
        else:
            user = User(username=username)
            user.set_password(password)
            
            # Attribuer les rôles
            if role_ids:
                selected_roles = Role.query.filter(Role.id.in_(role_ids)).all()
                user.roles = selected_roles
            
            db.session.add(user)
            db.session.commit()
            flash(f'Utilisateur {username} créé avec succès.', 'success')
            return redirect(url_for('users.index'))
            
    return render_template('users/form.html', title="Nouvel Utilisateur", all_roles=roles)

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'user_admin'])
def edit(id):
    user = User.query.get_or_404(id)
    all_roles = Role.query.all()
    if request.method == 'POST':
        user.username = request.form.get('username').lower()
        role_ids = request.form.getlist('roles')
        
        # Mettre à jour les rôles
        if role_ids:
            selected_roles = Role.query.filter(Role.id.in_(role_ids)).all()
            user.roles = selected_roles
        else:
            user.roles = []
            
        password = request.form.get('password')
        if password:
            user.set_password(password)
            
        db.session.commit()
        flash(f'Utilisateur {user.username} mis à jour.', 'success')
        return redirect(url_for('users.index'))
        
    return render_template('users/form.html', user=user, title=f"Modifier {user.username}", all_roles=all_roles)

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
