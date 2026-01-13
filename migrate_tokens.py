from app import create_app
from extensions import db
from models import Document
import uuid

app = create_app()

with app.app_context():
    print("Checking for documents without secure token...")
    documents = Document.query.filter_by(secure_token=None).all()
    
    if not documents:
        print("All documents already have a secure token.")
    else:
        print(f"Found {len(documents)} documents to update.")
        for doc in documents:
            doc.secure_token = str(uuid.uuid4())
            print(f"Assigning token to Document N°{doc.numero}")
        
        db.session.commit()
        print("Migration completed.")
