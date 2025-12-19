import sys
import os

# IMPORTANT: Update this path with your PythonAnywhere username
# Example: /home/yourusername/STPAPP
project_home = '/home/STPAPP/STPAPP'

# Importer l'application Flask
from app import create_app
application = create_app()