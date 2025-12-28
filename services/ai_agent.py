import os
import json
from datetime import datetime
from models import AISettings

class AIAgent:
    def __init__(self):
        self.settings = None
        self.provider = None
        self.last_error = None
        self.refresh_settings()

    def refresh_settings(self):
        """Reload settings from DB and re-initialize provider."""
        from extensions import db
        try:
            # Force refresh to ensure we have latest data on PA
            db.session.expire_all()
            self.settings = AISettings.get_settings()
            
            if not self.settings or not self.settings.enabled:
                self.provider = None
                self.last_error = "L'assistant IA est désactivé dans les paramètres."
                return

            api_key = (self.settings.api_key or "").strip()
            if not api_key:
                self.provider = None
                self.last_error = "Clé API manquante dans les paramètres."
                return

            if self.settings.provider == 'google':
                self.provider = GoogleProvider(api_key, self.settings.model_name)
                self.last_error = None
            elif self.settings.provider == 'openai':
                self.provider = OpenAIProvider(api_key, self.settings.model_name)
                self.last_error = None
        except Exception as e:
            err_msg = f"Erreur d'initialisation : {str(e)}"
            print(f"AI Agent: {err_msg}")
            self.last_error = err_msg
            self.provider = None

    def generate_response(self, user_input, context=None, external_activity=None):
        if not self.provider:
            return {"action": "error", "reply": self.last_error or "Assistant non configuré."}
            
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

**RÈGLE DE VALIDATION (CRUCIAL)** :
Pour toute action **sensible** (Suppression, Modification d'un document existant, ou Envoi d'email), tu ne dois PAS envoyer l'action technique immédiatement si c'est la première fois que l'utilisateur en parle.
*   **Étape 1 (Proposition)** : Décris ce que tu vas faire et demande explicitement : "Voulez-vous que je réalise cette action ?". Utilise uniquement l'action `message` à cette étape.
*   **Étape 2 (Exécution)** : N'inclus l'action technique (`delete_...`, `update_...`, `send_email`) QUE si l'utilisateur a confirmé (ex: "Oui", "Fais-le", "Ok", "Je confirme").

ACTIONS DISPONIBLES :

### Gestion des Clients & Fournisseurs
1. **create_client** / **create_supplier**
   {{ "action": "create_client", "data": {{ "raison_sociale": "Nom", "email": "...", "telephone": "..." }}, "reply": "Création..." }}
2. **list_clients** / **list_suppliers**
   {{ "action": "list_clients", "data": {{ "limit": 10 }}, "reply": "Recherche..." }}
3. **update_client** / **update_supplier** (Sujet à VALIDATION)
   {{ "action": "update_client", "data": {{ "client_name": "Nom", "adresse": "...", "email": "..." }}, "reply": "Mise à jour..." }}
4. **delete_client** / **delete_supplier** (Sujet à VALIDATION)
   {{ "action": "delete_client", "data": {{ "client_name": "Nom" }}, "reply": "Suppression..." }}
5. **add_contact**
   {{ "action": "add_contact", "data": {{ "client_name": "Nom", "nom": "Last", "prenom": "First" }}, "reply": "Ajout..." }}

### Gestion des Documents (Devis, Factures, Avoirs, BC)
6. **create_document**
   Type: 'devis', 'facture', 'avoir', 'bon_de_commande'.
   **IMPORTANT**: Ne crée JAMAIS un document vide. Demande d'abord les articles.
   {{ "action": "create_document", "data": {{ "type": "devis", "client_name": "Nom" }}, "reply": "Création..." }}
7. **add_line**
   {{ "action": "add_line", "data": {{ "document_number": "D-2025-...", "designation": "Article", "quantite": 1, "prix_unitaire": 100 }}, "reply": "Ajout ligne..." }}
8. **delete_line** (Sujet à VALIDATION)
   {{ "action": "delete_line", "data": {{ "document_number": "...", "designation": "..." }}, "reply": "Suppression ligne..." }}
9. **update_document** (Sujet à VALIDATION)
   {{ "action": "update_document", "data": {{ "document_number": "...", "paid": true, "date": "2025-01-01" }}, "reply": "Modification..." }}
10. **list_documents**
    {{ "action": "list_documents", "data": {{ "type": "facture", "timeframe": "this_month" }}, "reply": "Recherche..." }}
11. **view_document**
    {{ "action": "view_document", "data": {{ "document_number": "..." }}, "reply": "Voici le document..." }}
12. **delete_document** (Sujet à VALIDATION)
    {{ "action": "delete_document", "data": {{ "document_number": "..." }}, "reply": "Suppression document..." }}
13. **convert_document** (Devis -> Facture)
    {{ "action": "convert_document", "data": {{ "source_number": "..." }}, "reply": "Conversion..." }}

### Email & Stats
14. **send_email** (Sujet à VALIDATION)
    {{ "action": "send_email", "data": {{ "document_number": "...", "recipient_name": "..." }}, "reply": "Envoi de l'email..." }}
15. **get_stats**
    {{ "action": "get_stats", "data": {{ "timeframe": "this_month" }}, "reply": "Analyse..." }}

### Chat & Divers
16. **message** (Réponse simple, proposition, ou validation)
    {{ "action": "message", "data": {{ "text": "Ma réponse ici..." }}, "reply": "Ma réponse ici..." }}
17. **reset** (Remet à zéro le contexte/la mémoire)
    {{ "action": "reset", "data": {{ }}, "reply": "Mémoire effacée." }}

**CONSIGNES POUR LES LIENS** :
Quand une action retourne un `pdf_url`, inclus TOUJOURS ce lien dans ta réponse finale pour que l'utilisateur puisse cliquer dessus.

USER INPUT: "{user_input}"
JSON RESPONSE:
"""

class GoogleProvider:
    def __init__(self, api_key, model_name=None):
        if not api_key:
            raise ValueError("Clé API manquante. Veuillez la configurer dans les paramètres.")
            
        import google.generativeai as genai
        # Force 'rest' transport for PythonAnywhere proxy compatibility
        genai.configure(api_key=api_key, transport='rest')
        
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
