from app import create_app
from extensions import db
from sqlalchemy import text, inspect

app = create_app()

def migrate():
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('document')]
        
        if 'sent_at' not in columns:
            print("Ajout de la colonne sent_at à la table document...")
            db.session.execute(text("ALTER TABLE document ADD COLUMN sent_at DATETIME"))
            db.session.commit()
            print("Migration terminée avec succès.")
        else:
            print("La colonne sent_at existe déjà.")

if __name__ == "__main__":
    migrate()
