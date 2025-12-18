import zipfile
import re
import sys
import os

def read_odt(path):
    print(f"\n--- Reading {path} ---")
    if not os.path.exists(path):
        print("File not found.")
        return

    try:
        with zipfile.ZipFile(path, 'r') as z:
            content = z.read('content.xml').decode('utf-8')
            # Extract text
            text = re.sub('<[^>]+>', ' ', content)
            text = re.sub('\s+', ' ', text).strip()
            
            # Search for keywords
            keywords = ["Bon pour accord", "Signature", "Date", "Avoir", "Total", "Conditions"]
            for kw in keywords:
                if kw in text:
                    print(f"FOUND: '{kw}'")
                    # Show context
                    idx = text.find(kw)
                    print(f"CONTEXT: ...{text[idx-50:idx+50]}...")
            
    except Exception as e:
        print(f"Error: {e}")

read_odt('d:/websites/stp/templates/devis/Devis2.odt')
read_odt('d:/websites/stp/templates/avoirs/Avoir_avec_logo.odt')
