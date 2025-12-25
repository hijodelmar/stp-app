from app import create_app
from extensions import db
from models import Document, Client
from sqlalchemy import func
from datetime import datetime

app = create_app()
with app.app_context():
    start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    stats = db.session.query(Client.raison_sociale, func.sum(Document.montant_ht))\
        .join(Document, Document.client_id == Client.id)\
        .filter(Document.type=='facture', Document.date >= start_date)\
        .group_by(Client.raison_sociale)\
        .order_by(func.sum(Document.montant_ht).desc()).all()
    print("DEBUG_STATS_START")
    for s in stats:
        print(f"CLIENT: {s[0]} | TOTAL: {s[1]}")
    print("DEBUG_STATS_END")
