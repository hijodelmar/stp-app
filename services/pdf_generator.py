import os
from flask import render_template, current_app
from xhtml2pdf import pisa
from models import CompanyInfo
from extensions import db
def generate_pdf(document):
    """
    Génère le PDF pour un document donné et l'enregistre.
    """
    company_info = CompanyInfo.query.first()
        
    # RELIABLE PATH: Resolve the absolute path to the logo file
    static_root = os.path.join(current_app.root_path, 'static')
    logo_abs_path = ""
    if company_info and company_info.logo_path:
        logo_abs_path = os.path.join(static_root, company_info.logo_path)
    
    # Rendu du template HTML
    html_string = render_template('pdf_template.html', 
                                document=document, 
                                info=company_info,
                                logo_abs_path=logo_abs_path)
    
    filename = f"{document.numero}.pdf"
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        with open(save_path, "wb") as result_file:
            pisa_status = pisa.CreatePDF(src=html_string, dest=result_file)
            
        if pisa_status.err:
             raise Exception(f"Erreur lors de la génération PDF (code {pisa_status.err})")
             
    except Exception as e:
        print(f"PDF Error: {e}")
        raise e
    
    document.pdf_path = filename
    db.session.commit()
    return filename
def delete_old_pdf(document):
    if document.pdf_path:
        old_pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.pdf_path)
        if os.path.exists(old_pdf_path):
            try:
                os.remove(old_pdf_path)
            except Exception as e:
                print(f"⚠️ Could not delete old PDF: {e}")
        document.pdf_path = None
