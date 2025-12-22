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
    elif doc.type == 'bon_de_commande':
        required_roles.append('facture_admin')
    
    if not current_user.has_any_role(required_roles):
        from flask import abort
        return abort(403)

    info = CompanyInfo.query.first()
    
    # Determine recipient
    if doc.type == 'bon_de_commande':
        recipient_name = doc.supplier.raison_sociale
        recipient_email = doc.supplier.email
    else:
        recipient_name = doc.client.raison_sociale
        recipient_email = doc.client.email
    
    if not recipient_email:
        flash(f"Le destinataire {recipient_name} n'a pas d'adresse email enregistrée.", "danger")
        return redirect(request.referrer or url_for('index'))

    if not info or not info.smtp_server:
        flash("Veuillez configurer vos paramètres SMTP dans les Paramètres avant d'envoyer un email.", "warning")
        return redirect(url_for('settings.index'))

    try:
        # 1. Générer le PDF en mémoire
        pdf_bytes = generate_pdf_bytes(doc)
        
        # 2. Préparer l'email (Format HTML avec Signature)
        doc_type_display = "Bon de Commande" if doc.type == 'bon_de_commande' else doc.type.title()
        subject = f"{doc_type_display} n°{doc.numero} - {info.nom}"
        
        # Version HTML du message
        base_message = f"Bonjour,<br><br>Veuillez trouver ci-joint votre {doc_type_display.lower()} n°{doc.numero}.<br><br>"
        signature = info.email_signature if info.email_signature else f"Cordialement,<br><br>{info.nom}<br>{info.telephone or ''}"
        
        body_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                {base_message}
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                {signature}
            </body>
        </html>
        """
        
        filename = f"{doc.type}_{doc.numero}.pdf"
        
        # 3. Envoyer
        send_email_with_attachment(recipient_email, subject, body_html, pdf_bytes, filename)
        
        # 4. Enregistrer la date d'envoi
        from datetime import datetime
        doc.sent_at = datetime.utcnow()
        db.session.commit()
        
        flash(f"L'email a été envoyé avec succès à {recipient_email}.", "success")
    except Exception as e:
        flash(f"Erreur lors de l'envoi de l'email : {str(e)}", "danger")
        current_app.logger.error(f"Mail Error: {str(e)}")

    return redirect(request.referrer or url_for('index'))
