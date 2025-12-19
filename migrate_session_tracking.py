import sqlite3
import os

# Path to your database
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')

def migrate():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add last_active column
        cursor.execute("ALTER TABLE user ADD COLUMN last_active DATETIME")
        print("Column 'last_active' added.")
    except sqlite3.OperationalError as e:
        print(f"Column 'last_active' might already exist or error: {e}")

    try:
        # Add current_session_id column
        cursor.execute("ALTER TABLE user ADD COLUMN current_session_id VARCHAR(36)")
        print("Column 'current_session_id' added.")
    except sqlite3.OperationalError as e:
        print(f"Column 'current_session_id' might already exist or error: {e}")

    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
