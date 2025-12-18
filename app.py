import os
from flask import Flask, render_template
from flask_login import login_required
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

    @app.route('/')
    @login_required
    def index():
        from models import CompanyInfo
        info = CompanyInfo.query.first()
        return render_template('base.html', info=info)

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001, host='0.0.0.0')
