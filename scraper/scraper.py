#!/usr/bin/env python3
import sys
import os
import time
import importlib
import logging
from datetime import datetime, timedelta
import traceback
import random
import json
from statistics import mean, median, stdev
from pathlib import Path

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

# Fichier pour stocker les métriques de scraping
METRICS_FILE = Path(config.LOG_DIR) / 'scraper_metrics.json'

def load_metrics():
    """Charge les métriques de scraping du fichier"""
    if not METRICS_FILE.exists():
        return {}
    
    try:
        with open(METRICS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Impossible de charger les métriques: {str(e)}")
        return {}

def save_metrics(metrics):
    """Sauvegarde les métriques de scraping dans le fichier"""
    try:
        # Ensure the directory exists
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, 'w') as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        logger.warning(f"Impossible de sauvegarder les métriques: {str(e)}")

def update_source_metrics(metrics, source_name, success, response_time=None, items_count=None, error=None):
    """Met à jour les métriques pour une source donnée"""
    if source_name not in metrics:
        metrics[source_name] = {
            'runs': 0,
            'successes': 0,
            'failures': 0,
            'response_times': [],
            'items_counts': [],
            'last_run': None,
            'errors': {},
            'optimal_delay': config.SCRAPER_DELAY,
            'optimal_pages': 3
        }
    
    metrics[source_name]['runs'] += 1
    metrics[source_name]['last_run'] = datetime.utcnow().isoformat()
    
    if success:
        metrics[source_name]['successes'] += 1
        if response_time is not None:
            metrics[source_name]['response_times'].append(response_time)
            # Garder seulement les 50 derniers temps de réponse
            metrics[source_name]['response_times'] = metrics[source_name]['response_times'][-50:]
        
        if items_count is not None:
            metrics[source_name]['items_counts'].append(items_count)
            # Garder seulement les 20 derniers comptes d'items
            metrics[source_name]['items_counts'] = metrics[source_name]['items_counts'][-20:]
    else:
        metrics[source_name]['failures'] += 1
        if error:
            error_type = error.__class__.__name__
            metrics[source_name]['errors'][error_type] = metrics[source_name]['errors'].get(error_type, 0) + 1
    
    # Calculer le délai optimal basé sur les temps de réponse
    if len(metrics[source_name]['response_times']) >= 5:
        avg_response_time = mean(metrics[source_name]['response_times'])
        metrics[source_name]['optimal_delay'] = max(config.SCRAPER_DELAY, min(5.0, avg_response_time * 0.2))
    
    # Déterminer le nombre optimal de pages basé sur le taux de succès
    success_rate = metrics[source_name]['successes'] / max(1, metrics[source_name]['runs'])
    if success_rate > 0.9 and metrics[source_name]['runs'] > 10:
        metrics[source_name]['optimal_pages'] = 5
    elif success_rate > 0.7 and metrics[source_name]['runs'] > 5:
        metrics[source_name]['optimal_pages'] = 3
    else:
        metrics[source_name]['optimal_pages'] = 2
    
    return metrics

def get_source_priority(metrics, source_name):
    """Calcule la priorité d'une source basée sur les métriques"""
    if source_name not in metrics:
        return 5  # Priorité par défaut pour les nouvelles sources
    
    source_metrics = metrics[source_name]
    success_rate = source_metrics['successes'] / max(1, source_metrics['runs'])
    
    # Calcul de la priorité (plus le chiffre est bas, plus la priorité est élevée)
    priority = 10 - (success_rate * 10)
    
    # Bonus si la source a fourni beaucoup d'items
    if source_metrics['items_counts'] and mean(source_metrics['items_counts']) > 50:
        priority -= 2
    
    # Malus si la source a eu beaucoup d'erreurs récemment
    if source_metrics['failures'] > source_metrics['successes']:
        priority += 3
    
    return max(1, min(10, priority))  # Limiter entre 1 et 10

