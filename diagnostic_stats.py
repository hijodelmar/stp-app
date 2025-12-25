from app import create_app
from extensions import db
from models import Document, Client
from sqlalchemy import func
from datetime import datetime

app = create_app()
with app.app_context():
    start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Check total invoices this month
    count = Document.query.filter(Document.type == 'facture', Document.date >= start_date).count()
    print(f"Total invoices this month: {count}")
    
    # Check top clients
    avoir_sources = db.session.query(Document.source_document_id).filter(
        Document.type == 'avoir', 
        Document.source_document_id.isnot(None)
    ).subquery()

    client_stats = db.session.query(
        Client.raison_sociale,
        func.sum(Document.montant_ht).label('total_ht')
    ).join(Document, Document.client_id == Client.id).filter(
        Document.type == 'facture',
        Document.date >= start_date,
        ~Document.id.in_(avoir_sources)
    ).group_by(Client.raison_sociale).order_by(func.sum(Document.montant_ht).desc()).all()
    
    print("Top Clients this month:")
    for c in client_stats:
        print(f"- {c[0]}: {c[1]}€")
