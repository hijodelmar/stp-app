from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        # Check if table exists
        inspector = db.inspect(db.engine)
        if 'expense' not in inspector.get_table_names():
            print("Creating 'expense' table...")
            # Create table using raw SQL for control or rely on create_all if models are updated
            # Ideally we use create_all but only for the new table if possible, or just create everything (safe for existing tables usually)
            
            # Using raw SQL to be explicit and safe for SQLite
            sql = """
            CREATE TABLE expense (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                description VARCHAR(200) NOT NULL,
                amount_ht FLOAT,
                tva FLOAT,
                amount_ttc FLOAT,
                category VARCHAR(50) NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                is_reimbursed BOOLEAN,
                proof_path VARCHAR(300),
                supplier_id INTEGER,
                created_at DATETIME,
                updated_at DATETIME,
                created_by_id INTEGER,
                FOREIGN KEY(supplier_id) REFERENCES supplier(id),
                FOREIGN KEY(created_by_id) REFERENCES user(id)
            );
            """
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                print("Table 'expense' created successfully.")
            except Exception as e:
                print(f"Error creating table: {e}")
        else:
            print("Table 'expense' already exists.")

if __name__ == "__main__":
    migrate()
