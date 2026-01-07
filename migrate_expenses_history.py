import sqlite3
import os

def migrate():
    db_path = os.path.join('instance', 'app.db')
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(expense)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'updated_by_id' not in columns:
            print("Adding updated_by_id column to expense table...")
            cursor.execute("ALTER TABLE expense ADD COLUMN updated_by_id INTEGER REFERENCES user(id)")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column updated_by_id already exists.")

    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
