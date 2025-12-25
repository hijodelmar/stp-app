import sqlite3
import os
from app import create_app

app = create_app()

with app.app_context():
    db_path = os.path.join(app.instance_path, 'app.db')
    print(f"Connecting to database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Checking CompanyInfo table for 'theme' column...")
        cursor.execute("PRAGMA table_info(company_info)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'theme' not in columns:
            print("Adding 'theme' column to company_info...")
            cursor.execute("ALTER TABLE company_info ADD COLUMN theme VARCHAR(50) DEFAULT 'default'")
            print("Column 'theme' added successfully.")
        else:
            print("Column 'theme' already exists.")
            
        conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()
