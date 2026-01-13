from services.ai_agent import GoogleProvider
from models import AISettings
import json
import re

def extract_expense_data(image_path):
    """
    Extracts expense data using AI (Gemini) instead of regex.
    Returns a dict with: date, amount_ttc, tva, amount_ht, category, description, supplier.
    """
    print(f"AI OCR: Processing {image_path}...")
    
    settings = AISettings.get_settings()
    if not settings.enabled:
        return {"error": "AI is disabled in settings"}
        
    if settings.provider != 'google':
         # OpenAI vision not implemented yet in this simplified provider, easy to add if needed
         return {"error": "Only Google Gemini is supported for OCR currently."}

    try:
        provider = GoogleProvider(settings.api_key, settings.model_name)
        
        prompt = """
        Tu es un expert comptable. Analyse cette image de ticket de caisse / facture.
        Extrais les informations suivantes au format JSON UNIQUEMENT (pas de markdown) :
        {
            "date": "dd/mm/yyyy", (La date du ticket)
            "amount_ttc": 0.00, (Le montant total à payer)
            "tva": 0.00, (Le montant total de la TVA)
            "amount_ht": 0.00, (Le montant HT, ou TTC - TVA)
            "category": "string", (choisis une des catégories : restaurant, transport, material, urssaf, salary, other)
            "description": "string", (Nom du commerçant + brève description ex: 'Restaurant Le Saes', 'Total Station Essence')
            "supplier": "string" (Nom du fournisseur/commerçant seul)
        }
        
        Règles pour la catégorie :
        - restaurant : repas, bar, hotel
        - transport : essence, peage, taxi, train, avion, parking
        - material : bricolage, fournitures bureau, informatique, materiel
        - urssaf : charges sociales
        - salary : salaire
        - other : tout le reste
        
        Si une valeur est introuvable, mets null.
        Réponds uniquement avec le JSON valide.
        """
        
        response_text = provider.generate_with_image(prompt, image_path)
        print(f"AI OCR Raw Response: {response_text}")
        
        # Clean markdown
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        data = json.loads(response_text)
        
        # Ensure numbers are floats (AI sometimes returns strings)
        for field in ['amount_ttc', 'tva', 'amount_ht']:
            if data.get(field):
                try:
                    data[field] = float(data[field])
                except:
                    data[field] = 0.0
        
        return data

    except Exception as e:
        print(f"AI OCR Error: {e}")
        return {"error": str(e)}
