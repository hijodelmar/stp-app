from app import create_app, db
from models import Expense, ExpenseAttachment
import os

app = create_app()

with app.app_context():
    print("Starting migration of legacy proofs...")
    
    # filters for expenses that have a proof_path but NO attachments yet
    expenses = Expense.query.filter(Expense.proof_path.isnot(None)).all()
    
    count = 0
    for expense in expenses:
        # Check if already migrated (avoid duplicates if script runs twice)
        existing = ExpenseAttachment.query.filter_by(
            expense_id=expense.id, 
            file_path=expense.proof_path
        ).first()
        
        if not existing:
            # Extract filename from path
            filename = os.path.basename(expense.proof_path)
            
            attachment = ExpenseAttachment(
                expense_id=expense.id,
                file_path=expense.proof_path,
                filename=filename,
                created_at=expense.date # Use expense date as approximation
            )
            db.session.add(attachment)
            count += 1
            print(f"Migrating: {filename} (ID: {expense.id})")
    
    if count > 0:
        db.session.commit()
        print(f"Successfully migrated {count} legacy proofs to attachments.")
    else:
        print("No legacy proofs needed migration.")
