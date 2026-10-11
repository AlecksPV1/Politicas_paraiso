import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY', 'clave-secreta-politicas-2026-super-segura')
MASTER_PASSWORD = os.environ.get('MASTER_PASSWORD', 'admin2026')

# En plataformas serverless como Vercel o AWS Lambda, solo /tmp es escribible
IS_SERVERLESS = os.environ.get('VERCEL') == '1' or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
if IS_SERVERLESS:
    STORAGE_BASE = os.path.join('/tmp', 'storage')
else:
    STORAGE_BASE = os.environ.get('STORAGE_DIR', os.path.join(BASE_DIR, 'storage'))

DB_PATH = os.path.join(STORAGE_BASE, 'politicas.db')
PDF_STORAGE_DIR = os.path.join(STORAGE_BASE, 'pdfs')
SIGNATURE_STORAGE_DIR = os.path.join(STORAGE_BASE, 'signatures')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'plantilla_politica.txt')
LOGO_PATH = os.path.join(BASE_DIR, 'logo.png')

os.makedirs(PDF_STORAGE_DIR, exist_ok=True)
os.makedirs(SIGNATURE_STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
