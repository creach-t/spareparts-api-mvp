import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import sys
import os

# Ajout du répertoire parent au sys.path pour pouvoir importer config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config

logger = logging.getLogger('spareparts-scraper.sosaccessoire')

def scrape(search_terms=None, max_pages=3):
    """
    Scrape les données de sosaccessoire.com
    
    Args:
        search_terms (list): Liste optionnelle de termes de recherche
        max_pages (int): Nombre maximum de pages à scraper par terme de recherche
    
    Returns:
        list: Liste de dictionnaires contenant les données des pièces
    """
    results = []
    
    # Si aucun terme de recherche n'est fourni, utiliser une liste par défaut
    if not search_terms:
        search_terms = ["refrigerateur", "lave-linge", "lave-vaisselle", "four", "micro-onde"]
    
    for term in search_terms:
        logger.info(f"Recherche de pièces pour '{term}'")
        
        for page in range(1, max_pages + 1):
            try:
                url = f"https://www.sosaccessoire.com/recherche?controller=search&s={term}&page={page}"
                response = requests.get(
                    url,
                    headers={'User-Agent': config.SCRAPER_USER_AGENT},
                    timeout=config.SCRAPER_TIMEOUT
                )
                
                if response.status_code != 200:
                    logger.warning(f"Erreur HTTP {response.status_code} pour {url}")
                    break
                
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Extraction des produits
                products = soup.select('.product-miniature')
                
                if not products:
                    logger.info(f"Aucun produit trouvé pour '{term}' sur la page {page}")
                    break
                
                for product in products:
                    try:
                        # Extraction des données du produit
                        item = {}
                        
                        # Référence
                        reference_elem = product.select_one('.product-reference')
                        if reference_elem:
                            reference_text = reference_elem.text.strip()
                            # Utilisation d'une expression régulière pour extraire la référence
                            reference_match = re.search(r'Référence\s*:\s*([A-Za-z0-9\-]+)', reference_text)
                            if reference_match:
                                item['reference'] = reference_match.group(1)
                            else:
                                # Si pas de référence claire, on utilise l'ID du produit
                                data_id = product.get('data-id-product')
                                if data_id:
                                    item['reference'] = f"SOS-{data_id}"
                                else:
                                    # Si toujours pas de référence, on passe au produit suivant
                                    continue
                        else:
                            # Si pas d'élément de référence, on vérifie s'il y a un data-id-product
                            data_id = product.get('data-id-product')
                            if data_id:
                                item['reference'] = f"SOS-{data_id}"
                            else:
                                # Si toujours pas de référence, on passe au produit suivant
                                continue
                        
                        # Nom du produit
                        name_elem = product.select_one('.product-title a')
                        item['name'] = name_elem.text.strip() if name_elem else ""
                        
                        # URL du produit
                        if name_elem and 'href' in name_elem.attrs:
                            item['url'] = name_elem['href']
                        
                        # Image
                        img_elem = product.select_one('.product-thumbnail img')
                        if img_elem:
                            # SosAccessoire peut utiliser soit src, soit data-src pour les images
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
                        availability_elem = product.select_one('.product-availability')
                        if availability_elem:
                            availability_text = availability_elem.text.strip().lower()
                            item['in_stock'] = "disponible" in availability_text or "en stock" in availability_text
                        else:
                            # Par défaut, on considère que le produit est en stock s'il est affiché
                            item['in_stock'] = True
                        
                        # Description (courte)
                        description_elem = product.select_one('.product-description')
                        if description_elem:
                            item['description'] = description_elem.text.strip()
                        
                        # Catégorie basée sur le terme de recherche
                        item['category'] = term
                        
                        # Vérifier les données minimales requises
                        if item.get('reference') and item.get('name'):
                            results.append(item)
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de l'extraction d'un produit: {str(e)}")
                        continue
                
                logger.info(f"Page {page} pour '{term}': {len(products)} produits extraits")
                
                # Pause entre les requêtes pour éviter de surcharger le serveur
                time.sleep(config.SCRAPER_DELAY)
            
            except Exception as e:
                logger.error(f"Erreur lors du scraping de la page {page} pour '{term}': {str(e)}")
                break
    
    logger.info(f"Scraping terminé pour SosAccessoire. Total: {len(results)} produits")
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
