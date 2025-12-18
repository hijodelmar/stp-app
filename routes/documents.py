from flask import Blueprint, send_from_directory, current_app, abort
from extensions import db
from models import Document
from services.pdf_generator import generate_pdf
import os

bp = Blueprint('documents', __name__)

@bp.route('/pdf/<int:id>')
def view_pdf(id):
    document = Document.query.get_or_404(id)
    
    # Generate if not exists
    if not document.pdf_path or not os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], document.pdf_path)):
        try:
            filename = generate_pdf(document)
        except Exception as e:
            return f"Erreur lors de la génération du PDF : {str(e)}", 500
    else:
        filename = document.pdf_path
        
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
