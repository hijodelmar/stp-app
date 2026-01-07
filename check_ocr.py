import pytesseract
import shutil

# Configuration explicite pour le test Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def check_tesseract():
    print("--- Diagnostic OCR (Tesseract) ---")
    
    # 1. Check configured path or PATH
    try:
        version = pytesseract.get_tesseract_version()
        print(f"[OK] Tesseract fonctionnel ! Version : {version}")
        return True
    except Exception as e:
        print(f"[ERREUR] Tesseract inaccessible : {e}")
    else:
        print("[AVERTISSEMENT] 'tesseract' n'est pas dans le PATH système.")
        print("L'OCR ne fonctionnera pas tant que Tesseract n'est pas installé sur la machine.")
        print("Lien de téléchargement : https://github.com/UB-Mannheim/tesseract/wiki")
        return False

if __name__ == "__main__":
    check_tesseract()
