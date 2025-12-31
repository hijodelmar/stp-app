import sys
from app import create_app
from extensions import db
from models import User

def create_admin(username, password):
    app = create_app()
    with app.app_context():
        from models import Role
        # Ensure 'admin' role exists
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrateur complet')
            db.session.add(admin_role)
            db.session.commit()

        # Check if user exists
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"Mise à jour du mot de passe pour {username}...")
            user.set_password(password)
            if admin_role not in user.roles:
                user.roles.append(admin_role)
        else:
            print(f"Création de l'administrateur {username}...")
            user = User(username=username)
            user.set_password(password)
            user.roles.append(admin_role)
            db.session.add(user)
        
        db.session.commit()
        print("Opération réussie !")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password>")
    else:
        create_admin(sys.argv[1].lower(), sys.argv[2])
