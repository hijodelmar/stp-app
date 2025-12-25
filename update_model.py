from app import create_app
from extensions import db
from models import AISettings

app = create_app()
with app.app_context():
    s = AISettings.get_settings()
    print(f"DEBUG: Current Provider: {s.provider}")
    print(f"DEBUG: Current Model Name: [{s.model_name}]")
    print(f"DEBUG: AI Enabled: {s.enabled}")
    
    # Force a clean name for test
    s.model_name = 'gemini-1.5-flash'
    db.session.commit()
    print("Modèle forcé à 'gemini-1.5-flash'")
