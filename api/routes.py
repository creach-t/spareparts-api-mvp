from flask import Blueprint, jsonify, request
from flask_restful import Api, Resource
from database.models import Part, Supplier, Availability, ApiKey
from database.db import db_session
from api.auth import auth, generate_api_key
from sqlalchemy import or_, and_, join
import logging
from datetime import datetime
import re
import sys
import os

# Ajout du répertoire parent au sys.path pour pouvoir importer config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Configuration du logging
logger = logging.getLogger('spareparts-api.routes')

# Création d'un blueprint pour les routes API
api_bp = Blueprint('api', __name__)
api = Api(api_bp)


# Ressource pour la liste et la recherche de pièces
class PartsList(Resource):
    @auth.login_required
    def get(self):
        """
        Retourne la liste des pièces avec filtres optionnels
        
        Query Parameters:
            category (str): Filtre par catégorie
            keyword (str): Recherche par mot-clé (dans le nom ou la description)
            limit (int): Limite le nombre de résultats (défaut: 50)
            offset (int): Décalage pour la pagination (défaut: 0)
        
        Returns:
            JSON: Liste des pièces correspondantes
        """
        try:
            # Récupération des paramètres de requête
            category = request.args.get('category')
            keyword = request.args.get('keyword')
            
            # Validation et protection contre les injections SQL
            try:
                limit = min(int(request.args.get('limit', 50)), 100)  # Maximum 100 résultats
                offset = max(int(request.args.get('offset', 0)), 0)  # Minimum 0
            except (ValueError, TypeError):
                return {'error': 'Les paramètres limit et offset doivent être des nombres entiers'}, 400
            
            # Construction de la requête de base
            query = Part.query
            
            # Application des filtres
            if category:
                # Échapper les caractères spéciaux pour éviter les injections
                category = re.escape(category)
                query = query.filter(Part.category == category)
            
            if keyword:
                # Échapper les caractères spéciaux pour éviter les injections
                keyword = re.escape(keyword)
                query = query.filter(
                    or_(
                        Part.name.ilike(f'%{keyword}%'),
                        Part.description.ilike(f'%{keyword}%'),
                        Part.reference.ilike(f'%{keyword}%')
                    )
                )
            
            # Comptage du nombre total d'éléments
            total_count = query.count()
            
            # Application de la pagination
            parts = query.order_by(Part.updated_at.desc()).offset(offset).limit(limit).all()
            
            # Conversion en dictionnaire pour la sérialisation JSON
            parts_data = [part.to_dict() for part in parts]
            
            logger.info(f"Liste des pièces renvoyée: {len(parts_data)} résultats (total: {total_count})")
            
            return jsonify({
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'data': parts_data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la liste des pièces: {str(e)}")
            return {'error': 'Une erreur est survenue lors de la récupération des pièces'}, 500


# Ressource pour la recherche de pièces par référence
class PartsSearch(Resource):
    @auth.login_required
    def get(self):
        """
        Recherche des pièces par référence
        
        Query Parameters:
            reference (str): Référence à rechercher (peut être partielle)
        
        Returns:
            JSON: Liste des pièces correspondantes
        """
        try:
            reference = request.args.get('reference')
            
            if not reference:
                return {'error': 'Le paramètre reference est requis'}, 400
            
            # Validation pour éviter les injections
            reference = re.escape(reference)
            
            # Recherche des pièces par référence (correspondance partielle)
            parts = Part.query.filter(Part.reference.ilike(f'%{reference}%')).all()
            
            # Conversion en dictionnaire pour la sérialisation JSON
            parts_data = [part.to_dict() for part in parts]
            
            logger.info(f"Recherche par référence '{reference}': {len(parts_data)} résultats")
            
            return jsonify({
                'total': len(parts_data),
                'data': parts_data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche par référence: {str(e)}")
            return {'error': 'Une erreur est survenue lors de la recherche'}, 500


# Ressource pour les détails d'une pièce spécifique
class PartDetail(Resource):
    @auth.login_required
    def get(self, part_id):
        """
        Retourne les détails d'une pièce spécifique
        
        Args:
            part_id (int): ID de la pièce
        
        Returns:
            JSON: Détails de la pièce
        """
        try:
            # Validation de l'ID
            try:
                part_id = int(part_id)
                if part_id <= 0:
                    raise ValueError("ID invalide")
            except (ValueError, TypeError):
                return {'error': 'ID de pièce invalide'}, 400
                
            part = Part.query.get(part_id)
            
            if not part:
                return {'error': 'Pièce non trouvée'}, 404
            
            # Conversion en dictionnaire pour la sérialisation JSON
            part_data = part.to_dict()
            
            logger.info(f"Détails de la pièce {part_id} renvoyés")
            
            return jsonify(part_data)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des détails de la pièce {part_id}: {str(e)}")
            return {'error': 'Une erreur est survenue lors de la récupération des détails de la pièce'}, 500


# Ressource pour la disponibilité d'une pièce spécifique
class PartAvailability(Resource):
    @auth.login_required
    def get(self, part_id):
        """
        Retourne la disponibilité et les prix d'une pièce chez les différents fournisseurs
        
        Args:
            part_id (int): ID de la pièce
        
        Returns:
            JSON: Disponibilité et prix de la pièce
        """
        try:
            # Validation de l'ID
            try:
                part_id = int(part_id)
                if part_id <= 0:
                    raise ValueError("ID invalide")
            except (ValueError, TypeError):
                return {'error': 'ID de pièce invalide'}, 400
                
            # Récupération de la pièce avec optimisation des requêtes
            part = Part.query.get(part_id)
            
            if not part:
                return {'error': 'Pièce non trouvée'}, 404
            
            # Récupération des disponibilités avec jointure pour éviter requêtes N+1
            # Chargement à la fois des relations supplier pour chaque disponibilité
            availabilities = Availability.query.join(
                Supplier, Availability.supplier_id == Supplier.id
            ).filter(
                Availability.part_id == part_id
            ).all()
            
            # Conversion en dictionnaire pour la sérialisation JSON
            availability_data = [availability.to_dict() for availability in availabilities]
            
            logger.info(f"Disponibilité de la pièce {part_id} renvoyée: {len(availability_data)} fournisseurs")
            
            return jsonify({
                'part_id': part_id,
                'part_reference': part.reference,
                'part_name': part.name,
                'availabilities': availability_data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la disponibilité de la pièce {part_id}: {str(e)}")
            return {'error': 'Une erreur est survenue lors de la récupération de la disponibilité'}, 500


# Ressource pour la liste des fournisseurs
class SuppliersList(Resource):
    @auth.login_required
    def get(self):
        """
        Retourne la liste des fournisseurs
        
        Returns:
            JSON: Liste des fournisseurs
        """
        try:
            suppliers = Supplier.query.all()
            
            # Conversion en dictionnaire pour la sérialisation JSON
            suppliers_data = [supplier.to_dict() for supplier in suppliers]
            
            logger.info(f"Liste des fournisseurs renvoyée: {len(suppliers_data)} résultats")
            
            return jsonify({
                'total': len(suppliers_data),
                'data': suppliers_data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la liste des fournisseurs: {str(e)}")
            return {'error': 'Une erreur est survenue lors de la récupération des fournisseurs'}, 500


# Route pour générer une clé API (à utiliser en développement ou via un CLI)
class GenerateApiKey(Resource):
    def post(self):
        """
        Génère une nouvelle clé API
        
        POST Body:
            name (str): Nom associé à la clé API
            email (str): Email associé à la clé API
            secret (str): Secret pour autoriser la génération (à configurer)
        
        Returns:
            JSON: Nouvelle clé API
        """
        try:
            # Dans un environnement de production, cette route devrait être protégée ou désactivée
            # et la génération de clé devrait se faire via un CLI ou une interface admin
            
            # Récupération des données de la requête
            data = request.get_json()
            
            if not data:
                return {'error': 'Données JSON requises'}, 400
            
            name = data.get('name')
            email = data.get('email')
            secret = data.get('secret')
            
            # Vérification des données requises
            if not name or not email or not secret:
                return {'error': 'Nom, email et secret requis'}, 400
            
            # Vérification du secret en utilisant la valeur de config
            if secret != config.API_KEY_GENERATION_SECRET:
                return {'error': 'Secret invalide'}, 403
            
            # Validation de l'email
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                return {'error': 'Format d\'email invalide'}, 400
            
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
            
            logger.info(f"Nouvelle clé API générée pour {name} ({email})")
            
            return jsonify({
                'key': api_key,
                'name': name,
                'email': email,
                'created_at': new_key.created_at.isoformat()
            })
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Erreur lors de la génération de la clé API: {str(e)}")
            return {'error': 'Une erreur est survenue lors de la génération de la clé API'}, 500


# Enregistrement des routes
api.add_resource(PartsList, '/parts')
api.add_resource(PartsSearch, '/parts/search')
api.add_resource(PartDetail, '/parts/<int:part_id>')
api.add_resource(PartAvailability, '/parts/<int:part_id>/availability')
api.add_resource(SuppliersList, '/suppliers')
api.add_resource(GenerateApiKey, '/generate-key')


# Route racine pour vérifier que l'API fonctionne
@api_bp.route('/')
def index():
    return jsonify({
        'name': 'SpareParts API',
        'version': '1.0.0',
        'status': 'OK',
        'endpoints': [
            '/api/parts',
            '/api/parts/search',
            '/api/parts/<id>',
            '/api/parts/<id>/availability',
            '/api/suppliers'
        ]
    })
