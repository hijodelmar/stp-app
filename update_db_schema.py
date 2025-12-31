import sqlite3
from app import create_app, db
from models import AISettings

def update_schema():
    app = create_app()
    with app.app_context():
        # Get database path from config
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            print(f"Database path: {db_path}")
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. Check/Add brand_icon to company_info
            try:
                cursor.execute("SELECT brand_icon FROM company_info LIMIT 1")
                print("Column 'brand_icon' already exists in 'company_info'.")
            except sqlite3.OperationalError:
                print("Adding 'brand_icon' column to 'company_info'...")
                try:
                    cursor.execute("ALTER TABLE company_info ADD COLUMN brand_icon TEXT DEFAULT 'fas fa-tools'")
                    conn.commit()
                    print("Column added successfully.")
                except Exception as e:
                    print(f"Error adding column: {e}")

            # 2. Check/Add other potentially missing columns if any (from recent changes)
            # Example: theme was added recently too?
            try:
                cursor.execute("SELECT theme FROM company_info LIMIT 1")
            except sqlite3.OperationalError:
                print("Adding 'theme' column to 'company_info'...")
                try:
                    cursor.execute("ALTER TABLE company_info ADD COLUMN theme TEXT DEFAULT 'default'")
                    conn.commit()
                    print("Column added successfully.")
                except Exception as e:
                    print(f"Error adding column: {e}")

            conn.close()
            
            # 3. Create missing tables (like AISettings) using SQLAlchemy
            print("Checking for new tables...")
            db.create_all()
            print("Database schema update complete.")
        else:
            print("This script is optimized for SQLite. Please check your database URI.")

if __name__ == "__main__":
    update_schema()
