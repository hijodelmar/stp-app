import sqlite3
import os

# Chemins potentiels de la base de données
db_paths = ['instance/app.db', 'instance/stp.db', 'stp.db']
db_file = None

for path in db_paths:
    if os.path.exists(path):
        db_file = path
        break

if not db_file:
    print("❌ Base de données non trouvée. Assurez-vous d'être dans le dossier racine du projet.")
else:
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Tentative d'ajout de la colonne
        cursor.execute("ALTER TABLE document ADD COLUMN chantier_reference VARCHAR(50)")
        
        conn.commit()
        conn.close()
        print(f"✅ Colonne 'chantier_reference' ajoutée avec succès à {db_file} !")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️ La colonne 'chantier_reference' existe déjà.")
        else:
            print(f"❌ Erreur SQLite : {e}")
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")
