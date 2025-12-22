import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from models import CompanyInfo

def send_email_with_attachment(to_email, subject, body, attachment_content, attachment_filename):
    """
    Envoie un email avec une pièce jointe en utilisant les réglages SMTP de la base de données.
    """
    settings = CompanyInfo.query.first()
    if not settings or not settings.smtp_server:
        raise Exception("Configuration SMTP manquante dans les paramètres de la société.")

    # Création du message
    msg = MIMEMultipart()
    msg['From'] = settings.mail_default_sender or settings.smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject

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
    
    server.send_message(msg)
    server.quit()
