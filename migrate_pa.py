import sqlite3
import os
from app import create_app
from extensions import db
from models import User, Role, user_roles
from sqlalchemy import text

# 1. Create missing tables (Supplier, Role, user_roles, etc.) using SQLAlchemy
app = create_app()
with app.app_context():
    db.create_all()
    print("Checked/Created missing tables.")

    db_path = os.path.join(app.instance_path, 'app.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 2. Update User table
    print("Checking User table columns...")
    user_columns = [
        ("last_active", "DATETIME"),
        ("current_session_id", "VARCHAR(36)")
    ]
    for col_name, col_type in user_columns:
        try:
            cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}")
            print(f"Column '{col_name}' added to user table.")
        except sqlite3.OperationalError:
            pass

    # 3. Update CompanyInfo table
    print("Checking CompanyInfo table columns...")
    company_columns = [
        ("tva_default", "FLOAT DEFAULT 20.0"),
        ("smtp_server", "VARCHAR(100)"),
        ("smtp_port", "INTEGER DEFAULT 587"),
        ("smtp_user", "VARCHAR(100)"),
        ("smtp_password", "VARCHAR(100)"),
        ("smtp_use_tls", "BOOLEAN DEFAULT 1"),
        ("smtp_use_ssl", "BOOLEAN DEFAULT 0"),
        ("mail_default_sender", "VARCHAR(100)")
    ]
    for col_name, col_type in company_columns:
        try:
            cursor.execute(f"ALTER TABLE company_info ADD COLUMN {col_name} {col_type}")
            print(f"Column '{col_name}' added to company_info table.")
        except sqlite3.OperationalError:
            pass

    # 4. Update LigneDocument table (FIX for category)
    print("Checking LigneDocument table columns...")
    try:
        cursor.execute("ALTER TABLE ligne_document ADD COLUMN category VARCHAR(20) DEFAULT 'fourniture'")
        print("Column 'category' added to ligne_document table.")
    except sqlite3.OperationalError:
        print("Column 'category' already exists in ligne_document.")
    
    conn.commit()
    conn.close()

    # 5. Create default roles
    default_roles = [
        ('admin', 'Administrateur complet'),
        ('manager', 'Gestionnaire (Docs/Clients, pas de Paramètres/Users)'),
        ('settings', 'Accès aux Paramètres'),
        ('user_admin', 'Gestion des Utilisateurs'),
        ('reporting', 'Visualisation uniquement (Lecture seule)'),
        ('devis_admin', 'Gestion des Devis'),
        ('facture_admin', 'Gestion des Factures'),
        ('avoir_admin', 'Gestion des Avoirs'),
        ('client_admin', 'Gestion des Clients')
    ]
    
    role_objs = {}
    for r_name, r_desc in default_roles:
        role = Role.query.filter_by(name=r_name).first()
        if not role:
            role = Role(name=r_name, description=r_desc)
            db.session.add(role)
            print(f"Role created: {r_name}")
        role_objs[r_name] = role
    
    db.session.commit()

    # 6. Migrate existing users' roles
    users = User.query.all()
    for user in users:
        if not user.roles:
            try:
                result = db.session.execute(text(f"SELECT role FROM user WHERE id = {user.id}")).fetchone()
                old_role_name = result[0] if result else None
            except Exception:
                old_role_name = None
            
            if old_role_name and old_role_name in role_objs:
                user.roles.append(role_objs[old_role_name])
                print(f"User {user.username}: Migrated role '{old_role_name}'")
            else:
                user.roles.append(role_objs['admin'])
                print(f"User {user.username}: Assigned 'admin'")
    
    db.session.commit()

# 7. Fix Document table schema
print("Checking Document table schema...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("PRAGMA table_info(document)")
    cols = {c[1]: c for c in cursor.fetchall()}
    
    if 'supplier_id' in cols and cols['client_id'][3] == 0:
        print("Document table already correct.")
    else:
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
        cursor.execute("PRAGMA table_info(document)")
        old_cols = [c[1] for c in cursor.fetchall()]
        cursor.execute("PRAGMA table_info(document_new)")
        new_cols = [c[1] for c in cursor.fetchall()]
        common_cols = [c for c in old_cols if c in new_cols]
        cols_str = ", ".join(common_cols)
        cursor.execute(f"INSERT INTO document_new ({cols_str}) SELECT {cols_str} FROM document")
        cursor.execute("DROP TABLE document")
        cursor.execute("ALTER TABLE document_new RENAME TO document")
        print("Document table updated.")

    conn.commit()
    print("All migrations finished successfully.")

except Exception as e:
    conn.rollback()
    print(f"Migration failed: {e}")
finally:
    conn.close()
