from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Début de la migration pour ajouter 'category' à 'ligne_document'...")
    
    with db.engine.connect() as conn:
        # Vérifier si la colonne existe déjà
        try:
            result = conn.execute(text("SELECT category FROM ligne_document LIMIT 1"))
            print("La colonne 'category' existe déjà.")
        except Exception:
            print("Ajout de la colonne 'category'...")
            # SQLite ne supporte pas toujours ADD COLUMN avec DEFAULT sur une table existante complexe, 
            # mais pour un champ simple ça passe souvent. Sinon il faut recréer.
            # Essayons ADD COLUMN standard.
            try:
                conn.execute(text("ALTER TABLE ligne_document ADD COLUMN category VARCHAR(20) DEFAULT 'fourniture'"))
                # Mettre à jour les lignes existantes pour avoir 'fourniture'
                conn.execute(text("UPDATE ligne_document SET category = 'fourniture' WHERE category IS NULL"))
                conn.commit()
                print("Colonne 'category' ajoutée avec succès.")
            except Exception as e:
                print(f"Erreur lors de l'ajout de la colonne : {e}")
                
    print("Migration terminée.")
