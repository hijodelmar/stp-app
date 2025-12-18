import sys
import os

# IMPORTANT: Update this path with your PythonAnywhere username
# Example: /home/yourusername/STPAPP
project_home = '/home/YOUR_USERNAME_HERE/STPAPP'

# Importer l'application Flask
from app import create_app
application = create_app()