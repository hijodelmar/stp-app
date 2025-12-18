import sqlite3
import os

DB_PATH = os.path.join('instance', 'app.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print("Base de données introuvable.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Ajout de la colonne source_document_id...")
        cursor.execute("ALTER TABLE document ADD COLUMN source_document_id INTEGER REFERENCES document(id)")
        conn.commit()
        print("Migration réussie !")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("La colonne existe déjà.")
        else:
            print(f"Erreur : {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
