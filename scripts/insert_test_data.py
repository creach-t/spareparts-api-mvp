#!/usr/bin/env python3
import os
import sys

# Ajout du répertoire parent au sys.path pour pouvoir importer config et database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import db_session, init_db
from database.models import Part, Supplier, Availability
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('spareparts-test-data')

def insert_test_data():
    """Insère des données de test dans la base de données"""
    logger.info("Initialisation de la base de données...")
    init_db()
    
    # Vérifier si le fournisseur existe
    supplier = Supplier.query.filter_by(name='1001pieces').first()
    if not supplier:
        supplier = Supplier(
            name='1001pieces',
            website='https://www.1001pieces.com/',
            created_at=datetime.utcnow()
        )
        db_session.add(supplier)
        db_session.commit()
        logger.info("Fournisseur 1001pieces créé")
    else:
        logger.info("Fournisseur 1001pieces déjà existant")

    # Vérifier si des pièces existent déjà
    parts_count = Part.query.count()
    if parts_count > 0:
        logger.info(f"{parts_count} pièces existantes. Suppression des données de test...")
        
    # Ajouter des pièces de test
    categories = ['refrigerateur', 'lave-linge', 'lave-vaisselle', 'four', 'micro-onde']
    for i in range(1, 101):  # Ajoutons 100 pièces
        category = categories[i % len(categories)]
        part = Part(
            reference=f'TEST-{category.upper()}-{i:04d}',
            name=f'Pièce de test {i} pour {category}',
            description=f'Description de la pièce de test {i} pour {category}',
            category=category,
            image_url=f'https://example.com/images/{category}{i}.jpg',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(part)
        
        # Ajouter une disponibilité pour cette pièce
        availability = Availability(
            part_id=None,  # Sera défini après le flush
            supplier_id=supplier.id,
            price=10.0 + (i / 10),
            in_stock=i % 3 != 0,  # 2/3 des pièces sont en stock
            url=f'https://www.1001pieces.com/product{i}',
            last_checked=datetime.utcnow()
        )
        
        # Flush pour obtenir l'ID de la pièce
        db_session.flush()
        availability.part_id = part.id
        db_session.add(availability)
    
    # Valider les changements
    try:
        db_session.commit()
        logger.info("100 pièces de test ajoutées avec succès")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Erreur lors de l'ajout des pièces de test: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        insert_test_data()
    except Exception as e:
        logger.error(f"Erreur non gérée: {str(e)}")
    finally:
        db_session.remove()
