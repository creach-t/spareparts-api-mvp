from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
import sys
from datetime import datetime

# Ajout du répertoire parent au sys.path pour pouvoir importer config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Création de l'engine et de la session SQLAlchemy
engine = create_engine(config.DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# Base de classe pour les modèles déclaratifs
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    """Initialise la base de données et créée les tables"""
    from database.models import Part, Supplier, Availability
    
    # Création des tables
    Base.metadata.create_all(bind=engine)
    
    # Vérification si les fournisseurs existent déjà
    existing_suppliers = Supplier.query.all()
    if not existing_suppliers:
        # Ajout des fournisseurs initiaux
        for source in config.SOURCES:
            if source['enabled']:
                supplier = Supplier(
                    name=source['name'],
                    website=source['website'],
                    created_at=datetime.utcnow()
                )
                db_session.add(supplier)
        
        db_session.commit()
        print("Base de données initialisée avec les fournisseurs")
    else:
        print("Base de données déjà initialisée")

def close_db_session():
    """Ferme la session de base de données"""
    db_session.remove()
