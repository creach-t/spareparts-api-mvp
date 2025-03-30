#!/usr/bin/env python3
import sys
import os
import argparse
from datetime import datetime

# Ajout du répertoire parent au sys.path pour pouvoir importer config et database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import db_session, init_db
from database.models import ApiKey
from api.auth import generate_api_key

def create_test_api_key(name="Test User", email="test@example.com"):
    """
    Crée une clé API de test dans la base de données
    
    Args:
        name (str): Nom associé à la clé API
        email (str): Email associé à la clé API
    
    Returns:
        str: Clé API générée
    """
    # Initialisation de la base de données si nécessaire
    init_db()
    
    # Vérification si une clé existe déjà pour cet email
    existing_key = ApiKey.query.filter_by(email=email).first()
    
    if existing_key:
        print(f"Une clé API existe déjà pour {email}: {existing_key.key}")
        return existing_key.key
    
    # Génération de la clé API
    api_key = generate_api_key()
    
    # Enregistrement de la clé dans la base de données
    new_key = ApiKey(
        key=api_key,
        name=name,
        email=email,
        active=True,
        created_at=datetime.utcnow()
    )
    
    db_session.add(new_key)
    db_session.commit()
    
    print(f"Nouvelle clé API créée: {api_key}")
    print(f"Nom: {name}")
    print(f"Email: {email}")
    
    return api_key

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crée une clé API de test")
    parser.add_argument("--name", default="Test User", help="Nom associé à la clé API")
    parser.add_argument("--email", default="test@example.com", help="Email associé à la clé API")
    
    args = parser.parse_args()
    
    try:
        create_test_api_key(args.name, args.email)
    except Exception as e:
        print(f"Erreur lors de la création de la clé API: {str(e)}")
        sys.exit(1)
    finally:
        db_session.remove()
