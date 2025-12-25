import os
import json
from datetime import datetime
from models import AISettings

class AIAgent:
    def __init__(self):
        self.settings = None
        self.provider = None
        self.refresh_settings()

    def refresh_settings(self):
        """Reload settings from DB and re-initialize provider."""
        from extensions import db
        try:
            self.settings = AISettings.get_settings()
            if not self.settings.enabled:
                self.provider = None
                return

            if self.settings.provider == 'google':
                self.provider = GoogleProvider(self.settings.api_key, self.settings.model_name)
            elif self.settings.provider == 'openai':
                self.provider = OpenAIProvider(self.settings.api_key, self.settings.model_name)
        except Exception as e:
            print(f"AI Agent: Error loading settings: {e}")
            self.provider = None

    def generate_response(self, user_input, context=None, external_activity=None):
        if not self.provider:
            return {"action": "error", "reply": "Assistant désactivé ou erreur de configuration."}
            
        prompt = self._build_system_prompt(user_input, context, external_activity)
        
        try:
            content = self.provider.generate(prompt)
            print(f"AI Agent Raw Output: {content}")
            # Clean up potential markdown code blocks
            clean_content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                command = json.loads(clean_content)
                return command
            except json.JSONDecodeError:
                return {
                    "action": "message", 
                    "data": {"text": clean_content},
                    "reply": clean_content
                }
        except Exception as e:
            return {"action": "error", "reply": f"Erreur de connexion à l'IA : {str(e)}"}

    def format_result(self, user_input, command, results):
        if not self.provider: return "Opération terminée."
        
        res_list = results if isinstance(results, list) else [{"result": results}]
        errors = [r['result'].get('message') for r in res_list if 'result' in r and r['result'].get('status') == 'error']
        if errors:
            return f"Je suis désolé, une erreur s'est produite : {errors[0]}"

        simplified_results = []
        pdf_urls = []
        from flask import request
        host_url = request.host_url.rstrip('/')

        for r in res_list:
            action = r.get('action')
            res_val = r.get('result', r)
            data = res_val.get('data', {})
            
            if isinstance(data, dict) and data.get('pdf_url'):
                url = data['pdf_url']
                if url.startswith('/'): url = f"{host_url}{url}"
                pdf_urls.append(url)
            
            simplified_results.append({
                "action": action or (command.get('action') if isinstance(command, dict) else "unknown"),
                "status": res_val.get('status'),
                "message": res_val.get('message'),
                "data": data
            })

        prompt = f"""
Tu es l'assistant de gestion STP. Tu viens d'exécuter des actions.
**RÈGLE D'OR : RÉPONSE EN FRANÇAIS UNIQUEMENT.**

DEMANDE UTILISATEUR : "{user_input}"
RÉSULTATS DES ACTIONS (JSON) : {json.dumps(simplified_results)}

CONSIGNES :
1. Rédige une réponse professionnelle et concise résumant ce qui a été fait.
2. Ne sois pas technique. Ne mentionne pas de JSON ou de termes système.
3. Si les données contiennent "top_clients", tu DOIS citer nommément le client en haut de la liste.
4. Pour les rapports financiers, donne le détail : HT, TVA, TTC, Encaissements.
5. Pas d'émoticônes. Pas de markdown complexe.
6. Si des liens PDF sont présents ({", ".join(pdf_urls)}), inclus les à la fin.

RÉPONSE FINALE :
"""
        try:
            return self.provider.generate(prompt).strip()
        except Exception:
            return "Opération terminée avec succès."

    def _build_system_prompt(self, user_input, context=None, external_activity=None):
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        context = context or {}
        activity = external_activity or []
        
        # Format context for prompt
        context_str = f"Dernier Client ID: {context.get('last_client_id', 'None')}\n"
        context_str += f"Nom Dernier Client: {context.get('last_client_name', 'None')}\n"
        context_str += f"Dernier Document #: {context.get('last_document_number', 'None')}\n"
        
        activity_str = "\n".join([f"- {a}" for a in activity]) if activity else "Aucune activité manuelle récente."

        return f"""
Tu es l'assistant IA de gestion pour l'entreprise STP (Plomberie/Bâtiment).
Ton rôle est d'aider l'utilisateur à gérer ses documents et clients de manière fluide.

**RÈGLE CRUCIALE : TU DOIS RÉPONDRE EXCLUSIVEMENT EN FRANÇAIS.**
Le champ `reply` doit contenir ce que tu DIRAIS à l'utilisateur. Ne décris pas tes actions (ex: au lieu de "Information sur la régénération...", dis "J'ai mis à jour le document, voici le nouveau lien").

Date actuelle: {now}

CONTEXTE (Dernières interactions chat):
{context_str}

ACTIVITÉ RÉCENTE (Actions faites manuellement dans l'interface):
{activity_str}

RÈGLES DE RÉPONSE :
1. Tu dois sortir EXCLUSIVEMENT du JSON valide.
2. Si la demande nécessite plusieurs étapes, retourne une LISTE JSON d'objets : `[ {{ "action": "..."}}, {{"action": "..."}} ]`.
3. Pas de formatage markdown dans la réponse JSON.
4. SOIS NATUREL, parle comme un collègue serviable. Évite les phrases robotiques.
5. Si l'utilisateur mentionne "ce devis", "lui", "ce client", sers-toi du CONTEXTE pour trouver l'ID.
6. La génération PDF est automatique. Quand tu reçois un `pdf_url` du système, affiche-le CLAIREMENT à l'utilisateur pour qu'il puisse cliquer dessus.

ACTIONS DISPONIBLES :

1. **create_client**
   {{ "action": "create_client", "data": {{ "raison_sociale": "Nom", "email": "...", "telephone": "..." }}, "reply": "Création du client..." }}

2. **list_clients**
   {{ "action": "list_clients", "data": {{ "limit": 5 }}, "reply": "Recherche des clients..." }}

3. **add_contact**
   {{ "action": "add_contact", "data": {{ "client_name": "Nom", "nom": "Nom Famille", "prenom": "Prénom", "email": "...", "telephone": "..." }}, "reply": "Ajout du contact..." }}

4. **create_supplier**
   {{ "action": "create_supplier", "data": {{ "raison_sociale": "Nom" }}, "reply": "Création du fournisseur..." }}

5. **list_suppliers**
   {{ "action": "list_suppliers", "data": {{ "limit": 10 }}, "reply": "Liste des fournisseurs..." }}

6. **list_documents**
   {{ "action": "list_documents", "data": {{ "type": "facture", "timeframe": "this_month" }}, "reply": "Recherche des documents..." }}

7. **create_document**
   Type: 'devis', 'facture', 'avoir', 'bon_de_commande'.
   **IMPORTANT**: Ne crée JAMAIS un document vide. Si l'utilisateur demande un devis sans détails, DEMANDE-LUI d'abord les articles (désignation, quantité, prix).
   Si les détails sont fournis, tu peux enchaîner `create_document` suivi de plusieurs `add_line`.
   {{ "action": "create_document", "data": {{ "type": "devis", "client_name": "Nom" }}, "reply": "Création du document..." }}

8. **add_line**
   {{ "action": "add_line", "data": {{ "document_number": "D-2025-...", "designation": "Nom article", "quantite": 1, "prix_unitaire": 100 }}, "reply": "Ajout de la ligne..." }}

9. **convert_document**
   {{ "action": "convert_document", "data": {{ "source_number": "D-2025-..." }}, "reply": "Conversion du document..." }}

10. **send_email**
   {{ "action": "send_email", "data": {{ "document_number": "F-2025-...", "recipient_name": "..." }}, "reply": "Envoi de l'email..." }}

11. **get_stats**
    {{ "action": "get_stats", "data": {{ "timeframe": "this_month" }}, "reply": "Analyse des statistiques..." }}
    *Note*: Pour "Top clients", "TVA", "Chiffre d'affaires".

12. **message** (Chat général)
    {{ "action": "message", "data": {{ "text": "Texte de réponse" }}, "reply": "Texte de réponse" }}

**CONSIGNES POUR LES LIENS** :
Quand une action retourne un `pdf_url`, inclus TOUJOURS ce lien dans ta réponse finale (dans le champ `reply` ou via l'action `message`) pour que l'utilisateur puisse cliquer dessus.

USER INPUT: "{user_input}"
JSON RESPONSE:
"""

