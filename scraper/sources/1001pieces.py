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
def make_request(url,