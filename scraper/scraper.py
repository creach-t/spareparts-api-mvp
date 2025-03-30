#!/usr/bin/env python3
import sys
import os
import time
import importlib
import logging
from datetime import datetime
import traceback
import random

# Ajout du répertoire parent au sys.path pour pouvoir importer config et database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from database.db import db_session, init_db
from database.models import Part, Supplier, Availability

# Configuration du logging
if not os.path.exists(config.LOG_DIR):
    os.makedirs(config.LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(config.LOG_DIR, 'scraper.log'))
    ]
)
logger = logging.getLogger('spareparts-scraper')

def run_scraper_with_retry(source_config, supplier, max_retries=None):
    """
    Exécute un scraper avec un mécanisme de reprise en cas d'échec
    
    Args:
        source_config (dict): Configuration de la source
        supplier (Supplier): Fournisseur correspondant
        max_retries (int): Nombre maximum de tentatives (None pour utiliser la config globale)
    
    Returns:
        list: Résultats du scraping ou None en cas d'échec
    """
    if max_retries is None:
        max_retries = config.SCRAPER_MAX_RETRIES
    
    retry_count = 0
    backoff_time = config.SCRAPER_DELAY
    
    while retry_count <= max_retries:
        try:
            # Importation dynamique du module du scraper
            scraper_module = importlib.import_module(source_config['module'])
            logger.info(f"Exécution du scraper pour {source_config['name']} (tentative {retry_count + 1}/{max_retries + 1})...")
            
            # Exécution du scraper
            results = scraper_module.scrape()
            
            # Si on arrive ici, c'est que le scraping a réussi
            logger.info(f"Scraping réussi pour {source_config['name']} après {retry_count + 1} tentative(s)")
            return results
        
        except ImportError as e:
            # Erreur critique - pas de reprise possible
            logger.error(f"Impossible d'importer le module {source_config['module']}: {e}")
            return None
        
        except Exception as e:
            retry_count += 1
            logger.warning(f"Erreur lors du scraping de {source_config['name']} (tentative {retry_count}/{max_retries + 1}): {str(e)}")
            
            if retry_count <= max_retries:
                # Attente avec backoff exponentiel
                wait_time = backoff_time * (2 ** (retry_count - 1))
                logger.info(f"Nouvelle tentative dans {wait_time:.2f} secondes...")
                time.sleep(wait_time)
            else:
                logger.error(f"Abandon du scraping pour {source_config['name']} après {max_retries + 1} tentatives")
                logger.error(traceback.format_exc())
                return None

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
    
    # Mélange aléatoire des sources pour éviter de toujours commencer par le même
    sources = config.SOURCES.copy()
    random.shuffle(sources)
    
    # Statistiques globales
    total_success = 0
    total_failed = 0
    
    # Exécution de chaque scraper activé
    for source_config in sources:
        if not source_config.get('enabled', False):
            logger.info(f"Scraper {source_config['name']} désactivé - ignoré")
            continue
        
        if source_config['name'] not in suppliers_map:
            logger.warning(f"Fournisseur {source_config['name']} non trouvé dans la base de données")
            continue
        
        supplier = suppliers_map[source_config['name']]
        
        # Exécution du scraper avec reprise
        results = run_scraper_with_retry(source_config, supplier)
        
        if results:
            # Traitement des résultats
            success = process_results(results, supplier)
            if success:
                total_success += 1
            else:
                total_failed += 1
            
            logger.info(f"Scraping terminé pour {source_config['name']}")
        else:
            total_failed += 1
            logger.error(f"Échec du scraping pour {source_config['name']}")
        
        # Pause entre les scrapers pour éviter de surcharger les sites
        # Ajout d'un délai aléatoire pour éviter la détection de bots
        jitter = random.uniform(0.5, 1.5)
        time.sleep(config.SCRAPER_DELAY * jitter)
    
    logger.info(f"Scraping terminé pour tous les fournisseurs. Succès: {total_success}, Échecs: {total_failed}")

def process_results(results, supplier):
    """
    Traite les résultats du scraping et les enregistre dans la base de données
    
    Args:
        results (list): Résultats du scraping
        supplier (Supplier): Fournisseur correspondant
    
    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    if not results:
        logger.warning(f"Aucun résultat de scraping pour {supplier.name}")
        return False
    
    count_new = 0
    count_updated = 0
    count_errors = 0
    batch_size = 100  # Traitement par lots pour éviter de surcharger la mémoire
    current_batch = []
    
    for item in results:
        try:
            # Vérification des données minimales requises
            if not item.get('reference') or not item.get('name'):
                logger.warning(f"Élément ignoré: données manquantes - {item}")
                continue
                
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
            
            # Ajout à la liste de traitement par lots
            current_batch.append(part)
            
            # Si le lot est plein, on commit
            if len(current_batch) >= batch_size:
                try:
                    db_session.commit()
                    logger.debug(f"Lot de {len(current_batch)} éléments traité")
                    current_batch = []
                except Exception as e:
                    db_session.rollback()
                    logger.error(f"Erreur lors de l'enregistrement d'un lot: {str(e)}")
                    count_errors += len(current_batch)
                    current_batch = []
            
        except Exception as e:
            count_errors += 1
            logger.error(f"Erreur lors du traitement de l'élément {item.get('reference')}: {str(e)}")
            continue
    
    # Commit des éléments restants
    if current_batch:
        try:
            db_session.commit()
            logger.debug(f"Lot final de {len(current_batch)} éléments traité")
        except Exception as e:
            db_session.rollback()
            logger.error(f"Erreur lors de l'enregistrement du lot final: {str(e)}")
            count_errors += len(current_batch)
    
    logger.info(f"Résultats traités pour {supplier.name}: {count_new} nouvelles pièces, {count_updated} mises à jour, {count_errors} erreurs")
    return count_errors < len(results) // 2  # Succès si moins de la moitié des éléments sont en erreur

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
