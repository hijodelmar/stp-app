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
    recipient_emails = []
    
    if doc.type == 'bon_de_commande':
        recipient_name = doc.supplier.raison_sociale
        if doc.supplier.email:
            recipient_emails = [doc.supplier.email]
    else:
        # Determine recipients (Direct "To" from selected "cc_contacts")
        # Note: 'cc_contacts' field is now used as the list of DIRECT recipients
        recipient_emails = [c.email for c in doc.cc_contacts if c.email]
        recipient_name = doc.client.raison_sociale # Used mainly for logging/context
    
    if not recipient_emails:
        flash(f"Aucun destinataire sélectionné ou adresse email manquante.", "danger")
        return redirect(request.referrer or url_for('index'))

    # recipient_name is set above
    
    # We send to all selected contacts directly
    # cc_emails is empty because everyone is in TO
    cc_emails = []

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
        base_message = f"Bonjour,<br><br>Veuillez trouver ci-joint votre {doc_type_display.lower()} n°{doc.numero}.<br><br>Cordialement,<br>"
        signature = info.email_signature if info.email_signature else f"{info.nom}<br>{info.telephone or ''}"
        
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
        # Nous passons la liste des emails. Le service devra gérer cela.
        # Pour l'instant, envoyons au premier destinataire et mettons les autres en CC ? 
        # NON, le user veut "directement".
        # Meilleure approche : Modifier mail_service pour accepter une liste.
        
        # Join emails for display in flash
        recipients_str = ', '.join(recipient_emails)
        
        send_email_with_attachment(recipient_emails, subject, body_html, pdf_bytes, filename)
        
        # 4. Enregistrer la date d'envoi
        from datetime import datetime
        doc.sent_at = datetime.utcnow()
        db.session.commit()
        
        msg_text = f"L'email a été envoyé avec succès à : {recipients_str}"
        flash(msg_text, "success")
    except Exception as e:
        flash(f"Erreur lors de l'envoi de l'email : {str(e)}", "danger")
        current_app.logger.error(f"Mail Error: {str(e)}")

    return redirect(request.referrer or url_for('index'))
