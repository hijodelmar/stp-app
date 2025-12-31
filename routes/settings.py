import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
from extensions import db
from models import CompanyInfo, AISettings
from forms import CompanyInfoForm
from utils.auth import role_required

bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'settings'])
def index():
    info = CompanyInfo.query.first()
    if not info:
        info = CompanyInfo(nom="STP Gestion", adresse="", cp="", ville="", ville_signature="")
        db.session.add(info)
        db.session.commit()
    
    ai_settings = AISettings.get_settings()
    form = CompanyInfoForm(obj=info)
    
    if request.method == 'POST':
        # Handle AI Settings (they come from raw form, not WTForms object)
        if 'ai_settings_submit' in request.form:
            ai_settings.enabled = 'enabled' in request.form
            ai_settings.provider = request.form.get('provider')
            ai_settings.api_key = request.form.get('api_key')
            ai_settings.model_name = request.form.get('model_name')
            db.session.commit()
            flash('Paramètres de l\'assistant mis à jour.', 'success')
            return redirect(url_for('settings.index', tab='ai'))

        # Handle Company Info (WTForms)
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
            return redirect(url_for('settings.index'))

    return render_template('settings.html', form=form, info=info, ai_settings=ai_settings)

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
