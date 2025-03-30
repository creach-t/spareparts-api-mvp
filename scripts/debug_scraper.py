#!/usr/bin/env python3
import os
import sys
import logging
import json
import importlib

# Ajout du répertoire parent au sys.path pour pouvoir importer config et database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database.db import db_session, init_db
from database.models import Part, Supplier, Availability

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,  # Niveau détaillé
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('spareparts-debug')

def debug_scraper():
    """Fonction de débogage pour tester directement le scraper"""
    logger.info("Démarrage du débogage du scraper...")
    
    # Initialisation de la base de données si nécessaire
    logger.info("Initialisation de la base de données...")
    init_db()
    
    # Vérifier si le fournisseur existe
    supplier = Supplier.query.filter_by(name='1001pieces').first()
    if not supplier:
        logger.info("Création du fournisseur 1001pieces...")
        supplier = Supplier(
            name='1001pieces',
            website='https://www.1001pieces.com/'
        )
        db_session.add(supplier)
        db_session.commit()
    
    # Importation dynamique du module (car le nom commence par un chiffre)
    logger.info("Importation du module scraper.sources.1001pieces...")
    scraper_module = importlib.import_module("scraper.sources.1001pieces")
    
    # Scraper seulement une catégorie pour tester
    logger.info("Lancement du scraper 1001pieces (seulement pour 'refrigerateur')...")
    results = scraper_module.scrape(search_terms=['refrigerateur'], max_pages=1)
    
    logger.info(f"Scraping terminé, {len(results)} produits extraits")
    
    # Afficher quelques exemples des données scrapées
    if len(results) > 0:
        logger.info("Exemples des données scrapées:")
        for i, item in enumerate(results[:3]):  # Afficher les 3 premiers éléments
            logger.info(f"Item {i+1}:")
            for key, value in item.items():
                logger.info(f"  {key}: {value}")
    
    # Processus d'enregistrement manuel
    logger.info("Enregistrement manuel des données dans la base...")
    count_new = 0
    count_updated = 0
    
    try:
        for item in results:
            # Vérification des données minimales requises
            if not item.get('reference') or not item.get('name'):
                logger.warning(f"Élément ignoré: données manquantes - {item}")
                continue
                
            # Recherche si la pièce existe déjà
            part = Part.query.filter_by(reference=item['reference']).first()
            
            # Si la pièce n'existe pas, on la crée
            if not part:
                logger.debug(f"Création d'une nouvelle pièce: {item['reference']}")
                part = Part(
                    reference=item['reference'],
                    name=item['name'],
                    description=item.get('description'),
                    category=item.get('category'),
                    image_url=item.get('image_url')
                )
                db_session.add(part)
                count_new += 1
            else:
                logger.debug(f"Mise à jour d'une pièce existante: {item['reference']}")
                part.name = item.get('name', part.name)
                part.description = item.get('description', part.description)
                part.category = item.get('category', part.category)
                part.image_url = item.get('image_url', part.image_url)
                count_updated += 1
            
            # Commit intermédiaire pour s'assurer que la pièce est bien créée
            db_session.flush()
            
            # Mise à jour de la disponibilité
            logger.debug(f"Vérification de la disponibilité pour part_id={part.id}, supplier_id={supplier.id}")
            availability = Availability.query.filter_by(
                part_id=part.id,
                supplier_id=supplier.id
            ).first()
            
            if not availability:
                logger.debug("Création d'une nouvelle disponibilité")
                availability = Availability(
                    part_id=part.id,
                    supplier_id=supplier.id,
                    price=item.get('price'),
                    in_stock=item.get('in_stock', False),
                    url=item.get('url')
                )
                db_session.add(availability)
            else:
                logger.debug("Mise à jour d'une disponibilité existante")
                availability.price = item.get('price', availability.price)
                availability.in_stock = item.get('in_stock', availability.in_stock)
                availability.url = item.get('url', availability.url)
        
        # Commit final
        logger.info("Exécution du commit final...")
        db_session.commit()
        logger.info(f"Données sauvegardées avec succès. {count_new} nouvelles pièces, {count_updated} mises à jour.")
        
        # Vérifier les données enregistrées
        parts_count = Part.query.count()
        avail_count = Availability.query.count()
        logger.info(f"Nombre total de pièces en base: {parts_count}")
        logger.info(f"Nombre total de disponibilités en base: {avail_count}")
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Erreur lors de l'enregistrement des données: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        debug_scraper()
    except Exception as e:
        logger.error(f"Erreur non gérée: {str(e)}", exc_info=True)
    finally:
        db_session.remove()
