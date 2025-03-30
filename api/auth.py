from flask_httpauth import HTTPTokenAuth
from database.models import ApiKey
from flask import g
import os
import hashlib
import logging
from datetime import datetime

# Configuration du logging
logger = logging.getLogger('spareparts-api.auth')

# Initialisation de l'authentification par token
auth = HTTPTokenAuth(scheme='ApiKey')

@auth.verify_token
def verify_token(token):
    """
    Vérifie si le token API fourni est valide
    
    Args:
        token (str): Token API à vérifier
    
    Returns:
        bool: True si le token est valide, False sinon
    """
    if not token:
        logger.warning("Tentative d'accès sans token API")
        return False
    
    # Recherche de la clé API dans la base de données
    api_key = ApiKey.query.filter_by(key=token, active=True).first()
    
    if not api_key:
        logger.warning(f"Tentative d'accès avec un token API invalide: {token}")
        return False
    
    # Mise à jour de la date de dernière utilisation
    api_key.last_used = datetime.utcnow()
    
    # Stockage de l'utilisateur dans le contexte global Flask
    g.api_user = api_key.name
    
    logger.info(f"Accès API authentifié pour: {api_key.name}")
    return True


def generate_api_key(length=32):
    """
    Génère une nouvelle clé API aléatoire
    
    Args:
        length (int): Longueur de la clé en octets (la clé hexadécimale résultante aura une longueur double)
    
    Returns:
        str: Clé API générée
    """
    # Génération d'octets aléatoires
    random_bytes = os.urandom(length)
    
    # Conversion en chaîne hexadécimale
    api_key = hashlib.sha256(random_bytes).hexdigest()[:length*2]
    
    return api_key
