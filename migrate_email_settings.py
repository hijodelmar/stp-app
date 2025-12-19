from app import create_app
from extensions import db
from sqlalchemy import text, inspect

app = create_app()

def migrate():
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('company_info')]
        
        new_columns = [
            ('smtp_server', 'VARCHAR(100)'),
            ('smtp_port', 'INTEGER'),
            ('smtp_user', 'VARCHAR(100)'),
            ('smtp_password', 'VARCHAR(100)'),
            ('smtp_use_tls', 'BOOLEAN'),
            ('smtp_use_ssl', 'BOOLEAN'),
            ('mail_default_sender', 'VARCHAR(100)')
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                print(f"Ajout de la colonne {col_name}...")
                db.session.execute(text(f"ALTER TABLE company_info ADD COLUMN {col_name} {col_type}"))
        
        db.session.commit()
        print("Migration des paramètres email terminée.")

if __name__ == "__main__":
    migrate()
