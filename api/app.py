#!/usr/bin/env python3
from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import sys
import logging
import atexit

# Ajout du répertoire parent au sys.path pour pouvoir importer config et database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from database.db import db_session, init_db
from api.routes import api_bp

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api.log')
    ]
)
logger = logging.getLogger('spareparts-api')

# Initialisation de l'application Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = config.API_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_ECHO'] = config.SQLALCHEMY_ECHO

# Initialisation du limiteur de requêtes
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=[config.API_RATE_LIMIT],
    storage_uri="memory://"
)

# Enregistrement du blueprint API
app.register_blueprint(api_bp, url_prefix='/api')

# Fonction pour fermer la session de base de données à la fin de l'exécution
@atexit.register
def close_db_connection():
    db_session.remove()

# Route d'accueil pour l'application
@app.route('/')
def index():
    return jsonify({
        'name': 'SpareParts API',
        'description': 'API pour la disponibilité des pièces détachées d\'électroménager',
        'version': '1.0.0',
        'status': 'OK',
        'api_url': '/api'
    })

# Gestionnaire d'erreur 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

# Gestionnaire d'erreur 500
@app.errorhandler(500)
def server_error(error):
    logger.error(f"Erreur serveur: {str(error)}")
    return jsonify({'error': 'Erreur interne du serveur'}), 500

# Initialisation de la base de données
def init_database():
    logger.info("Initialisation de la base de données...")
    try:
        init_db()
        logger.info("Base de données initialisée avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données: {str(e)}")
        sys.exit(1)

# Fonction principale
def main():
    init_database()
    logger.info(f"Démarrage de l'API sur {config.API_HOST}:{config.API_PORT}")
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.API_DEBUG
    )

if __name__ == "__main__":
    main()
