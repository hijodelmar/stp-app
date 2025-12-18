import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from werkzeug.utils import secure_filename
from extensions import db
from models import CompanyInfo
from forms import CompanyInfoForm

from flask_login import login_required
from utils.auth import role_required

bp = Blueprint('settings', __name__)

@bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required(['manager'])
def index():
    info = CompanyInfo.query.first()
    if not info:
        # Should create defaults if missing (migration script does it, but safety check)
        info = CompanyInfo(nom="My Company")
        db.session.add(info)
        db.session.commit()
    
    form = CompanyInfoForm(obj=info)
    
    if form.validate_on_submit():
        form.populate_obj(info)
        
        # Handle Logo Upload
        if form.logo.data:
            f = form.logo.data
            filename = secure_filename(f.filename)
            # Use a fixed name or reliable unique name, or just keep filename. 
            # Fixed name 'logo.png' overrides previous logo easily.
            ext = os.path.splitext(filename)[1]
            new_filename = f"logo{ext}"
            
            # Save to static/uploads
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads')
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
                
            file_path = os.path.join(upload_path, new_filename)
            f.save(file_path)
            
            # Save relative path for browser usage: 'uploads/logo.png'
            info.logo_path = f'uploads/{new_filename}'
        
        db.session.commit()
        flash('Paramètres mis à jour avec succès.', 'success')
        return redirect(url_for('settings.index'))

    return render_template('settings.html', form=form, info=info)

@bp.route('/template_editor')
@login_required
@role_required(['manager'])
def template_editor():
    # Read current template content
    template_path = os.path.join(current_app.root_path, 'templates', 'pdf_template.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return render_template('template_editor.html', content=content)

@bp.route('/template_preview', methods=['POST'])
def template_preview():
    # Get HTML from request
    html_content = request.form.get('content')
    
    # Create Mock Data
    from services.mock_data import get_mock_document
    doc = get_mock_document()
    
    # Get Company Info
    info = CompanyInfo.query.first()
    
    # Render with Jinja 'from_string' to safely render the submitted template string with context
    # WARNING: This is a security risk in public apps (Server Side Template Injection), 
    # but acceptable here for local admin tool as requested by user.
    from flask import render_template_string
    try:
        rendered_html = render_template_string(html_content, document=doc, info=info)
        return rendered_html
    except Exception as e:
        return f"<div style='color:red;'><h2>Erreur de Template</h2><pre>{str(e)}</pre></div>"

@bp.route('/save_template', methods=['POST'])
def save_template():
    content = request.form.get('content')
    if not content:
        flash('Contenu vide.', 'danger')
        return redirect(url_for('settings.template_editor'))
        
    template_path = os.path.join(current_app.root_path, 'templates', 'pdf_template.html')
    # Backup first? Maybe later.
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    flash('Template sauvegardé avec succès.', 'success')
    return redirect(url_for('settings.template_editor'))
