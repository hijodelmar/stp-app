from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
import uuid
from datetime import datetime, timedelta
from extensions import db
from models import User
from werkzeug.security import check_password_hash

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').lower()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # Check if user is already logged in (active in the last 5 minutes)
            five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
            if user.last_active and user.last_active >= five_mins_ago and user.current_session_id:
                # Store user id in session temporarily to handle force login
                session['temp_user_id'] = user.id
                return render_template('auth/force_login.html', username=user.username)
            
            # Normal login
            new_sid = str(uuid.uuid4())
            user.current_session_id = new_sid
            user.last_active = datetime.utcnow()
            db.session.commit()
            
            session['sid'] = new_sid
            session['login_at'] = datetime.utcnow() # Track connection time
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        
        flash('Identifiant ou mot de passe incorrect.', 'danger')
        
    return render_template('auth/login.html')

@bp.route('/force-login', methods=['POST'])
def force_login():
    user_id = session.get('temp_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    if user:
        new_sid = str(uuid.uuid4())
        user.current_session_id = new_sid
        user.last_active = datetime.utcnow()
        db.session.commit()
        
        session.pop('temp_user_id', None)
        session['sid'] = new_sid
        login_user(user)
        flash("Vous avez forcé la déconnexion de l'autre session.", "info")
        return redirect(url_for('index'))
    
    return redirect(url_for('auth.login'))

@bp.route('/logout')
@login_required
def logout():
    # Clear session tracking in DB
    current_user.current_session_id = None
    current_user.last_active = None
    db.session.commit()
    
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/active_users')
@login_required
def active_users():
    # Only admin can view functionality
    if not current_user.has_role('admin'):
        flash("Accès refusé.", "danger")
        return redirect(url_for('index'))
        
    # Users active in the last 5 minutes (Real-time view)
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    
    # Filter users who are active AND not ejected after their last activity
    # (Though logic should clear last_active, this is double safety)
    users = User.query.filter(User.last_active >= cutoff).all()
    
    # Post-filter to remove any zombies that might remain (optional but safe)
    valid_users = []
    for u in users:
        # If user has a force_logout_at that is NEWER than their last_active, they are effectively offline
        if u.force_logout_at and u.last_active and u.force_logout_at > u.last_active:
            continue
        valid_users.append(u)
    
    return render_template('auth/active_users.html', users=valid_users, now=datetime.utcnow())

@bp.route('/eject_user/<int:user_id>', methods=['POST'])
@login_required
def eject_user(user_id):
    if not current_user.has_role('admin'):
        flash("Accès refusé.", "danger")
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Vous ne pouvez pas vous éjecter vous-même.", "warning")
        return redirect(url_for('auth.active_users'))
        
    # Invalidate their session by timestamp
    user.force_logout_at = datetime.utcnow()
    user.last_active = None # Remove from active list immediately check
    user.current_session_id = None
    db.session.commit()
    
    flash(f"L'utilisateur {user.username} a été déconnecté.", "success")
    return redirect(url_for('auth.active_users'))
