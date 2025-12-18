import sys
import os
# Ajouter le répertoire de l'app au path
project_home = '/home/VOTRE_USERNAME/stp'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
# Importer l'application Flask
from app import create_app
application = create_app()