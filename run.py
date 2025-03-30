#!/usr/bin/env python3
import argparse
import sys
import logging
import subprocess
import os
import webbrowser
from pathlib import Path

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

def run_debug_scraper():
    """Exécute le scraper en mode debug"""
    logger.info("Démarrage du scraper en mode debug...")
    from scripts.debug_scraper import debug_scraper
    debug_scraper()
    logger.info("Scraping debug terminé")

def run_api():
    """Exécute l'API"""
    logger.info("Démarrage de l'API...")
    from api.app import main
    main()

def run_insert_test_data():
    """Insère des données de test dans la base de données"""
    logger.info("Insertion de données de test...")
    from scripts.insert_test_data import insert_test_data
    insert_test_data()
    logger.info("Données de test insérées")

def run_generate_report():
    """Génère un rapport de métriques du scraper"""
    logger.info("Génération du rapport de métriques...")
    import config
    from scripts.generate_metrics_report import main as generate_report_main
    
    report_file = Path(config.LOG_DIR) / 'reports' / 'scraper_report.html'
    report_exit_code = generate_report_main()
    
    if report_exit_code == 0 and report_file.exists():
        logger.info(f"Rapport généré avec succès: {report_file}")
        # Ouvrir le rapport dans le navigateur par défaut
        webbrowser.open(f'file://{report_file.absolute()}')
    else:
        logger.error("Échec de la génération du rapport")
        return 1
    
    return 0

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="SpareParts API Runner")
    parser.add_argument('command', choices=['init', 'scrape', 'api', 'report', 'test', 'all', 'testdata', 'debug'], 
                        help='Commande à exécuter (init, scrape, api, report, test, all, testdata, debug)')
    parser.add_argument('--max-pages', type=int, default=None,
                        help='Nombre maximum de pages à scraper par source (pour la commande scrape)')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'init':
            run_init_db()
            api_key = run_create_test_key()
            print(f"\nInitialisation terminée. Utilisez cette clé API pour les requêtes: {api_key}\n")
            
        elif args.command == 'scrape':
            # Si max_pages est spécifié, on le configure temporairement
            if args.max_pages is not None:
                logger.info(f"Configuration du nombre de pages maximum à {args.max_pages}")
                import config
                for source in config.SOURCES:
                    if source.get('enabled', False):
                        logger.info(f"Limiting {source['name']} to {args.max_pages} pages")
            
            run_scraper()
            
        elif args.command == 'debug':
            run_debug_scraper()
            
        elif args.command == 'api':
            run_api()
            
        elif args.command == 'report':
            run_generate_report()
            
        elif args.command == 'testdata':
            run_init_db()
            api_key = run_create_test_key()
            run_insert_test_data()
            print(f"\nDonnées de test insérées. Utilisez cette clé API pour les requêtes: {api_key}\n")
            
        elif args.command == 'test':
            # Commande de test : init + scrape limité + rapport
            run_init_db()
            api_key = run_create_test_key()
            print(f"\nClé API générée: {api_key}\n")
            
            # Configuration temporaire pour un test rapide
            import config
            for source in config.SOURCES:
                if source.get('enabled', False):
                    logger.info(f"Limiting {source['name']} to 1 page for test")
            
            # Exécuter le scraper avec des limites
            logger.info("Exécution du scraper en mode test (1 page max)...")
            from scraper.scraper import run_scrapers
            run_scrapers()
            
            # Générer le rapport
            run_generate_report()
            
            # Démarrer l'API
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
