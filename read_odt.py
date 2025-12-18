import zipfile
import re
import sys
import os

def read_odt(path):
    print(f"--- Rading {path} ---")
    if not os.path.exists(path):
        print("File not found.")
        return

    try:
        with zipfile.ZipFile(path, 'r') as z:
            content = z.read('content.xml').decode('utf-8')
            # Very basic strip tags
            text = re.sub('<[^>]+>', ' ', content)
            # Normalize spaces
            text = re.sub('\s+', ' ', text).strip()
            print(text[:2000]) # Print first 2000 chars
    except Exception as e:
        print(f"Error reading ODT: {e}")

read_odt('d:/websites/stp/templates/devis/Devis2.odt')
read_odt('d:/websites/stp/templates/avoirs/Avoir_avec_logo.odt')
