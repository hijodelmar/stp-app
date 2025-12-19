import os
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_login import login_required, current_user, logout_user
from config import Config
from extensions import db, login_manager

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialisation des extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"

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

    from routes.documents import bp as documents_bp
    app.register_blueprint(documents_bp, url_prefix='/documents')
    
    from routes.settings import bp as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')

    from routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from routes.users import bp as users_bp
    app.register_blueprint(users_bp, url_prefix='/users')

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

            # 2. Update last active timestamp
            from datetime import datetime
            current_user.last_active = datetime.utcnow()
            db.session.commit()

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
        from models import Document
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
        ).subquery()
        
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
        
        # 4. Données pour le graphique
        monthly_data = []
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
                labels.append(m_start.strftime('%b'))
                monthly_data.append(m_total)
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
                labels.append(curr.strftime('%d/%m'))
                monthly_data.append(d_total)
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

        return {
            'total_ht': total_ht,
            'total_ttc': total_ttc,
            'total_tva': total_tva,
            'total_autoliq': total_autoliq,
            'total_regle': total_regle,
            'total_impaye': total_impaye,
            'monthly_labels': labels,
            'monthly_data': monthly_data,
            'client_labels': client_labels,
            'client_data': client_data,
            'filter_label': filter_label,
            'available_years': available_years,
            'current_year': year_filter,
            'start_date': date_start_str,
            'end_date': date_end_str
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
