from extensions import db
from app import create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Migrating database for Validity Duration...")
    
    # Check if column exists
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('document')]
    
    if 'validity_duration' not in columns:
        print("Adding validity_duration to document table...")
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE document ADD COLUMN validity_duration INTEGER DEFAULT 1"))
            conn.commit()
    else:
        print("validity_duration already exists.")

    print("Migration complete.")
