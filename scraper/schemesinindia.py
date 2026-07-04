import httpx
from bs4 import BeautifulSoup
from .base import make_scheme
import logging

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_URL = "https://schemesinindia.in"

TARGET_URLS = {
    "Telangana": "https://schemesinindia.in/telangana-government-schemes/",
    "Andhra Pradesh": "https://schemesinindia.in/andhra-pradesh-government-schemes/",
    "Central": "https://schemesinindia.in/central-government-schemes/"
}

def scrape():
    schemes = []
    
    for state, url in TARGET_URLS.items():
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
            if resp.status_code != 200:
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            headings = soup.find_all(['h2', 'h3'])
            
            for h in headings:
                a_tag = h.find('a')
                if not a_tag:
                    continue
                    
                title = a_tag.text.strip()
                link = a_tag.get('href', '')
                
                if "scheme" not in title.lower() and "yojana" not in title.lower():
                    continue
                    
                scheme = make_scheme({
                    "name": title,
                    "description": f"Government welfare scheme for {state}.",
                    "apply_link": link if link.startswith("http") else f"{BASE_URL}{link}",
                    "state": state if state != "Central" else "All",
                    "source": "schemesinindia.in"
                })
                schemes.append(scheme)
                
        except Exception as e:
            logger.error(f"Error scraping schemesinindia for {state}: {e}")
            
    return schemes
