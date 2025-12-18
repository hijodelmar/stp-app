import sys
from app import create_app
from extensions import db
from models import User

def create_admin(username, password):
    app = create_app()
    with app.app_context():
        # Check if user exists
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"Mise à jour du mot de passe pour {username}...")
            user.set_password(password)
            user.role = 'admin'
        else:
            print(f"Création de l'administrateur {username}...")
            user = User(username=username, role='admin')
            user.set_password(password)
            db.session.add(user)
        
        db.session.commit()
        print("Opération réussie !")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password>")
    else:
        create_admin(sys.argv[1], sys.argv[2])
