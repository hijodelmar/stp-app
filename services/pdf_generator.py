import os
from flask import render_template, current_app
from xhtml2pdf import pisa
from models import CompanyInfo
from extensions import db
from io import BytesIO

def generate_pdf_bytes(document):
    """
    Génère le PDF pour un document donné et retourne les octets (bytes).
    """
    try:
        company_info = CompanyInfo.query.first()
        static_root = os.path.join(current_app.root_path, 'static')
        logo_abs_path = ""
        if company_info and company_info.logo_path:
            logo_abs_path = os.path.join(static_root, company_info.logo_path)
        
        # Render HTML template
        html_string = render_template('pdf_template.html', 
                                    document=document, 
                                    info=company_info,
                                    logo_abs_path=logo_abs_path)
        
        # Generate PDF
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(src=html_string, dest=pdf_buffer)
        
        if pisa_status.err:
            raise Exception(f"Erreur PDF (code {pisa_status.err})")
        
        return pdf_buffer.getvalue()
    except Exception as e:
        import traceback
        print(f"PDF Error:\n{traceback.format_exc()}")
        raise e

def generate_pdf(document):
    """
    Génère le PDF pour un document donné et l'enregistre.
    Retourne le nom du fichier.
    """
    try:
        # Récupérer les infos société
        company_info = CompanyInfo.query.first()
            
        # RELIABLE PATH: Resolve the absolute path to the logo file
        static_root = os.path.join(current_app.root_path, 'static')
        logo_abs_path = ""
        if company_info and company_info.logo_path:
            logo_abs_path = os.path.join(static_root, company_info.logo_path)
            
        # QR Code Generation (Skip for Bon de Commande)
        import qrcode
        import base64
        from io import BytesIO
        from flask import url_for
        import uuid
        
        # QR Code Generation (Enabled for ALL documents)
        qr_code_b64 = None
        
        # Ensure token exists (Silent Update)
        if not document.secure_token:
            original_updated = document.updated_at # Capture timestamp
            document.secure_token = str(uuid.uuid4())
            db.session.commit()
            
            # Restore timestamp if changed
            if document.updated_at != original_updated:
                document.updated_at = original_updated
                db.session.commit()
            
        # Generate link
        verify_url = url_for('public.verify', token=document.secure_token, _external=True)
        
        # Make QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(verify_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_code_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        print(f"DEBUG: QR Code Generated. Length: {len(qr_code_b64)}")
        
        # Rendu du template HTML
        html_string = render_template('pdf_template.html', 
                                    document=document, 
                                    info=company_info,
                                    logo_abs_path=logo_abs_path,
                                    qr_code_b64=qr_code_b64)
        
        # Filename
        filename = f"{document.numero}.pdf"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Generate and save PDF
        with open(save_path, "wb") as result_file:
            pisa_status = pisa.CreatePDF(src=html_string, dest=result_file)
            
        if pisa_status.err:
            raise Exception(f"Erreur PDF (code {pisa_status.err})")
        
        # Update database (Silent Update)
        original_updated_final = document.updated_at
        document.pdf_path = filename
        db.session.commit()
        
        # Restore timestamp to prevent "Mise à jour" badge
        if document.updated_at != original_updated_final:
            document.updated_at = original_updated_final
            db.session.commit()
        
        return filename
        
    except Exception as e:
        print(f"PDF Error: {e}")
        import traceback
        print(traceback.format_exc())
        raise e

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
