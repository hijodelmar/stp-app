import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
from extensions import db
from models import CompanyInfo, AISettings, User
from forms import CompanyInfoForm
from utils.auth import role_required

bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'settings'])
def index():
    return redirect(url_for('settings.company'))

@bp.route('/company', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'settings'])
def company():
    info = CompanyInfo.query.first()
    if not info:
        info = CompanyInfo(nom="STP Gestion", adresse="", cp="", ville="", ville_signature="")
        db.session.add(info)
        db.session.commit()
    
    form = CompanyInfoForm(obj=info)
    
    if form.validate_on_submit():
        form.populate_obj(info)
        if form.logo.data:
            f = form.logo.data
            filename = secure_filename(f.filename)
            ext = os.path.splitext(filename)[1]
            new_filename = f"logo{ext}"
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads')
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            f.save(os.path.join(upload_path, new_filename))
            info.logo_path = f'uploads/{new_filename}'
        
        db.session.commit()
        flash('Paramètres société mis à jour.', 'success')
        return redirect(url_for('settings.company'))

    return render_template('settings/company.html', form=form, info=info, active_page='company')

@bp.route('/ai', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'settings'])
def ai():
    ai_settings = AISettings.get_settings()
    
    if request.method == 'POST' and 'ai_settings_submit' in request.form:
        ai_settings.enabled = 'enabled' in request.form
        ai_settings.provider = request.form.get('provider')
        ai_settings.api_key = request.form.get('api_key')
        ai_settings.model_name = request.form.get('model_name')
        db.session.commit()
        flash('Paramètres de l\'assistant mis à jour.', 'success')
        return redirect(url_for('settings.ai'))
        
    return render_template('settings/ai.html', ai_settings=ai_settings, active_page='ai')

@bp.route('/backups', methods=['GET'])
@login_required
@role_required(['admin'])
def backups():
    from services.backup_service import BackupService
    backup_service = BackupService(current_app)
    
    # Filter & Pagination Params
    page = request.args.get('page', 1, type=int)
    per_page = 30
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Get all matching backups
    all_backups = backup_service.list_backups(start_date=start_date, end_date=end_date)
    
    # Calculate Pagination
    total = len(all_backups)
    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    
    # Slice for current page
    backups = all_backups[start:end]
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages
    }

    backup_schedule = backup_service.get_schedule_config()
    next_run_time = backup_service.get_next_run_time()
    
    return render_template('settings/backups.html', 
                           backups=backups, 
                           backup_schedule=backup_schedule, 
                           next_run_time=next_run_time,
                           pagination=pagination,
                           filters={'start_date': start_date, 'end_date': end_date},
                           active_page='backups')

@bp.route('/security', methods=['GET'])
@login_required
@role_required(['admin', 'user_admin'])
def security():
    return render_template('settings/security.html', active_page='security')

@bp.route('/users', methods=['GET'])
@login_required
@role_required(['admin', 'user_admin'])
def users():
    users = User.query.all()
    return render_template('settings/users.html', users=users, active_page='users')


@bp.route('/template_editor')
@login_required
@role_required(['admin', 'settings'])
def template_editor():
    template_path = os.path.join(current_app.root_path, 'templates', 'pdf_template.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return render_template('template_editor.html', content=content)

@bp.route('/template_preview', methods=['POST'])
@login_required
@role_required(['admin', 'settings'])
def template_preview():
    html_content = request.form.get('content')
    from services.mock_data import get_mock_document
    doc = get_mock_document()
    info = CompanyInfo.query.first()
    from flask import render_template_string
    try:
        return render_template_string(html_content, document=doc, info=info)
    except Exception as e:
        return f"<div style='color:red;'><h2>Erreur</h2><pre>{str(e)}</pre></div>"

@bp.route('/save_template', methods=['POST'])
@login_required
@role_required(['admin', 'settings'])
def save_template():
    content = request.form.get('content')
    if not content:
        flash('Contenu vide.', 'danger')
        return redirect(url_for('settings.template_editor'))
    template_path = os.path.join(current_app.root_path, 'templates', 'pdf_template.html')
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)
    flash('Template sauvegardé avec succès.', 'success')
    return redirect(url_for('settings.template_editor'))

# --- Backup Routes ---
@bp.route('/backups/create', methods=['POST'])
@login_required
@role_required(['admin'])
def create_backup():
    from services.backup_service import BackupService
    service = BackupService(current_app)
    try:
        filename = service.create_backup(description="manual")
        flash(f'Sauvegarde créée avec succès: {filename}', 'success')
    except Exception as e:
        flash(f'Erreur lors de la création de la sauvegarde: {str(e)}', 'danger')
    return redirect(url_for('settings.backups'))

@bp.route('/backups/restore/<filename>', methods=['POST'])
@login_required
@role_required(['admin'])
def restore_backup(filename):
    from services.backup_service import BackupService
    service = BackupService(current_app)
    try:
        service.restore_backup(filename)
        flash(f'Base de données restaurée depuis {filename}.', 'success')
    except Exception as e:
        flash(f'Erreur lors de la restauration: {str(e)}', 'danger')
    return redirect(url_for('settings.backups'))

@bp.route('/backups/delete/<filename>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_backup(filename):
    from services.backup_service import BackupService
    service = BackupService(current_app)
    try:
        service.delete_backup(filename)
        flash(f'Sauvegarde supprimée: {filename}', 'success')
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    return redirect(url_for('settings.backups'))

@bp.route('/backups/schedule', methods=['POST'])
@login_required
@role_required(['admin'])
def schedule_backup():
    from services.backup_service import BackupService
    service = BackupService(current_app)
    
    enabled = 'enabled' in request.form
    start_date = request.form.get('start_date', '')
    try:
        hour = int(request.form.get('hour', 2))
        minute = int(request.form.get('minute', 0))
    except ValueError:
        hour = 2
        minute = 0
    
    try:
        service.set_schedule_config(enabled, hour=hour, minute=minute, start_date=start_date)
        status = "activée" if enabled else "désactivée"
        flash(f'Planification {status} (tous les jours à {hour:02d}h{minute:02d}).', 'success')


    except Exception as e:
        flash(f'Erreur lors de la configuration: {str(e)}', 'danger')
        
    return redirect(url_for('settings.backups'))

