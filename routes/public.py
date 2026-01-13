from flask import Blueprint, render_template, abort
from models import Document, CompanyInfo
from extensions import db

bp = Blueprint('public', __name__)

@bp.route('/verify/<token>')
def verify(token):
    document = Document.query.filter_by(secure_token=token).first_or_404()
    info = CompanyInfo.query.first()
    
    return render_template('public/verify_document.html', document=document, info=info)

@bp.route('/debug_env')
def debug_env():
    import sys
    import os
    try:
        import qrcode
        qrcode_version = qrcode.__version__
        qrcode_path = qrcode.__file__
        status = "✅ qrcode imported successfully"
    except ImportError as e:
        status = f"❌ qrcode Import Error: {e}"
        qrcode_version = "N/A"
        qrcode_path = "N/A"
    
    return f"""
    <style>body{{font-family:sans-serif; padding:20px;}}</style>
    <h1>🔍 Environment Debugger</h1>
    <div style="background:#f0f0f0; padding:15px; border-radius:8px;">
        <h3>Module Status</h3>
        <p style="font-size:1.2em;"><strong>{status}</strong></p>
        <p><strong>QRCode Version:</strong> {qrcode_version}</p>
        <p><strong>QRCode Path:</strong> {qrcode_path}</p>
    </div>
    <div style="margin-top:20px;">
        <h3>Python Runtime</h3>
        <p><strong>Executable:</strong> {sys.executable}</p>
        <p><strong>Version:</strong> {sys.version}</p>
        <p><strong>CWD:</strong> {os.getcwd()}</p>
    </div>
    <div style="margin-top:20px;">
        <h3>System Path</h3>
        <ul style="background:#eee; padding:10px; list-style:none;">
            {''.join(f'<li>{p}</li>' for p in sys.path)}
        </ul>
    </div>
    """
