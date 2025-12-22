from models import Document
from extensions import db

def generate_document_number(prefix, year):
    """
    Generates a robust document number in the format PREFIX-YEAR-XXXX.
    Instead of counting, it finds the maximum existing number and increments it.
    """
    pattern = f'{prefix}-{year}-%'
    
    # Get all numbers for this year and prefix
    documents = Document.query.filter(Document.numero.like(pattern)).all()
    
    max_num = 0
    for doc in documents:
        try:
            # Extract XXXX from PREFIX-YEAR-XXXX
            parts = doc.numero.split('-')
            if len(parts) == 3:
                num = int(parts[2])
                if num > max_num:
                    max_num = num
        except (ValueError, IndexError):
            continue
            
    next_num = max_num + 1
    return f'{prefix}-{year}-{next_num:04d}'
