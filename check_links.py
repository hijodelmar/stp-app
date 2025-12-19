import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app
from models import Document
from extensions import db

app = create_app()

with app.app_context():
    # Find all devis
    devis_list = Document.query.filter(Document.type == 'devis').all()
    print(f"Total Devis found: {len(devis_list)}")
    
    for d in devis_list:
        # Check generated_documents via relationship
        links = d.generated_documents
        invoices = [l for l in links if l.type == 'facture']
        
        if invoices:
            print(f"✅ Devis {d.numero} (ID: {d.id}) is linked to Invoices: {[i.numero for i in invoices]}")
        
        # Manual check to compare
        manual_invoices = Document.query.filter_by(type='facture', source_document_id=d.id).all()
        if manual_invoices and not invoices:
            print(f"⚠️ DISCREPANCY: Devis {d.numero} (ID: {d.id}) has manual links {[i.numero for i in manual_invoices]} but relationship is empty!")
        
    # Check if there are any invoices at all
    factures = Document.query.filter_by(type='facture').all()
    print(f"\nTotal Factures found: {len(factures)}")
    with_source = [f for f in factures if f.source_document_id is not None]
    print(f"Factures with source_document_id: {len(with_source)}")
    for f in with_source:
        print(f"  Facture {f.numero} -> Source ID: {f.source_document_id}")
