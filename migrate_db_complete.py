from app import create_app
from extensions import db
from models import Document, User
from sqlalchemy import text
import uuid

app = create_app()

def add_column(table, column_def):
    try:
        with db.engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))
            conn.commit()
        print(f"✅ Added column: {column_def} to {table}")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print(f"ℹ️ Column {column_def} already exists in {table}")
        else:
            print(f"⚠️ Note on {table}: {e}")

def populate_tokens():
    print("🔄 Checking for documents needing tokens...")
    # Refresh metadata to ensure SQLAlchemy knows about the new column
    # Use raw SQL to update missing tokens to avoid model cache issues
    try:
        with db.engine.connect() as conn:
            # Check how many need updates
            result = conn.execute(text("SELECT id FROM document WHERE secure_token IS NULL"))
            ids = [row[0] for row in result]
            
            if not ids:
                print("✅ All documents already have tokens.")
                return

            print(f"📝 Updating {len(ids)} documents...")
            for doc_id in ids:
                token = str(uuid.uuid4())
                conn.execute(text("UPDATE document SET secure_token = :token WHERE id = :id"), 
                             {"token": token, "id": doc_id})
            conn.commit()
            print("✅ Tokens generated successfully.")
            
    except Exception as e:
        print(f"❌ Error generating tokens: {e}")

with app.app_context():
    print("🚀 Starting Database Migration...")
    
    # 1. Add Columns
    add_column("document", "secure_token VARCHAR(36)")
    add_column("user", "force_logout_at DATETIME")
    
    # 2. Populate Data
    populate_tokens()
    
    print("✨ Migration Complete!")
