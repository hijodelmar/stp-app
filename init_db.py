from app import create_app
from extensions import db
import os

app = create_app()

with app.app_context():
    db_path = os.path.join(app.instance_path, 'app.db')
    if os.path.exists(db_path):
        print(f"Database already exists at {db_path}")
    else:
        print(f"Creating database at {db_path}")
        db.create_all()
        print("Database initialized successfully.")
