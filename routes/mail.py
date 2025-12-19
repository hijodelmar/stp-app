from flask import Blueprint, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Document, CompanyInfo
from services.mail_service import send_email_with_attachment
from services.pdf_generator import generate_pdf_bytes
import os

bp = Blueprint('mail', __name__)

@bp.route('/send_document/<int:id>', methods=['POST'])
@login_required
def send_document(id):
    doc = Document.query.get_or_404(id)
    
    # Check permissions based on document type
    required_roles = ['admin', 'manager']
    if doc.type == 'devis':
        required_roles.append('devis_admin')
    elif doc.type == 'facture':
        required_roles.append('facture_admin')
    elif doc.type == 'avoir':
        required_roles.append('avoir_admin')
    
    if not current_user.has_any_role(required_roles):
        from flask import abort
        return abort(403)

    info = CompanyInfo.query.first()
    
    if not doc.client.email:
        flash(f"Le client {doc.client.raison_sociale} n'a pas d'adresse email enregistrée.", "danger")
        return redirect(request.referrer or url_for('index'))

    if not info or not info.smtp_server:
        flash("Veuillez configurer vos paramètres SMTP dans les Paramètres avant d'envoyer un email.", "warning")
        return redirect(url_for('settings.index'))

    try:
        # 1. Générer le PDF en mémoire
        pdf_bytes = generate_pdf_bytes(doc)
        
        # 2. Préparer l'email
        subject = f"{doc.type.title()} n°{doc.numero} - {info.nom}"
        body = f"Bonjour,\n\nVeuillez trouver ci-joint votre {doc.type} n°{doc.numero}.\n\nCordialement,\n\n{info.nom}\n{info.telephone or ''}"
        filename = f"{doc.type}_{doc.numero}.pdf"
        
        # 3. Envoyer
        send_email_with_attachment(doc.client.email, subject, body, pdf_bytes, filename)
        
        # 4. Enregistrer la date d'envoi
        from datetime import datetime
        doc.sent_at = datetime.utcnow()
        db.session.commit()
        
        flash(f"L'email a été envoyé avec succès à {doc.client.email}.", "success")
    except Exception as e:
        flash(f"Erreur lors de l'envoi de l'email : {str(e)}", "danger")
        current_app.logger.error(f"Mail Error: {str(e)}")

    return redirect(request.referrer or url_for('index'))
