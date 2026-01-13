import os
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user, logout_user
from config import Config
from extensions import db, login_manager, csrf
from datetime import datetime
import re # Added for regex in the new filter
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialisation des extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"

    # Custom Jinja2 filter for cleaning HTML in PDF
    def clean_html_for_pdf(html_content):
        """
        Clean Quill HTML output for PDF rendering:
        - Convert <ul><li> lists to <p> elements with bullets (•)
        - Use <p> with inline styles for xhtml2pdf compatibility
        """
        if not html_content:
            return html_content
        
        # Remove <p> tags (Quill wraps content in <p>)
        cleaned = re.sub(r'<p[^>]*>', '', html_content)
        cleaned = re.sub(r'</p>', '', cleaned)
        
        # Convert <li>text</li> to <p style="margin:2px 0 2px 15px; padding:0">• text</p>
        cleaned = re.sub(
            r'<li[^>]*>(.*?)</li>', 
            r'<p style="margin:2px 0 2px 15px; padding:0; line-height:1.3">• \1</p>', 
            cleaned, 
            flags=re.DOTALL
        )
        
        # Remove <ul> and </ul> tags
        cleaned = re.sub(r'</?ul[^>]*>', '', cleaned)
        
        # Remove any <br> tags (we use p now)
        cleaned = re.sub(r'<br\s*/?>', '', cleaned)
        
        # Clean up excessive whitespace
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n+', ' ', cleaned)
        
        return cleaned.strip()

    app.jinja_env.filters['clean_html_for_pdf'] = clean_html_for_pdf

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))

    # Création du dossier instance si nécessaire pour la DB
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Création du dossier archives si nécessaire
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        try:
             os.makedirs(app.config['UPLOAD_FOLDER'])
        except OSError:
            pass

    # Enregistrement des blueprints
    from routes.clients import bp as clients_bp
    app.register_blueprint(clients_bp, url_prefix='/clients')
    
    from routes.devis import bp as devis_bp
    app.register_blueprint(devis_bp, url_prefix='/devis')
    
    from routes.factures import bp as factures_bp
    app.register_blueprint(factures_bp, url_prefix='/factures')

    from routes.avoirs import bp as avoirs_bp
    app.register_blueprint(avoirs_bp, url_prefix='/avoirs')

    from routes.fournisseurs import bp as fournisseurs_bp
    app.register_blueprint(fournisseurs_bp, url_prefix='/fournisseurs')

    from routes.bons_commande import bp as bons_commande_bp
    app.register_blueprint(bons_commande_bp, url_prefix='/bons-commande')

    from routes.documents import bp as documents_bp
    app.register_blueprint(documents_bp, url_prefix='/documents')
    
    from routes.settings import bp as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')

    from routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from routes.users import bp as users_bp
    app.register_blueprint(users_bp, url_prefix='/users')

    from routes.mail import bp as mail_bp
    app.register_blueprint(mail_bp, url_prefix='/mail')

    from routes.chat import bp as chat_bp
    app.register_blueprint(chat_bp, url_prefix='/api/chat')

    from routes.expenses import bp as expenses_bp
    app.register_blueprint(expenses_bp, url_prefix='/expenses')

    from routes.public import bp as public_bp
    app.register_blueprint(public_bp, url_prefix='/')

    @app.before_request
    def before_request():
        if current_user.is_authenticated:
            # Make session permanent to respect PERMANENT_SESSION_LIFETIME
            session.permanent = True
            
            # 1. Check for unique session enforcement
            if 'sid' in session and current_user.current_session_id:
                if session['sid'] != current_user.current_session_id:
                    logout_user()
                    from flask import flash
                    flash("Votre session a été fermée car vous vous êtes connecté sur un autre appareil.", "warning")
                    return redirect(url_for('auth.login'))

            # 2. Check for Forced Ejection (Targeted)
            # Must happen BEFORE updating last_active to prevent "zombie" active status
            if current_user.force_logout_at:
                login_at = session.get('login_at')
                # If login time is unknown OR login happened BEFORE the force logout
                should_logout = False
                
                if not login_at:
                    should_logout = True
                else:
                     # Handle string (serialized) vs datetime
                    if isinstance(login_at, str):
                        try:
                            login_at = datetime.strptime(login_at, '%a, %d %b %Y %H:%M:%S %Z')
                        except:
                            pass
                            
                    if isinstance(login_at, datetime):
                        # Ensure we compare apples to apples (remove timezone if any)
                        login_at_naive = login_at.replace(tzinfo=None)
                        force_logout_naive = current_user.force_logout_at.replace(tzinfo=None)
                        
                        if login_at_naive < force_logout_naive:
                            should_logout = True
                            
                if should_logout:
                     logout_user()
                     session.clear()
                     
                     # Handle API requests with JSON 401
                     if request.path.startswith('/api/') or request.is_json:
                         return jsonify({'error': 'ejected', 'message': 'Session terminated'}), 401
                         
                     from flask import flash
                     flash("Votre session a été terminée par un administrateur.", "danger")
                     return redirect(url_for('auth.login'))

            # 3. Update last active timestamp (Only if NOT ejected)
            current_user.last_active = datetime.utcnow()
            db.session.commit()

    # Inject CompanyInfo globally for templates (Theme, Logo, etc.)
    @app.before_request
    def check_ejection():
        if current_user.is_authenticated and current_user.force_logout_at:
            login_at = session.get('login_at')
            # If login time is unknown OR login happened BEFORE the force logout
            if not login_at:
                 from flask_login import logout_user
                 logout_user()
                 session.clear()
                 flash("Votre session a été terminée par un administrateur.", "danger")
                 return redirect(url_for('auth.login'))
                 
            # Handle string (serialized) vs datetime
            if isinstance(login_at, str):
                try:
                    # Attempt parse if it became a string in session
                    login_at = datetime.strptime(login_at, '%a, %d %b %Y %H:%M:%S %Z')
                except:
                    pass

            if isinstance(login_at, datetime):
                # Ensure we compare apples to apples (remove timezone if any)
                login_at_naive = login_at.replace(tzinfo=None)
                force_logout_naive = current_user.force_logout_at.replace(tzinfo=None)
                
                if login_at_naive < force_logout_naive:
                     from flask_login import logout_user
                     logout_user()
                     session.clear()
                     
                     # Handle API requests with JSON 401
                     if request.path.startswith('/api/') or request.is_json:
                         return jsonify({'error': 'ejected', 'message': 'Session terminated'}), 401
                         
                     flash("Votre session a été terminée par un administrateur.", "danger")
                     return redirect(url_for('auth.login'))
                 
    @app.context_processor
    def inject_global_data():
        from models import CompanyInfo, AISettings
        info = CompanyInfo.query.first()
        ai_settings = AISettings.get_settings()
        return dict(company_info=info, ai_settings=ai_settings)
    
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    @app.route('/api/active-users')
    @login_required
    def active_users_api():
        from models import User
        from datetime import datetime, timedelta
        # Consider users active if they were seen in the last 5 minutes
        five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
        active_users = User.query.filter(User.last_active >= five_mins_ago).all()
        
        return jsonify({
            'count': len(active_users),
            'users': [{
                'id': u.id,
                'username': u.username,
                'is_me': u.id == current_user.id
            } for u in active_users]
        })

    def get_stats():
        from models import Document, Expense
        from sqlalchemy import func, extract
        from datetime import datetime, timedelta
        
        # 1. Filtres
        year_filter = request.args.get('year', type=int)
        date_start_str = request.args.get('start_date')
        date_end_str = request.args.get('end_date')
        
        # Déterminer la période de filtrage
        if date_start_str and date_end_str:
            start_date = datetime.strptime(date_start_str, '%Y-%m-%d')
            end_date = datetime.strptime(date_end_str, '%Y-%m-%d') + timedelta(days=1)
            filter_label = f"du {date_start_str} au {date_end_str}"
            chart_mode = 'daily'
        elif year_filter:
            start_date = datetime(year_filter, 1, 1)
            end_date = datetime(year_filter + 1, 1, 1)
            filter_label = f"Année {year_filter}"
            chart_mode = 'monthly'
        else:
            # Par défaut : Année en cours
            now = datetime.now()
            year_filter = now.year
            start_date = datetime(year_filter, 1, 1)
            end_date = datetime(year_filter + 1, 1, 1)
            filter_label = f"Année {year_filter} (en cours)"
            chart_mode = 'monthly'

        # 2. Obtenir toutes les factures qui n'ont PAS d'avoir associé
        avoir_sources = db.session.query(Document.source_document_id).filter(
            Document.type == 'avoir', 
            Document.source_document_id.isnot(None)
        )
        
        base_query = Document.query.filter(
            Document.type == 'facture',
            Document.date >= start_date,
            Document.date < end_date,
            ~Document.id.in_(avoir_sources)
        )
        
        # 3. Calculs des totaux
        total_ht = db.session.query(func.sum(Document.montant_ht)).filter(
            Document.type == 'facture',
            Document.date >= start_date,
            Document.date < end_date,
            ~Document.id.in_(avoir_sources)
        ).scalar() or 0.0
        
        total_ttc = db.session.query(func.sum(Document.montant_ttc)).filter(
            Document.type == 'facture',
            Document.date >= start_date,
            Document.date < end_date,
            ~Document.id.in_(avoir_sources)
        ).scalar() or 0.0
        
        total_tva = db.session.query(func.sum(Document.tva)).filter(
            Document.type == 'facture',
            Document.date >= start_date,
            Document.date < end_date,
            ~Document.id.in_(avoir_sources)
        ).scalar() or 0.0

        total_autoliq = db.session.query(func.sum(Document.montant_ht)).filter(
            Document.type == 'facture',
            Document.autoliquidation == True,
            Document.date >= start_date,
            Document.date < end_date,
            ~Document.id.in_(avoir_sources)
        ).scalar() or 0.0
        
        total_regle = db.session.query(func.sum(Document.montant_ttc)).filter(
            Document.type == 'facture',
            Document.paid == True,
            Document.date >= start_date,
            Document.date < end_date,
            ~Document.id.in_(avoir_sources)
        ).scalar() or 0.0
        
        total_impaye = total_ttc - total_regle

        # 3b. Calcul des dépenses (Bons de commande fournisseurs + Notes de Frais)
        total_depenses_commandes = db.session.query(func.sum(Document.montant_ht)).filter(
            Document.type == 'bon_de_commande',
            Document.date >= start_date,
            Document.date < end_date
        ).scalar() or 0.0

        total_depenses_expenses = db.session.query(func.sum(Expense.amount_ht)).filter(
            Expense.date >= start_date,
            Expense.date < end_date
        ).scalar() or 0.0
        
        total_depenses = total_depenses_commandes + total_depenses_expenses

        # 3c. Calcul TVA Déductible (Commandes + Notes de Frais)
        tva_commandes = db.session.query(func.sum(Document.tva)).filter(
            Document.type == 'bon_de_commande',
            Document.date >= start_date,
            Document.date < end_date
        ).scalar() or 0.0

        tva_expenses = db.session.query(func.sum(Expense.tva)).filter(
            Expense.date >= start_date,
            Expense.date < end_date
        ).scalar() or 0.0

        total_tva_deductible = tva_commandes + tva_expenses
        
        benefice_net = total_ht - total_depenses
        tva_nette = total_tva - total_tva_deductible
        
        # 4. Données pour le graphique
        monthly_data = []
        monthly_expense_data = []
        labels = []
        
        if chart_mode == 'monthly':
            for month in range(1, 13):
                m_start = datetime(start_date.year, month, 1)
                m_end = datetime(start_date.year + 1, 1, 1) if month == 12 else datetime(start_date.year, month + 1, 1)
                m_total = db.session.query(func.sum(Document.montant_ht)).filter(
                    Document.type == 'facture',
                    Document.date >= m_start,
                    Document.date < m_end,
                    ~Document.id.in_(avoir_sources)
                ).scalar() or 0.0
                
                # Dépenses (Commandes + Frais)
                m_cmd = db.session.query(func.sum(Document.montant_ht)).filter(
                    Document.type == 'bon_de_commande',
                    Document.date >= m_start,
                    Document.date < m_end
                ).scalar() or 0.0
                
                m_exp = db.session.query(func.sum(Expense.amount_ht)).filter(
                    Expense.date >= m_start,
                    Expense.date < m_end
                ).scalar() or 0.0
                
                labels.append(m_start.strftime('%b'))
                monthly_data.append(m_total)
                monthly_expense_data.append(m_cmd + m_exp)
        else:
            delta = end_date - start_date
            step = 1 if delta.days <= 60 else max(1, delta.days // 20)
            curr = start_date
            while curr < end_date:
                next_curr = curr + timedelta(days=step)
                d_total = db.session.query(func.sum(Document.montant_ht)).filter(
                    Document.type == 'facture',
                    Document.date >= curr,
                    Document.date < next_curr,
                    ~Document.id.in_(avoir_sources)
                ).scalar() or 0.0
                
                d_expense = db.session.query(func.sum(Document.montant_ht)).filter(
                    Document.type == 'bon_de_commande',
                    Document.date >= curr,
                    Document.date < next_curr
                ).scalar() or 0.0
                
                labels.append(curr.strftime('%d/%m'))
                monthly_data.append(d_total)
                monthly_expense_data.append(d_expense)
                curr = next_curr

        # 5. Statistiques par Client
        from models import Client
        client_stats_query = db.session.query(
            Client.raison_sociale,
            func.sum(Document.montant_ht).label('total_ht')
        ).join(Document, Document.client_id == Client.id).filter(
            Document.type == 'facture',
            Document.date >= start_date,
            Document.date < end_date,
            ~Document.id.in_(avoir_sources)
        ).group_by(Client.raison_sociale).order_by(func.sum(Document.montant_ht).desc()).limit(10).all()

        client_labels = [row[0] for row in client_stats_query]
        client_data = [float(row[1]) for row in client_stats_query]

        years = db.session.query(extract('year', Document.date)).filter(Document.type == 'facture').distinct().all()
        available_years = sorted([int(y[0]) for y in years if y[0]], reverse=True)
        if datetime.now().year not in available_years:
            available_years.insert(0, datetime.now().year)

        # 6. Statistiques de Conversion (Performance Commerciale)
        # Total Devis créés dans la période
        total_devis = db.session.query(func.count(Document.id)).filter(
            Document.type == 'devis',
            Document.date >= start_date,
            Document.date < end_date
        ).scalar() or 0

        # Devis convertis (ceux qui ont généré une facture)
        # On regarde si le devis a un 'generated_documents' de type facture
        # Note: generated_documents est une relation, mais pour compter efficacement on peut faire une sous-requête ou join
        # Une facture a source_document_id = id_du_devis
        
        # Sous-requête des IDs de devis qui sont source d'une facture
        converted_ids = db.session.query(Document.source_document_id).filter(
            Document.type == 'facture',
            Document.source_document_id.isnot(None)
        )
        
        converted_devis = db.session.query(func.count(Document.id)).filter(
            Document.type == 'devis',
            Document.date >= start_date,
            Document.date < end_date,
            Document.id.in_(converted_ids)
        ).scalar() or 0
        
        conversion_rate = (converted_devis / total_devis * 100) if total_devis > 0 else 0.0

        return {
            'total_ht': total_ht,
            'total_ttc': total_ttc,
            'total_tva': total_tva,
            'total_autoliq': total_autoliq,
            'total_regle': total_regle,
            'total_impaye': total_impaye,
            'total_depenses': total_depenses,
            'total_tva_deductible': total_tva_deductible,
            'tva_nette': tva_nette,
            'benefice_net': benefice_net,
            'monthly_labels': labels,
            'monthly_data': monthly_data,
            'monthly_expense_data': monthly_expense_data,
            'client_labels': client_labels,
            'client_data': client_data,
            'filter_label': filter_label,
            'available_years': available_years,
            'current_year': year_filter,
            'start_date': date_start_str,
            'end_date': date_end_str,
            'total_devis': total_devis,
            'converted_devis': converted_devis,
            'conversion_rate': conversion_rate
        }

    @app.route('/')
    @login_required
    def index():
        from models import CompanyInfo
        info = CompanyInfo.query.first()
        stats = get_stats()
        return render_template('index.html', info=info, stats=stats)

    @app.route('/export_stats_pdf')
    @login_required
    def export_stats_pdf():
        from models import CompanyInfo
        from xhtml2pdf import pisa
        from io import BytesIO
        from flask import make_response
        from datetime import datetime
        
        info = CompanyInfo.query.first()
        stats = get_stats()
        
        static_root = os.path.join(app.root_path, 'static')
        logo_abs_path = ""
        if info and info.logo_path:
            logo_abs_path = os.path.join(static_root, info.logo_path).replace("\\", "/")
            
        html = render_template('stats_pdf.html', stats=stats, info=info, logo_abs_path=logo_abs_path, now=datetime.now())
        
        pdf = BytesIO()
        pisa_status = pisa.CreatePDF(BytesIO(html.encode("utf-8")), dest=pdf)
        
        if pisa_status.err:
             print(f"DEBUG: PDF Generation Error Code {pisa_status.err}")
        
        response = make_response(pdf.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Rapport_STP_{datetime.now().strftime("%Y%m%d")}.pdf'
        return response
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001, host='0.0.0.0')
