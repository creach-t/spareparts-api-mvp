#!/usr/bin/env python3
import sys
import os
import time
import importlib
import logging
from datetime import datetime
import traceback

# Ajout du répertoire parent au sys.path pour pouvoir importer config et database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from database.db import db_session, init_db
from database.models import Part, Supplier, Availability

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log')
    ]
)
logger = logging.getLogger('spareparts-scraper')

def run_scrapers():
    """Exécute tous les scrapers configurés"""
    logger.info("Démarrage du scraping...")
    
    # Initialisation de la base de données si nécessaire
    init_db()
    
    # Récupération des fournisseurs depuis la base de données
    suppliers = Supplier.query.all()
    if not suppliers:
        logger.error("Aucun fournisseur trouvé dans la base de données")
        return
    
    # Mapping des fournisseurs par nom pour un accès facile
    suppliers_map = {supplier.name: supplier for supplier in suppliers}
    
    # Exécution de chaque scraper activé
    for source_config in config.SOURCES:
        if not source_config.get('enabled', False):
            logger.info(f"Scraper {source_config['name']} désactivé - ignoré")
            continue
        
        if source_config['name'] not in suppliers_map:
            logger.warning(f"Fournisseur {source_config['name']} non trouvé dans la base de données")
            continue
        
        supplier = suppliers_map[source_config['name']]
        
        try:
            # Importation dynamique du module du scraper
            scraper_module = importlib.import_module(source_config['module'])
            logger.info(f"Exécution du scraper pour {source_config['name']}...")
            
            # Exécution du scraper
            results = scraper_module.scrape()
            
            # Traitement des résultats
            process_results(results, supplier)
            
            logger.info(f"Scraping terminé pour {source_config['name']}")
            
            # Pause entre les scrapers pour éviter de surcharger les sites
            time.sleep(config.SCRAPER_DELAY)
            
        except ImportError as e:
            logger.error(f"Impossible d'importer le module {source_config['module']}: {e}")
        except Exception as e:
            logger.error(f"Erreur lors du scraping de {source_config['name']}: {str(e)}")
            logger.error(traceback.format_exc())
    
    logger.info("Scraping terminé pour tous les fournisseurs")


def process_results(results, supplier):
    """Traite les résultats du scraping et les enregistre dans la base de données"""
    if not results:
        logger.warning(f"Aucun résultat de scraping pour {supplier.name}")
        return
    
    count_new = 0
    count_updated = 0
    
    for item in results:
        try:
            # Recherche si la pièce existe déjà
            part = Part.query.filter_by(reference=item['reference']).first()
            
            # Si la pièce n'existe pas, on la crée
            if not part:
                part = Part(
                    reference=item['reference'],
                    name=item['name'],
                    description=item.get('description'),
                    category=item.get('category'),
                    image_url=item.get('image_url'),
                    created_at=datetime.utcnow()
                )
                db_session.add(part)
                db_session.flush()  # Pour obtenir l'ID de la pièce
                count_new += 1
            
            # Mise à jour de la disponibilité
            availability = Availability.query.filter_by(
                part_id=part.id,
                supplier_id=supplier.id
            ).first()
            
            if not availability:
                availability = Availability(
                    part_id=part.id,
                    supplier_id=supplier.id,
                    price=item.get('price'),
                    in_stock=item.get('in_stock', False),
                    url=item.get('url'),
                    last_checked=datetime.utcnow()
                )
                db_session.add(availability)
            else:
                availability.price = item.get('price', availability.price)
                availability.in_stock = item.get('in_stock', availability.in_stock)
                availability.url = item.get('url', availability.url)
                availability.last_checked = datetime.utcnow()
                count_updated += 1
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'élément {item.get('reference')}: {str(e)}")
            continue
    
    # Commit des changements à la base de données
    try:
        db_session.commit()
        logger.info(f"Résultats traités: {count_new} nouvelles pièces, {count_updated} mises à jour pour {supplier.name}")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Erreur lors de l'enregistrement des résultats dans la base de données: {str(e)}")


if __name__ == "__main__":
    try:
        run_scrapers()
    except KeyboardInterrupt:
        logger.info("Interruption du scraping par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur non gérée: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        db_session.remove()