class GoogleProvider:
    def __init__(self, api_key, model_name=None):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Try several names to find a working one
        models_to_try = []
        if model_name:
            models_to_try.append(model_name)
            if not model_name.endswith('-latest'):
                models_to_try.append(f"{model_name}-latest")
        
        models_to_try.extend([
            'gemini-1.5-flash-latest',
            'gemini-1.5-flash',
            'gemini-pro-latest',
            'gemini-pro'
        ])
        
        self.model = None
        last_err = None
        for name in models_to_try:
            try:
                # Remove prefixes if user added them, library adds them
                clean_name = name.split('/')[-1]
                m = genai.GenerativeModel(clean_name)
                # Verify it's reachable
                m.generate_content("ping", generation_config={"max_output_tokens": 1})
                self.model = m
                print(f"AI Agent: Modèle [{clean_name}] chargé avec succès.")
                break
            except Exception as e:
                last_err = e
                continue
                
        if not self.model:
            print(f"AI Agent Fatal Error: Aucun modèle n'a pu être chargé. Dernier erreur: {last_err}")
            # Fallback for constructor safety
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')

    def generate(self, prompt):
        response = self.model.generate_content(prompt)
        return response.text

class OpenAIProvider:
    def __init__(self, api_key, model_name=None):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model_name or 'gpt-4o-mini'

    def generate(self, prompt):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content
