from app import create_app
from extensions import db
from models import ClientContact, document_cc, Document
from sqlalchemy import text, inspect

app = create_app()

def migrate():
    with app.app_context():
        inspector = inspect(db.engine)
        print("--- Début de la migration Multi-Contacts ---")

        # 1. Create new table ClientContact
        if not inspector.has_table('client_contact'):
            print("Création de la table 'client_contact'...")
            ClientContact.__table__.create(db.engine)
        else:
            print("Table 'client_contact' existe déjà.")

        # 2. Create new association table document_cc
        if not inspector.has_table('document_cc'):
            print("Création de la table 'document_cc'...")
            document_cc.create(db.engine)
        else:
            print("Table 'document_cc' existe déjà.")

        # 3. Add column contact_id to Document table
        # Check if column exists
        columns = [col['name'] for col in inspector.get_columns('document')]
        if 'contact_id' not in columns:
            print("Ajout de la colonne 'contact_id' à la table 'document'...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE document ADD COLUMN contact_id INTEGER REFERENCES client_contact(id)"))
                conn.commit()
        else:
            print("Colonne 'contact_id' déjà présente dans 'document'.")

        print("--- Migration terminée avec succès ---")

if __name__ == '__main__':
    migrate()