def run_scraper_with_retry(source_config, supplier, metrics, max_retries=None):
    """
    Exécute un scraper avec un mécanisme de reprise en cas d'échec
    
    Args:
        source_config (dict): Configuration de la source
        supplier (Supplier): Fournisseur correspondant
        metrics (dict): Métriques de scraping
        max_retries (int): Nombre maximum de tentatives (None pour utiliser la config globale)
    
    Returns:
        list: Résultats du scraping ou None en cas d'échec
    """
    if max_retries is None:
        max_retries = config.SCRAPER_MAX_RETRIES
    
    source_name = source_config['name']
    
    # Obtenir le délai et le nombre de pages optimaux basés sur les métriques
    optimal_delay = metrics.get(source_name, {}).get('optimal_delay', config.SCRAPER_DELAY)
    optimal_pages = metrics.get(source_name, {}).get('optimal_pages', 3)
    
    retry_count = 0
    backoff_time = optimal_delay
    start_time = time.time()
    
    while retry_count <= max_retries:
        try:
            # Importation dynamique du module du scraper
            scraper_module = importlib.import_module(source_config['module'])
            logger.info(f"Exécution du scraper pour {source_name} (tentative {retry_count + 1}/{max_retries + 1})...")
            
            # Exécution du scraper avec le nombre de pages optimisé
            results = scraper_module.scrape(max_pages=optimal_pages)
            
            # Calcul du temps de réponse
            response_time = time.time() - start_time
            logger.info(f"Temps de réponse pour {source_name}: {response_time:.2f} secondes")
            
            # Mise à jour des métriques
            items_count = len(results) if results else 0
            update_source_metrics(metrics, source_name, True, response_time, items_count)
            save_metrics(metrics)
            
            # Si on arrive ici, c'est que le scraping a réussi
            logger.info(f"Scraping réussi pour {source_name} après {retry_count + 1} tentative(s)")
            return results
        
        except ImportError as e:
            # Erreur critique - pas de reprise possible
            logger.error(f"Impossible d'importer le module {source_config['module']}: {e}")
            update_source_metrics(metrics, source_name, False, error=e)
            save_metrics(metrics)
            return None
        
        except Exception as e:
            retry_count += 1
            logger.warning(f"Erreur lors du scraping de {source_name} (tentative {retry_count}/{max_retries + 1}): {str(e)}")
            
            # Mise à jour des métriques d'échec
            update_source_metrics(metrics, source_name, False, error=e)
            
            if retry_count <= max_retries:
                # Attente avec backoff exponentiel, mais en utilisant le délai optimal comme base
                wait_time = backoff_time * (2 ** (retry_count - 1))
                logger.info(f"Nouvelle tentative dans {wait_time:.2f} secondes...")
                time.sleep(wait_time)
            else:
                logger.error(f"Abandon du scraping pour {source_name} après {max_retries + 1} tentatives")
                logger.error(traceback.format_exc())
                save_metrics(metrics)
                return None

def ensure_suppliers_exist():
    """
    S'assure que tous les fournisseurs configurés existent dans la base de données
    
    Returns:
        dict: Mapping des noms de fournisseurs vers les objets Supplier
    """
    suppliers_map = {}
    
    # Récupérer d'abord tous les fournisseurs existants
    existing_suppliers = {supplier.name: supplier for supplier in Supplier.query.all()}
    
    # Parcourir les sources configurées
    for source_config in config.SOURCES:
        name = source_config['name']
        
        if name in existing_suppliers:
            # Le fournisseur existe déjà
            suppliers_map[name] = existing_suppliers[name]
            logger.debug(f"Fournisseur {name} déjà existant dans la base de données")
        elif source_config.get('enabled', False):
            # Création d'un nouveau fournisseur
            try:
                website = source_config.get('website', '')
                new_supplier = Supplier(
                    name=name,
                    website=website,
                    created_at=datetime.utcnow()
                )
                db_session.add(new_supplier)
                db_session.commit()
                
                suppliers_map[name] = new_supplier
                logger.info(f"Nouveau fournisseur créé: {name} ({website})")
            except Exception as e:
                db_session.rollback()
                logger.error(f"Erreur lors de la création du fournisseur {name}: {str(e)}")
    
    return suppliers_map

