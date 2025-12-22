import sqlite3
import os
from app import create_app
from extensions import db

# 1. Create missing tables (like Supplier) using SQLAlchemy
app = create_app()
with app.app_context():
    db.create_all()
    print("Missing tables (Supplier) created if they didn't exist.")

# 2. Fix Document table schema (Make client_id nullable and add supplier_id)
db_path = 'instance/app.db'
if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Starting Document table migration...")

try:
    # Check if we already have the new schema
    cursor.execute("PRAGMA table_info(document)")
    cols = {c[1]: c for c in cursor.fetchall()}
    
    if 'supplier_id' in cols and cols['client_id'][3] == 0:
        print("Document table already has the correct schema. Skipping swap.")
        conn.close()
        exit(0)

    # Re-creating manually for safety to match models.py exactly
    create_stmt = '''
    CREATE TABLE document_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type VARCHAR(20) NOT NULL,
        numero VARCHAR(50) NOT NULL UNIQUE,
        date DATETIME,
        client_id INTEGER,
        supplier_id INTEGER,
        montant_ht FLOAT,
        tva FLOAT,
        montant_ttc FLOAT,
        autoliquidation BOOLEAN,
        tva_rate FLOAT,
        paid BOOLEAN,
        client_reference VARCHAR(50),
        chantier_reference VARCHAR(100),
        validity_duration INTEGER,
        pdf_path VARCHAR(200),
        sent_at DATETIME,
        created_at DATETIME,
        updated_at DATETIME,
        created_by_id INTEGER,
        updated_by_id INTEGER,
        source_document_id INTEGER,
        FOREIGN KEY(client_id) REFERENCES client (id),
        FOREIGN KEY(supplier_id) REFERENCES supplier (id),
        FOREIGN KEY(created_by_id) REFERENCES user (id),
        FOREIGN KEY(updated_by_id) REFERENCES user (id),
        FOREIGN KEY(source_document_id) REFERENCES document (id)
    )
    '''
    
    cursor.execute(create_stmt)
    print("Temporary table created.")

    # Find common columns to copy
    cursor.execute("PRAGMA table_info(document)")
    old_cols = [c[1] for c in cursor.fetchall()]
    cursor.execute("PRAGMA table_info(document_new)")
    new_cols = [c[1] for c in cursor.fetchall()]
    
    common_cols = [c for c in old_cols if c in new_cols]
    cols_str = ", ".join(common_cols)
    
    cursor.execute(f"INSERT INTO document_new ({cols_str}) SELECT {cols_str} FROM document")
    print(f"Data copied ({cursor.rowcount} rows).")

    # Swap tables
    cursor.execute("DROP TABLE document")
    cursor.execute("ALTER TABLE document_new RENAME TO document")
    print("Document table updated successfully.")

    conn.commit()
    print("Migration finished successfully.")

except Exception as e:
    conn.rollback()
    print(f"Migration failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
