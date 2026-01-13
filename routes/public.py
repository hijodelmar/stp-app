from flask import Blueprint, render_template, abort
from models import Document, CompanyInfo
from extensions import db

bp = Blueprint('public', __name__)

@bp.route('/verify/<token>')
def verify(token):
    document = Document.query.filter_by(secure_token=token).first_or_404()
    info = CompanyInfo.query.first()
    
    return render_template('public/verify_document.html', document=document, info=info)
