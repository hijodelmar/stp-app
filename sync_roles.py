from app import create_app
from extensions import db
from models import Role

app = create_app()

def sync_roles():
    """
    Master Role Sync Script
    - Adds missing roles
    - Updates descriptions for existing roles
    - Removes undefined roles
    """
    
    # Source of Truth (Local)
    roles_data = {
        'admin': 'Administrateur complet',
        'manager': 'Gestionnaire (Docs/Clients, pas de Paramètres/Users)',
        'settings': 'Accès aux Paramètres uniquement',
        'user_admin': 'Gestion des Utilisateurs',
        'reporting': 'Accès aux rapports et dashboard',
        'devis_admin': 'Gestion complète des Devis',
        'facture_admin': 'Gestion complète des Factures',
        'avoir_admin': 'Gestion complète des Avoirs',
        'client_admin': 'Gestion complète des Clients',
        'supplier_admin': 'Gestion complète des Fournisseurs',
        'access_expenses': 'Grants access to the detailed Expenses module'
    }

    print("🔄 Syncing Roles & Descriptions...")
    
    with app.app_context():
        current_db_roles = Role.query.all()
        current_roles_map = {r.name: r for r in current_db_roles}
        
        roles_added = 0
        roles_updated = 0
        roles_deleted = 0
        
        # 1. Add or Update
        for name, desc in roles_data.items():
            if name in current_roles_map:
                role = current_roles_map[name]
                if role.description != desc:
                    print(f"📝 Updating desc for '{name}'")
                    role.description = desc
                    roles_updated += 1
            else:
                print(f"➕ Adding role '{name}'")
                new_role = Role(name=name, description=desc)
                db.session.add(new_role)
                roles_added += 1

        # 2. Delete Extras
        for role in current_db_roles:
            if role.name not in roles_data:
                print(f"🗑️ Deleting extra role '{role.name}'")
                db.session.delete(role)
                roles_deleted += 1
        
        if roles_added or roles_updated or roles_deleted:
            try:
                db.session.commit()
                print(f"✅ Sync Complete: +{roles_added} Added, ~{roles_updated} Updated, -{roles_deleted} Deleted.")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error: {e}")
        else:
            print("✅ Roles are already perfectly aligned.")

if __name__ == "__main__":
    sync_roles()
