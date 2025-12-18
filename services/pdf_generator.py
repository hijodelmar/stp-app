import os
from flask import render_template, current_app
from xhtml2pdf import pisa
from models import CompanyInfo
from extensions import db

def generate_pdf(document):
    """
    Génère le PDF pour un document donné et l'enregistre.
    Retourne le nom du fichier.
    """
    # Récupérer les infos société
    # On prend le premier (et normalement unique) enregistrement
    company_info = CompanyInfo.query.first()
        
    # Base path for static files (used for images in PDF)
    static_base_path = os.path.join(current_app.root_path, 'static')
    
    # Rendu du template HTML
    html_string = render_template('pdf_template.html', 
                                document=document, 
                                info=company_info,
                                static_base_path=static_base_path)
    
    # Nom du fichier
    filename = f"{document.numero}.pdf"
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    # Génération du PDF
    try:
        with open(save_path, "wb") as result_file:
            pisa_status = pisa.CreatePDF(
                src=html_string,
                dest=result_file
            )
            
        if pisa_status.err:
             raise Exception(f"Erreur lors de la génération PDF (code {pisa_status.err})")
             
    except Exception as e:
        # Log error in real app
        print(f"PDF Error: {e}")
        raise e
    
    # Mise à jour du chemin dans la BDD
    document.pdf_path = filename
    db.session.commit()
    
    return filename

def delete_old_pdf(document):
    """
    Supprime l'ancien PDF d'un document si il existe.
    À appeler avant de modifier un document.
    """
    if document.pdf_path:
        old_pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.pdf_path)
        if os.path.exists(old_pdf_path):
            try:
                os.remove(old_pdf_path)
                print(f"✅ Old PDF deleted: {document.pdf_path}")
            except Exception as e:
                print(f"⚠️ Could not delete old PDF: {e}")
        
        # Réinitialiser le chemin PDF dans la base
        document.pdf_path = None
