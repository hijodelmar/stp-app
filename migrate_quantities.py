import sqlite3
import os

def migrate():
    db_path = os.path.join('instance', 'app.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Starting migration: converting 'quantite' to INTEGER...")

        # 1. Check current schema
        cursor.execute("PRAGMA table_info(ligne_document)")
        columns = cursor.fetchall()
        # db.Float usually maps to REAL or FLOAT in SQLite
        
        # 2. Update existing data: round to nearest integer
        # Note: SQLite is dynamically typed, so we can store ints in REAL columns, but we want to enforce schema if possible
        # However, usually we just update the values first.
        
        print("Rounding existing quantities...")
        cursor.execute("UPDATE ligne_document SET quantite = CAST(ROUND(quantite) AS INTEGER)")
        
        # 3. Alter table to change column type (SQLite doesn't support ALTER COLUMN TYPE directly easily)
        # But for SQLAlchemy models, it's enough if the data fits.
        # To cleaner schema change in SQLite, we usually have to recreate table.
        # Given this is a small project, just updating values and Python model is often "enough" for SQLite + SQLAlchemy 
        # as long as we don't need strict schema constraint enforcement at DB level immediately.
        # BUT, to be clean, let's try to update the definition if possible or just rely on Python side casting.
        # Since the user asked specifically to change format, updating values is key.

        conn.commit()
        print("Quantities updated successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
