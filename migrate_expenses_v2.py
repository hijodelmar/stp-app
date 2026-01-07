from app import create_app, db
from models import ExpenseAttachment
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Check if table exists
    inspector = db.inspect(db.engine)
    if 'expense_attachment' not in inspector.get_table_names():
        print("Creating expense_attachment table...")
        ExpenseAttachment.__table__.create(db.engine)
        print("Table 'expense_attachment' created successfully.")
    else:
        print("Table 'expense_attachment' already exists.")

    print("Migration complete.")
