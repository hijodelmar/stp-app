import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from models import CompanyInfo

def send_email_with_attachment(to_email, subject, body, attachment_content, attachment_filename, cc_emails=None):
    """
    Envoie un email avec une pièce jointe en utilisant les réglages SMTP de la base de données.
    cc_emails: Liste d'adresses email en copie
    """
    settings = CompanyInfo.query.first()
    if not settings or not settings.smtp_server:
        raise Exception("Configuration SMTP manquante dans les paramètres de la société.")

    # Création du message
    msg = MIMEMultipart()
    msg['From'] = settings.mail_default_sender or settings.smtp_user
    recipients = []
    
    if isinstance(to_email, list):
        msg['To'] = ', '.join(to_email)
        recipients.extend(to_email)
    else:
        msg['To'] = to_email
        recipients.append(to_email)
    
    msg['Subject'] = subject
    
    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)
        recipients.extend(cc_emails)

    # Corps de l'email (HTML support)
    msg.attach(MIMEText(body, 'html'))

    # Pièce jointe (PDF)
    part = MIMEApplication(attachment_content, _subtype="pdf")
    part.add_header('Content-Disposition', 'attachment', filename=attachment_filename)
    msg.attach(part)

    # Connexion au serveur
    if settings.smtp_use_ssl:
        server = smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port)
    else:
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        if settings.smtp_use_tls:
            server.starttls()

    # Authentification et envoi
    if settings.smtp_user and settings.smtp_password:
        server.login(settings.smtp_user, settings.smtp_password)
    
    server.send_message(msg, to_addrs=recipients)
    server.quit()
