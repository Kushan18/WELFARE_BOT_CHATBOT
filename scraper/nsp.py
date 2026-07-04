import httpx
from bs4 import BeautifulSoup
from .base import make_scheme
import logging

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# We use a reliable public list since the main scholarships.gov.in portal requires JS
NSP_FALLBACK_URL = "https://www.buddy4study.com/article/national-scholarship-portal"

def scrape():
    schemes = []
    
    try:
        resp = httpx.get(NSP_FALLBACK_URL, headers=HEADERS, timeout=15, follow_redirects=True)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Buddy4Study usually lists schemes in tables
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 2:
                        title_text = cols[0].text.strip()
                        
                        if "scholarship" not in title_text.lower() and "scheme" not in title_text.lower():
                            continue
                            
                        # Often the link is in the text or we provide the main NSP portal link
                        apply_link = "https://scholarships.gov.in/"
                        
                        scheme = make_scheme({
                            "name": title_text,
                            "description": "Central Government Scholarship Scheme via National Scholarship Portal.",
                            "apply_link": apply_link,
                            "state": "All",
                            "source": "scholarships.gov.in"
                        })
                        schemes.append(scheme)
                        
    except Exception as e:
        logger.error(f"Error scraping NSP schemes: {e}")
            
    return schemes
