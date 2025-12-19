from app import create_app
from extensions import db
from models import User, Role, user_roles
from sqlalchemy import text, inspect

app = create_app()

def migrate():
    with app.app_context():
        # 1. Vérifier si les tables existent
        inspector = inspect(db.engine)
        
        print("--- Début de la migration vers le système Multi-Rôles ---")
        
        # Création des tables si elles n'existent pas
        db.create_all()
        
        # 2. Création des rôles par défaut
        default_roles = [
            ('admin', 'Administrateur complet'),
            ('manager', 'Gestionnaire (Docs/Clients, pas de Paramètres/Users)'),
            ('settings', 'Accès aux Paramètres'),
            ('user_admin', 'Gestion des Utilisateurs'),
            ('reporting', 'Visualisation uniquement (Lecture seule)'),
            ('devis_admin', 'Gestion des Devis'),
            ('facture_admin', 'Gestion des Factures'),
            ('avoir_admin', 'Gestion des Avoirs'),
            ('client_admin', 'Gestion des Clients')
        ]
        
        role_objs = {}
        for r_name, r_desc in default_roles:
            role = Role.query.filter_by(name=r_name).first()
            if not role:
                role = Role(name=r_name, description=r_desc)
                db.session.add(role)
                print(f"Rôle créé : {r_name}")
            role_objs[r_name] = role
        
        db.session.commit()
        
        # 3. Migration des utilisateurs existants
        # On lit directement la colonne 'role' via SQL pour être sûr
        users = User.query.all()
        for user in users:
            # On récupère l'ancien rôle via une requête SQL brute au cas où SQLAlchemy a déjà "oublié" la colonne
            try:
                result = db.session.execute(text(f"SELECT role FROM user WHERE id = {user.id}")).fetchone()
                old_role_name = result[0] if result else None
            except Exception as e:
                print(f"Erreur lors de la lecture de l'ancien rôle pour {user.username}: {e}")
                old_role_name = None
            
            if old_role_name and not user.roles:
                if old_role_name in role_objs:
                    user.roles.append(role_objs[old_role_name])
                    print(f"Utilisateur {user.username} : Ancien rôle '{old_role_name}' migré.")
                else:
                    print(f"Utilisateur {user.username} : Ancien rôle '{old_role_name}' inconnu, rôle par défaut 'manager' attribué.")
                    user.roles.append(role_objs['manager'])
        
        db.session.commit()
        print("Migration des données terminée.")
        
        # 4. Nettoyage (Optionnel : On laisse la colonne pour l'instant pour éviter les crashs si le code n'est pas prêt)
        print("Note : La colonne 'role' dans la table 'user' n'est plus utilisée par le code.")
        print("--- Migration terminée avec succès ---")

if __name__ == '__main__':
    migrate()
