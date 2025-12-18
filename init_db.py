from app import create_app
from extensions import db
from models import CompanyInfo
import os

app = create_app()

with app.app_context():
    db_path = os.path.join(app.instance_path, 'app.db')
    
    # Create tables
    db.create_all()
    print(f"Database tables created at {db_path}")
    
    # Check if CompanyInfo already exists
    existing_info = CompanyInfo.query.first()
    
    if not existing_info:
        # Create default company info with required fields
        default_info = CompanyInfo(
            nom="Service Température Plomberie",
            adresse="Votre adresse",
            cp="00000",
            ville="Votre ville",
            ville_signature="Votre ville",
            telephone="",
            email="",
            conditions_reglement="",
            iban="",
            footer_info=""
        )
        db.session.add(default_info)
        db.session.commit()
        print("Default company info created successfully.")
        print("Please update your company information in the Settings page.")
    else:
        print("Company info already exists.")
    
    print("Database initialized successfully.")
