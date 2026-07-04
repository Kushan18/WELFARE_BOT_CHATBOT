import httpx
from bs4 import BeautifulSoup
from .base import make_scheme
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_URL = "https://www.india.gov.in/my-government/schemes"
DOMAIN = "https://www.india.gov.in"

def scrape():
    schemes = []
    
    try:
        resp = httpx.get(BASE_URL, headers=HEADERS, timeout=15, follow_redirects=True, verify=False)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find the view-content div or just look for article links
            links = soup.find_all('a')
            
            for a_tag in links:
                title = a_tag.text.strip()
                href = a_tag.get('href', '')
                
                if not title or not href:
                    continue
                    
                if "scheme" in title.lower() or "yojana" in title.lower() or "fund" in title.lower():
                    apply_link = href if href.startswith("http") else urljoin(DOMAIN, href)
                    
                    scheme = make_scheme({
                        "name": title,
                        "description": "Central Government Scheme listed on National Portal of India.",
                        "apply_link": apply_link,
                        "state": "All",
                        "source": "india.gov.in"
                    })
                    schemes.append(scheme)
                    
    except Exception as e:
        logger.error(f"Error scraping india.gov.in: {e}")
            
    return schemes
