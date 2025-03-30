import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import sys
import os
import random
import backoff

# Ajout du répertoire parent au sys.path pour pouvoir importer config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config

logger = logging.getLogger('spareparts-scraper.1001pieces')

# Liste des User-Agents pour alterner et éviter la détection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
]

# Décorateur de retentative avec backoff exponentiel
@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, ConnectionError),
    max_tries=5,
    giveup=lambda e: isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 404
)
def make_request(url, headers):
    """
    Effectue une requête HTTP avec gestion des erreurs et retry
    
    Args:
        url (str): URL à scraper
        headers (dict): Headers HTTP à utiliser
        
    Returns:
        requests.Response: Réponse HTTP
    """
    response = requests.get(url, headers=headers, timeout=config.SCRAPER_TIMEOUT)
    response.raise_for_status()
    return response

def scrape(search_terms=None, max_pages=3):
    """
    Scrape les données de 1001pieces.com
    
    Args:
        search_terms (list): Liste optionnelle de termes de recherche
        max_pages (int): Nombre maximum de pages à scraper par terme de recherche
    
    Returns:
        list: Liste de dictionnaires contenant les données des pièces
    """
    results = []
    
    # Si aucun terme de recherche n'est fourni, utiliser une liste par défaut
    if not search_terms:
        search_terms = ["refrigerateur", "lave-linge", "lave-vaisselle", "four", "micro-onde", "ressort"]
    
    for term in search_terms:
        logger.info(f"Recherche de pièces pour '{term}'")
        
        for page in range(1, max_pages + 1):
            try:
                url = f"https://www.1001pieces.com/recherche?controller=search&s={term}&page={page}"
                
                # Utiliser un User-Agent aléatoire
                user_agent = random.choice(USER_AGENTS)
                headers = {
                    'User-Agent': user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                }
                
                # Ajouter un délai aléatoire pour simuler un comportement humain
                wait_time = config.SCRAPER_DELAY + random.uniform(1.0, 3.0)
                logger.debug(f"Attente de {wait_time:.2f} secondes avant la requête")
                time.sleep(wait_time)
                
                try:
                    response = make_request(url, headers)
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 403:
                        logger.warning(f"Erreur HTTP 403 pour {url} - Le site bloque probablement le scraping")
                        logger.info(f"Attente plus longue avant la prochaine tentative...")
                        time.sleep(random.uniform(10.0, 15.0))  # Attente plus longue
                        continue
                    else:
                        logger.warning(f"Erreur HTTP {e.response.status_code} pour {url}")
                        break
                
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Correction du sélecteur basé sur l'analyse du site
                products = soup.select('.product-miniature.js-product-miniature')
                
                if not products:
                    logger.info(f"Aucun produit trouvé pour '{term}' sur la page {page}")
                    break
                
                for product in products:
                    try:
                        # Extraction des données du produit
                        item = {}
                        
                        # ID du produit
                        data_id = product.get('data-id-product')
                        if data_id:
                            item['reference'] = f"1001P-{data_id}"
                        else:
                            # Si pas d'ID, on passe au produit suivant
                            continue
                        
                        # Nom du produit
                        name_elem = product.select_one('.product-title a')
                        if name_elem:
                            item['name'] = name_elem.text.strip()
                        else:
                            # Sans nom, on passe au produit suivant
                            continue
                        
                        # URL du produit
                        if name_elem and 'href' in name_elem.attrs:
                            item['url'] = name_elem['href']
                        
                        # Image
                        img_elem = product.select_one('.thumbnail img')
                        if img_elem:
                            # Différentes possibilités pour l'URL de l'image
                            if 'src' in img_elem.attrs:
                                item['image_url'] = img_elem['src']
                            elif 'data-src' in img_elem.attrs:
                                item['image_url'] = img_elem['data-src']
                        
                        # Prix
                        price_elem = product.select_one('.product-price-and-shipping .price')
                        if price_elem:
                            price_text = price_elem.text.strip()
                            # Extraction du prix numérique
                            price_match = re.search(r'(\d+[.,]\d+)', price_text)
                            if price_match:
                                item['price'] = float(price_match.group(1).replace(',', '.'))
                        
                        # Disponibilité
                        availability_elem = product.select_one('.product-availabilities')
                        if availability_elem:
                            # Rechercher directement le texte "En stock"
                            in_stock = "en stock" in availability_elem.text.strip().lower()
                            item['in_stock'] = in_stock
                        else:
                            # Par défaut, on considère que le produit est en stock s'il est affiché
                            item['in_stock'] = True
                        
                        # Catégorie basée sur le terme de recherche
                        item['category'] = term
                        
                        # Vérifier les données minimales requises
                        if item.get('reference') and item.get('name'):
                            results.append(item)
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de l'extraction d'un produit: {str(e)}")
                        continue
                
                logger.info(f"Page {page} pour '{term}': {len(products)} produits extraits")
                
            except Exception as e:
                logger.error(f"Erreur lors du scraping de la page {page} pour '{term}': {str(e)}")
                break
    
    logger.info(f"Scraping terminé pour 1001pieces. Total: {len(results)} produits")
    return results

if __name__ == "__main__":
    # Configuration du logging pour les tests standalone
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test du scraper
    results = scrape(max_pages=1)
    for item in results[:5]:  # Afficher les 5 premiers résultats
        print(f"Référence: {item['reference']}")
        print(f"Nom: {item['name']}")
        print(f"Prix: {item.get('price')}")
        print(f"En stock: {item.get('in_stock')}")
        print("---")
