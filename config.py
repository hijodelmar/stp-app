import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-me-in-prod'
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'archives')
    
    # Session configurations
    from datetime import timedelta
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Backup Configuration
    BACKUP_FOLDER = os.path.join(basedir, 'backups')
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "Europe/Paris"


