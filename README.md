# SpareParts API - MVP

Service MVP qui scrape les données de disponibilité des pièces détachées d'électroménager et les expose via une API simple.

## Objectifs

- Scraper les données de 2-3 sites majeurs de pièces détachées
- Stocker ces données dans une base simple
- Exposer les données via une API REST basique
- Mettre en place un système d'authentification minimaliste

## Structure du projet

```
spareparts-mvp/
├── scraper/
│   ├── scraper.py         # Logique de scraping principale
│   └── sources/           # Un fichier par site source
│       ├── source1.py
│       └── source2.py
│
├── database/
│   ├── models.py          # Modèles de données simplifiés
│   └── db.py              # Connexion à la base de données
│
├── api/
│   ├── app.py             # Application principale
│   ├── routes.py          # Routes de l'API
│   └── auth.py            # Authentification simple
│
├── config.py              # Configuration centralisée
├── requirements.txt       # Dépendances
└── README.md              # Documentation
```

## Schéma de base de données

```
Table parts:
- id (PK)
- reference (Index)
- name
- description
- category
- image_url
- created_at
- updated_at

Table suppliers:
- id (PK)
- name
- website
- created_at

Table availability:
- id (PK)
- part_id (FK)
- supplier_id (FK)
- price
- in_stock (boolean)
- url
- last_checked
```

## Technologies utilisées

- **Scraping**: Python avec BeautifulSoup ou Requests-HTML
- **Base de données**: SQLite
- **API**: Flask avec authentification par clé API
- **Endpoints**:
  - GET /parts: Liste des pièces avec filtres basiques
  - GET /parts/{id}: Détails d'une pièce
  - GET /parts/search: Recherche par référence
  - GET /parts/{id}/availability: Disponibilité et prix

## Installation et démarrage

1. Créer un environnement virtuel Python
   ```
   python -m venv venv
   source venv/bin/activate  # Sur Windows: venv\Scripts\activate
   ```

2. Installer les dépendances
   ```
   pip install -r requirements.txt
   ```

3. Configurer les sources dans config.py

4. Initialiser la base de données
   ```
   python -c "from database.db import init_db; init_db()"
   ```

5. Exécuter un premier scraping
   ```
   python -m scraper.scraper
   ```

6. Démarrer l'API
   ```
   python -m api.app
   ```

## Authentification

L'API utilise une authentification simple par clé API. Pour accéder aux endpoints, incluez votre clé API dans l'en-tête de la requête :

```
Authorization: ApiKey YOUR_API_KEY
```

## Limites d'utilisation

- 100 requêtes par jour par clé API

## Développements futurs (post-MVP)

- Ajout de davantage de sources
- Système de scraping plus robuste
- Historique des prix
- Relations pièces-appareils
- Authentification plus élaborée
- Plans d'abonnement
- Documentation interactive
