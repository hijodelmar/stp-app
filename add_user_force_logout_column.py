from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Migrating User table...")
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE user ADD COLUMN force_logout_at DATETIME"))
            conn.commit()
        print("Successfully added 'force_logout_at' column to 'user' table.")
    except Exception as e:
        print(f"Error (might already exist): {e}")

    print("Migration Check Complete.")
