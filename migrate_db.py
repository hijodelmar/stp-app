"""
Script to add the 'paid' column to existing database
"""
from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Try to add the column
        db.session.execute(text('ALTER TABLE document ADD COLUMN paid BOOLEAN DEFAULT 0'))
        db.session.commit()
        print("✅ Column 'paid' added successfully!")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✅ Column 'paid' already exists!")
        else:
            print(f"❌ Error: {e}")
            # Try to update existing rows to have paid=False
            try:
                db.session.rollback()
                db.session.execute(text('UPDATE document SET paid = 0 WHERE paid IS NULL'))
                db.session.commit()
                print("✅ Updated existing rows with default value!")
            except Exception as e2:
                print(f"❌ Could not update: {e2}")
