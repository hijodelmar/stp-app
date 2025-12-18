import sqlite3
import os

def migrate():
    db_path = 'instance/app.db'
    if not os.path.exists(db_path):
        print(f"Base de données non trouvée à {db_path}")
        return

    print(f"Migration de la base de données : {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Vérifier si la colonne existe déjà
        cursor.execute("PRAGMA table_info(document)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'client_reference' not in columns:
            print("Ajout de la colonne 'client_reference' à la table 'document'...")
            cursor.execute("ALTER TABLE document ADD COLUMN client_reference VARCHAR(30)")
            conn.commit()
            print("Migration réussie !")
        else:
            print("La colonne 'client_reference' existe déjà.")
            
    except Exception as e:
        print(f"Erreur lors de la migration : {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
