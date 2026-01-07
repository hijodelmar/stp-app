import pytesseract
from PIL import Image
import re
from datetime import datetime

# Windows path configuration (Common default, but might need adjustment)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_expense_data(image_path):
    """
    Extracts date, amount, VAT, HT, and category from an image.
    Returns a dict with found values.
    """
    try:
        text = pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        print(f"OCR Failed: {e}")
        return {}

    data = {
        'date': None,
        'amount_ttc': None,
        'tva': None,
        'amount_ht': None,
        'category': 'other',
        'supplier': None
    }
    
    # 1. Date Extraction (DD/MM/YYYY or DD-MM-YYYY)
    date_match = re.search(r'(\d{2})[/-](\d{2})[/-](\d{4})', text)
    if date_match:
        try:
            day, month, year = date_match.groups()
            data['date'] = f"{day}/{month}/{year}" # Return as string for form consumption
        except:
            pass
            
    # 2. Amount Extraction (Look for largest number with currency or "Total")
    # Finds pattern like 12.50 or 12,50
    amounts = re.findall(r'(\d+[.,]\d{2})(?:\s?€)?', text)
    if amounts:
        # Normalize and convert to floats
        valid_amounts = []
        for amt in amounts:
            try:
                val = float(amt.replace(',', '.'))
                valid_amounts.append(val)
            except:
                pass
        if valid_amounts:
            data['amount_ttc'] = max(valid_amounts) # Assumption: Max amount is Total
            
    # 3. TVA Extraction
    # Look for "TVA" or "%" followed by amount
    tva_match = re.search(r'(?:TVA|Taxe|Total TVA).*?(\d+[.,]\d{2})', text, re.IGNORECASE)
    if tva_match:
         try:
            data['tva'] = float(tva_match.group(1).replace(',', '.'))
         except:
             pass
             
    # 4. HT Calculation
    if data['amount_ttc'] and data['tva']:
        data['amount_ht'] = round(data['amount_ttc'] - data['tva'], 2)
    elif data['amount_ttc']:
        # Fallback: estimate HT if explicit line not found? No, better leave empty.
        pass

    # 5. Category Detection
    text_lower = text.lower()
    keywords = {
        'restaurant': ['restaurant', 'bar', 'café', 'déjeuner', 'diner', 'mcdo', 'kebab', 'pizza'],
        'transport': ['uber', 'taxi', 'sncf', 'train', 'essence', 'total', 'peage', 'parking'],
        'material': ['amazon', 'fnac', 'bureau', 'informatique', 'leroy', 'castorama'],
        'urssaf': ['urssaf'],
        'salary': ['salaire', 'paie']
    }
    
    for cat, words in keywords.items():
        if any(word in text_lower for word in words):
            data['category'] = cat
            break
            
    return data
