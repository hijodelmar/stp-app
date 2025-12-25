import logging
from flask import Blueprint, request, jsonify, session
from flask_login import login_required
from services.chat_executor import ChatExecutor
from services.ai_agent import AIAgent

logger = logging.getLogger(__name__)

bp = Blueprint('chat', __name__)

executor = ChatExecutor()
# AI Agent is initialized lazily or here if env var is ready
try:
    agent = AIAgent()
except Exception as e:
    print(f"Warning: AI Agent not initialized: {e}")
    agent = None

@bp.route('/send', methods=['POST'])
@login_required
def send_message():
    try:
        if agent:
            agent.refresh_settings()

        if not agent or not agent.provider:
            return jsonify({
                "reply": "L'assistant IA est actuellement désactivé ou non configuré.",
                "status": "disabled"
            })
            
        user_input = request.json.get('message')
        if not user_input:
            return jsonify({"error": "No message provided."}), 400

        # 1. Get Context (Session + Manual Activity)
        chat_context = session.get('chat_context', {})
        
        # Fetch recent manual activity for learning
        activity_check = executor.get_recent_activity()
        activity_context = activity_check.get('data', []) if activity_check.get('status') == 'success' else []

        # 2. Understand Intent (with context)
        ai_response = agent.generate_response(user_input, context=chat_context, external_activity=activity_context)
        
        # Standardize to list for processing
        if isinstance(ai_response, dict) and ai_response.get('action') == 'error':
            return jsonify({
                "reply": ai_response.get('reply', "An error occurred."),
                "status": "error"
            })
            
        commands = ai_response if isinstance(ai_response, list) else [ai_response]
        
        # 3. Execute Commands
        execution_results = []
        final_reply = ""
        last_action = "message"

        for cmd in commands:
            if not isinstance(cmd, dict): continue
            
            action = cmd.get('action')
            last_action = action
            
            if action == 'message':
                final_reply = cmd.get('reply')
                execution_results.append({"action": action, "status": "success", "data": cmd.get('data')})
                continue

            res = executor.execute(cmd, context=chat_context)
            execution_results.append({"action": action, "result": res})
            
            # 4. Update Context after each step
            if res.get('status') == 'success':
                res_data = res.get('data', {})
                if isinstance(res_data, dict):
                    if res_data.get('type') == 'client' or res_data.get('client_id'):
                        chat_context['last_client_id'] = res_data.get('id') or res_data.get('client_id')
                        chat_context['last_client_name'] = res_data.get('name')
                    
                    if res_data.get('document_number'):
                        chat_context['last_document_number'] = res_data.get('document_number')
                        chat_context['last_document_id'] = res_data.get('id')
                    
                    session['chat_context'] = chat_context

        # 5. Global Reply Formatting
        if len(execution_results) > 0:
            if not any(r['action'] != 'message' for r in execution_results):
                 first_cmd = commands[0] if len(commands) > 0 else {}
                 if isinstance(first_cmd, dict):
                     final_reply = first_cmd.get('reply') or first_cmd.get('data', {}).get('text') or "Message reçu."
                 else:
                     final_reply = str(first_cmd)
            else:
                 try:
                     final_reply = agent.format_result(user_input, ai_response, execution_results)
                 except Exception as fe:
                     logger.error(f"Format result error: {fe}")
                     final_reply = "Opération terminée. J'ai mis à jour les informations demandées."

        if not final_reply and len(execution_results) == 0:
            final_reply = "Je n'ai pas pu traiter votre demande. Pouvez-vous reformuler ?"

        return jsonify({
            "reply": final_reply,
            "action": last_action,
            "results": execution_results
        })
    except Exception as e:
        logger.error(f"General chat error: {e}")
        return jsonify({
            "reply": f"Désolé, une erreur interne est survenue : {str(e)}",
            "status": "error"
        }), 500

@bp.route('/reset', methods=['POST'])
@login_required
def reset_chat():
    session.pop('chat_context', None)
    return jsonify({"status": "success", "message": "Context reset."})
