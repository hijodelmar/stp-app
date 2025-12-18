import sqlite3
import os
from datetime import datetime

# Robust path detection
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'instance', 'app.db')

def migrate():
    print(f"--- Démarrage de la migration complète ---")
    
    if not os.path.exists(db_path):
        # Fallback to local 'instance/app.db'
        db_path_fallback = 'instance/app.db'
        if not os.path.exists(db_path_fallback):
            print(f"Erreur : Base de données non trouvée.")
            return
        actual_db = db_path_fallback
    else:
        actual_db = db_path

    print(f"Base de données cible : {actual_db}")
    conn = sqlite3.connect(actual_db)
    cursor = conn.cursor()

    # 1. Table USER
    print("\n[1/3] Vérification de la table 'user'...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
    if not cursor.fetchone():
        print("Création de la table 'user'...")
        cursor.execute('''
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(64) UNIQUE NOT NULL,
            password_hash VARCHAR(128),
            role VARCHAR(20) NOT NULL DEFAULT 'manager'
        )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS ix_user_username ON user (username)')
    else:
        print("La table 'user' existe déjà.")

    # 2. Colonnes CLIENT
    print("\n[2/3] Vérification des colonnes de la table 'client'...")
    columns_client = [
        ('created_at', 'DATETIME'),
        ('updated_at', 'DATETIME'),
        ('created_by_id', 'INTEGER'),
        ('updated_by_id', 'INTEGER')
    ]
    
    for col_name, col_type in columns_client:
        try:
            cursor.execute(f"ALTER TABLE client ADD COLUMN {col_name} {col_type}")
            print(f"Ajouté : client.{col_name}")
        except sqlite3.OperationalError:
            pass # Colonne déjà présente

    # 3. Colonnes DOCUMENT
    print("\n[3/3] Vérification des colonnes de la table 'document'...")
    columns_doc = [
        ('paid', 'BOOLEAN DEFAULT 0'),
        ('client_reference', 'VARCHAR(30)'),
        ('source_document_id', 'INTEGER'),
        ('created_at', 'DATETIME'),
        ('updated_at', 'DATETIME'),
        ('created_by_id', 'INTEGER'),
        ('updated_by_id', 'INTEGER')
    ]
    
    for col_name, col_type in columns_doc:
        try:
            cursor.execute(f"ALTER TABLE document ADD COLUMN {col_name} {col_type}")
            print(f"Ajouté : document.{col_name}")
        except sqlite3.OperationalError:
            pass # Colonne déjà présente

    # 4. Initialisation des dates (si nécessaire)
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("UPDATE client SET created_at = ?, updated_at = ? WHERE created_at IS NULL", (now, now))
    cursor.execute("UPDATE document SET created_at = ?, updated_at = ? WHERE created_at IS NULL", (now, now))

    conn.commit()
    conn.close()
    print("\n--- Migration terminée avec succès ! ---")

if __name__ == '__main__':
    migrate()
