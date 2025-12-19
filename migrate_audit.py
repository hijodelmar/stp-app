import sqlite3
import os

# Robust path detection: find instance folder Relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'instance', 'app.db')

def migrate():
    print(f"Tentative de migration sur : {db_path}")
    if not os.path.exists(db_path):
        # Fallback to local 'instance/app.db' if absolute path fails for some reason
        db_path_fallback = 'instance/app.db'
        if not os.path.exists(db_path_fallback):
            print(f"Erreur : La base de données n'a pas été trouvée à {db_path} ou {db_path_fallback}")
            return
        actual_db = db_path_fallback
    else:
        actual_db = db_path

    conn = sqlite3.connect(actual_db)
    cursor = conn.cursor()

    print(f"Migration de la base de données : {db_path}")

    # Correct SQLite syntax: INTEGER PRIMARY KEY is already autoincrementing
    cursor.execute('DROP TABLE IF EXISTS user')
    cursor.execute('''
    CREATE TABLE user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(64) UNIQUE NOT NULL,
        password_hash VARCHAR(128),
        role VARCHAR(20) NOT NULL DEFAULT 'manager'
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_user_username ON user (username)')

    # 2. Ajouter les colonnes d'audit à client
    columns_client = [
        ('created_at', 'DATETIME'),
        ('updated_at', 'DATETIME'),
        ('created_by_id', 'INTEGER'),
        ('updated_by_id', 'INTEGER')
    ]
    
    for col_name, col_type in columns_client:
        try:
            cursor.execute(f"ALTER TABLE client ADD COLUMN {col_name} {col_type}")
            print(f"Ajout de {col_name} à client")
        except sqlite3.OperationalError:
            print(f"La colonne {col_name} existe déjà dans client")

    # 3. Ajouter les colonnes d'audit à document
    columns_doc = [
        ('created_at', 'DATETIME'),
        ('updated_at', 'DATETIME'),
        ('created_by_id', 'INTEGER'),
        ('updated_by_id', 'INTEGER')
    ]
    
    for col_name, col_type in columns_doc:
        try:
            cursor.execute(f"ALTER TABLE document ADD COLUMN {col_name} {col_type}")
            print(f"Ajout de {col_name} à document")
        except sqlite3.OperationalError:
            print(f"La colonne {col_name} existe déjà dans document")

    # 4. Initialiser les dates pour les enregistrements existants
    from datetime import datetime
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("UPDATE client SET created_at = ?, updated_at = ? WHERE created_at IS NULL", (now, now))
    cursor.execute("UPDATE document SET created_at = ?, updated_at = ? WHERE created_at IS NULL", (now, now))

    conn.commit()
    conn.close()
    print("Migration réussie !")

if __name__ == '__main__':
    migrate()
