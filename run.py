#!/usr/bin/env python3
import argparse
import sys
import logging
import subprocess
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('spareparts-runner')

def run_init_db():
    """Initialise la base de données"""
    logger.info("Initialisation de la base de données...")
    from database.db import init_db
    init_db()
    logger.info("Base de données initialisée")

def run_create_test_key():
    """Crée une clé API de test"""
    logger.info("Création d'une clé API de test...")
    from scripts.create_test_api_key import create_test_api_key
    api_key = create_test_api_key()
    logger.info(f"Clé API de test créée: {api_key}")
    return api_key

def run_scraper():
    """Exécute le scraper"""
    logger.info("Démarrage du scraper...")
    from scraper.scraper import run_scrapers
    run_scrapers()
    logger.info("Scraping terminé")

def run_api():
    """Exécute l'API"""
    logger.info("Démarrage de l'API...")
    from api.app import main
    main()

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="SpareParts API Runner")
    parser.add_argument('command', choices=['init', 'scrape', 'api', 'all'], 
                        help='Commande à exécuter (init, scrape, api, all)')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'init':
            run_init_db()
            api_key = run_create_test_key()
            print(f"\nInitialisation terminée. Utilisez cette clé API pour les requêtes: {api_key}\n")
            
        elif args.command == 'scrape':
            run_scraper()
            
        elif args.command == 'api':
            run_api()
            
        elif args.command == 'all':
            # Pour 'all', on initialise, on lance le scraper, puis l'API
            run_init_db()
            api_key = run_create_test_key()
            print(f"\nClé API générée: {api_key}\n")
            run_scraper()
            run_api()
            
    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Assurez-vous que le répertoire courant est le répertoire racine du projet
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
