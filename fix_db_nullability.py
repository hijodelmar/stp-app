import sqlite3
import os

db_path = 'instance/app.db'

if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Starting complex migration to make client_id nullable...")

try:
    # 1. Get existing schema of document table
    cursor.execute("PRAGMA table_info(document)")
    columns = cursor.fetchall()
    
    # 2. Build the CREATE TABLE statement for the new table
    # We want to change client_id from NOT NULL to NULLABLE
    column_defs = []
    col_names = []
    
    for col in columns:
        name = col[1]
        type_ = col[2]
        notnull = col[3]
        dflt_value = col[4]
        pk = col[5]
        
        col_names.append(name)
        
        definition = f"{name} {type_}"
        if pk:
            definition += " PRIMARY KEY"
            if name == 'id':
                definition += " AUTOINCREMENT"
        
        # Change client_id to be nullable
        if name == 'client_id':
             # Skip adding NOT NULL
             pass
        elif notnull:
            definition += " NOT NULL"
            
        if dflt_value is not None:
            definition += f" DEFAULT {dflt_value}"
            
        column_defs.append(definition)

    # Add foreign keys if possible (simplified for now)
    # definition_str = ", ".join(column_defs)
    
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

    # 3. Copy data
    # Note: we need to handle mapping if columns changed, but here we just added supplier_id earlier or it might be missing
    # Let's dynamically find common columns
    cursor.execute("PRAGMA table_info(document)")
    old_cols = [c[1] for c in cursor.fetchall()]
    cursor.execute("PRAGMA table_info(document_new)")
    new_cols = [c[1] for c in cursor.fetchall()]
    
    common_cols = [c for c in old_cols if c in new_cols]
    cols_str = ", ".join(common_cols)
    
    cursor.execute(f"INSERT INTO document_new ({cols_str}) SELECT {cols_str} FROM document")
    print(f"Data copied ({cursor.rowcount} rows).")

    # 4. Swap tables
    cursor.execute("DROP TABLE document")
    cursor.execute("ALTER TABLE document_new RENAME TO document")
    print("Tables swapped successfully.")

    conn.commit()
    print("Migration finished successfully.")

except Exception as e:
    conn.rollback()
    print(f"Migration failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
