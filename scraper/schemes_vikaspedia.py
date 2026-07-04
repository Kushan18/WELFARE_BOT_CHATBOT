import httpx
from bs4 import BeautifulSoup
from .base import make_scheme
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_URL = "https://schemes.vikaspedia.in/"

def scrape():
    schemes = []
    
    try:
        resp = httpx.get(BASE_URL, headers=HEADERS, timeout=15, follow_redirects=True, verify=False)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Scrape scheme links from the dedicated portal
            links = soup.find_all('a')
            
            for a_tag in links:
                title = a_tag.text.strip()
                href = a_tag.get('href', '')
                
                if not title or not href or len(title) < 5:
                    continue
                    
                # Broad match since it's a dedicated scheme site
                if "scheme" in title.lower() or "yojana" in title.lower() or "fund" in title.lower() or "mission" in title.lower() or "samman" in title.lower():
                    apply_link = href if href.startswith("http") else urljoin(BASE_URL, href)
                    
                    scheme = make_scheme({
                        "name": title,
                        "description": "Government scheme sourced from Vikaspedia Schemes Portal.",
                        "apply_link": apply_link,
                        "state": "All", # Can be enriched later by NLP
                        "source": "schemes.vikaspedia.in"
                    })
                    schemes.append(scheme)
                    
    except Exception as e:
        logger.error(f"Error scraping schemes.vikaspedia.in: {e}")
            
    return schemes
