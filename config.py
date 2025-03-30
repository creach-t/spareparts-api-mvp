import os
from dotenv import load_dotenv
import sys

# Chargement des variables d'environnement
load_dotenv()

# Configuration de base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URI = os.environ.get('DATABASE_URI', f'sqlite:///{os.path.join(BASE_DIR, "spareparts.db")}')

# Configuration de l'API
API_HOST = os.environ.get('API_HOST', '0.0.0.0')
API_PORT = int(os.environ.get('API_PORT', 5000))
API_DEBUG = os.environ.get('API_DEBUG', 'False').lower() == 'true'
API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '100 per day')
API_SECRET_KEY = os.environ.get('API_SECRET_KEY', 'dev-secret-key-change-in-production')

# Secret pour la génération de clés API (précédemment en dur dans routes.py)
API_KEY_GENERATION_SECRET = os.environ.get('API_KEY_GENERATION_SECRET', 'dev-secret-key-change-me')

# Vérification de sécurité en production
if not API_DEBUG and (API_SECRET_KEY == 'dev-secret-key-change-in-production' or 
                     API_KEY_GENERATION_SECRET == 'dev-secret-key-change-me'):
    print("AVERTISSEMENT DE SÉCURITÉ: Vous utilisez des clés par défaut en production !")
    print("Veuillez définir API_SECRET_KEY et API_KEY_GENERATION_SECRET dans votre fichier .env")
    # Exit si on n'est pas en mode debug et que les clés sont les valeurs par défaut
    if os.environ.get('ALLOW_DEFAULT_KEYS', 'False').lower() != 'true':
        sys.exit(1)

# Configuration du scraper
SCRAPER_USER_AGENT = os.environ.get('SCRAPER_USER_AGENT', 
                                    'SpareParts-Scraper/1.0 (+https://github.com/creach-t/spareparts-api-mvp)')
SCRAPER_DELAY = float(os.environ.get('SCRAPER_DELAY', 1.0))  # Délai entre les requêtes en secondes
SCRAPER_TIMEOUT = int(os.environ.get('SCRAPER_TIMEOUT', 10))  # Timeout des requêtes en secondes
SCRAPER_MAX_RETRIES = int(os.environ.get('SCRAPER_MAX_RETRIES', 3))  # Nombre maximum de tentatives en cas d'échec

# Répertoire pour les logs
LOG_DIR = os.environ.get('LOG_DIR', os.path.join(BASE_DIR, 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)  # Création du répertoire s'il n'existe pas

# Sources de données (sites à scraper)
SOURCES = [
    {
        'name': 'PiecesDetachees24',
        'website': 'https://www.piecesdetachees24.com/',
        'enabled': True,
        'module': 'scraper.sources.piecesdetachees24'
    },
    {
        'name': 'SosAccessoire',
        'website': 'https://www.sosaccessoire.com/',
        'enabled': True,
        'module': 'scraper.sources.sosaccessoire'
    }
]

# Configuration de la base de données
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
