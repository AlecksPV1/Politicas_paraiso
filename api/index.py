import sys
import os

# Asegurar que el directorio raíz del proyecto esté en el sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
