from app import create_app
from extensions import db
from models import Role

app = create_app()

def sync_roles():
    """
    Ensures all necessary roles exist in the database.
    Add new roles to the list below.
    """
    required_roles = [
        'admin', 
        'manager', 
        'reporting', 
        'settings', 
        'user_admin',
        'access_expenses',
        'access_clients',
        'access_documents'
    ]

    print("🔄 Checking Roles...")
    
    with app.app_context():
        existing_roles = {r.name for r in Role.query.all()}
        
        roles_added = 0
        for role_name in required_roles:
            if role_name not in existing_roles:
                print(f"➕ Adding missing role: {role_name}")
                new_role = Role(name=role_name)
                db.session.add(new_role)
                roles_added += 1
            else:
                print(f"✓ Role exists: {role_name}")
        
        if roles_added > 0:
            try:
                db.session.commit()
                print(f"✅ Successfully added {roles_added} new roles.")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error saving roles: {e}")
        else:
            print("✅ All roles are already up to date.")

if __name__ == "__main__":
    sync_roles()
