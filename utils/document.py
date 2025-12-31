from models import Document
from extensions import db

def generate_document_number(prefix, year):
    """
    Generates a robust document number in the format PREFIX-YEAR-XXXX.
    Increments based on the highest existing suffix and verifies availability.
    """
    pattern = f'{prefix}-{year}-%'
    
    # Get all matching numbers to find the true maximum suffix
    documents = Document.query.filter(Document.numero.like(pattern)).all()
    
    max_num = 0
    for doc in documents:
        try:
            # Suffix is the last part: F-2025-0001 -> 0001
            parts = doc.numero.split('-')
            if len(parts) >= 3:
                num = int(parts[-1]) # Use parts[-1] to be safer if number format varies
                if num > max_num:
                    max_num = num
        except (ValueError, IndexError):
            continue
            
    next_num = max_num + 1
    
    # FINAL SAFETY: Check if the candidate number already exists (collision protection)
    while True:
        candidate = f'{prefix}-{year}-{next_num:04d}'
        # We check across ALL documents, not just matching the prefix, to be 100% sure
        existing = Document.query.filter_by(numero=candidate).first()
        if not existing:
            return candidate
        next_num += 1
