from app import create_app
from models import CompanyInfo
import os

app = create_app()

with app.app_context():
    info = CompanyInfo.query.first()
    if info:
        print(f"ID: {info.id}")
        print(f"Nom: {info.nom}")
        print(f"Logo Path in DB: '{info.logo_path}'")
        
        if info.logo_path:
            # We used hardcoded d: prefix in template, let's check both relative and absolute assumptions
            computed_static_path = os.path.join(app.root_path, 'static', info.logo_path)
            print(f"Computed Static Path: '{computed_static_path}'")
            print(f"File Exists: {os.path.exists(computed_static_path)}")
            
            # Also check if it works with the hardcoded string used in template
            hardcoded_template_path = f"d:/websites/stp/static/{info.logo_path}"
            print(f"Hardcoded Template Path: '{hardcoded_template_path}'")
            print(f"File Exists: {os.path.exists(hardcoded_template_path)}")
        else:
            print("No logo path set.")
    else:
        print("No CompanyInfo found.")
