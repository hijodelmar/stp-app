from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Migrating database for Configurable TVA...")
    
    # 1. Add tva_default to company_info
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE company_info ADD COLUMN tva_default FLOAT DEFAULT 20.0"))
            # Set default value for existing rows
            conn.execute(text("UPDATE company_info SET tva_default = 20.0"))
            conn.commit()
            print("Added tva_default to company_info.")
    except Exception as e:
        print(f"Skipping company_info update (maybe already exists): {e}")

    # 2. Add tva_rate to document
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE document ADD COLUMN tva_rate FLOAT DEFAULT 20.0"))
            # Set default value for existing rows
            conn.execute(text("UPDATE document SET tva_rate = 20.0"))
            conn.commit()
            print("Added tva_rate to document.")
    except Exception as e:
        print(f"Skipping document update (maybe already exists): {e}")
        
    print("Migration complete.")