def run_scrapers():
    """Exécute tous les scrapers configurés avec optimisation automatique"""
    logger.info("Démarrage du scraping...")
    
    # Initialisation de la base de données si nécessaire
    init_db()
    
    # S'assurer que tous les fournisseurs existent
    suppliers_map = ensure_suppliers_exist()
    
    if not suppliers_map:
        logger.error("Aucun fournisseur disponible pour le scraping")
        return
    
    # Chargement des métriques existantes
    metrics = load_metrics()
    
    # Calcul des priorités pour chaque source
    priorities = {}
    for source_config in config.SOURCES:
        if source_config.get('enabled', False):
            priorities[source_config['name']] = get_source_priority(metrics, source_config['name'])
    
    # Tri des sources par priorité (du plus prioritaire au moins prioritaire)
    sorted_sources = sorted([s for s in config.SOURCES if s.get('enabled', False)], 
                           key=lambda s: priorities.get(s['name'], 5))
    
    # Statistiques globales
    total_success = 0
    total_failed = 0
    total_items = 0
    
    # Exécution de chaque scraper dans l'ordre de priorité
    for source_config in sorted_sources:
        if source_config['name'] not in suppliers_map:
            logger.warning(f"Fournisseur {source_config['name']} non disponible pour le scraping")
            continue
        
        supplier = suppliers_map[source_config['name']]
        
        # Exécution du scraper avec reprise
        results = run_scraper_with_retry(source_config, supplier, metrics)
        
        if results:
            # Traitement des résultats
            success, processed_items = process_results(results, supplier)
            total_items += processed_items
            
            if success:
                total_success += 1
            else:
                total_failed += 1
            
            logger.info(f"Scraping terminé pour {source_config['name']}")
        else:
            total_failed += 1
            logger.error(f"Échec du scraping pour {source_config['name']}")
        
        # Pause entre les scrapers pour éviter de surcharger les sites
        # Utilisation du délai optimal avec un facteur aléatoire pour éviter la détection de bots
        optimal_delay = metrics.get(source_config['name'], {}).get('optimal_delay', config.SCRAPER_DELAY)
        jitter = random.uniform(0.8, 1.2)
        pause_time = optimal_delay * jitter
        logger.info(f"Pause de {pause_time:.2f} secondes avant le prochain scraper...")
        time.sleep(pause_time)
    
    logger.info(f"Scraping terminé pour tous les fournisseurs. Succès: {total_success}, Échecs: {total_failed}, Items récupérés: {total_items}")

def process_results(results, supplier):
    """
    Traite les résultats du scraping et les enregistre dans la base de données
    
    Args:
        results (list): Résultats du scraping
        supplier (Supplier): Fournisseur correspondant
    
    Returns:
        tuple: (success, processed_items) - True si le traitement a réussi, False sinon, et nombre d'items traités
    """
    if not results:
        logger.warning(f"Aucun résultat de scraping pour {supplier.name}")
        return False, 0
    
    count_new = 0
    count_updated = 0
    count_errors = 0
    
    # On traite tout en une seule transaction pour assurer la cohérence
    try:
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
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db_session.add(part)
                    # On fait un flush pour obtenir l'ID de la pièce, mais pas de commit
                    db_session.flush()  
                    count_new += 1
                else:
                    # Mise à jour des informations de la pièce
                    part.name = item.get('name', part.name)
                    part.description = item.get('description', part.description)
                    part.category = item.get('category', part.category)
                    part.image_url = item.get('image_url', part.image_url)
                    part.updated_at = datetime.utcnow()
                    count_updated += 1
                
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
                
            except Exception as e:
                count_errors += 1
                logger.error(f"Erreur lors du traitement de l'élément {item.get('reference')}: {str(e)}")
                continue
        
        # On commit une seule fois à la fin
        try:
            db_session.commit()
            logger.info(f"Données sauvegardées avec succès. {count_new} nouvelles pièces, {count_updated} mises à jour.")
        except Exception as e:
            db_session.rollback()
            logger.error(f"Erreur lors de l'enregistrement des données: {str(e)}")
            count_errors += count_new + count_updated
            count_new = 0
            count_updated = 0
            
    except Exception as e:
        db_session.rollback()
        logger.error(f"Erreur globale lors du traitement des résultats: {str(e)}")
        logger.error(traceback.format_exc())
        return False, 0
    
    total_processed = count_new + count_updated
    logger.info(f"Résultats traités pour {supplier.name}: {count_new} nouvelles pièces, {count_updated} mises à jour, {count_errors} erreurs")
    return count_errors < len(results) // 2, total_processed  # Succès si moins de la moitié des éléments sont en erreur

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
