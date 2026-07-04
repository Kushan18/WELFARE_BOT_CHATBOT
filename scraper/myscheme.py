import httpx
from bs4 import BeautifulSoup
from scraper.base import make_scheme
import logging
import re

logger = logging.getLogger(__name__)

SITEMAP_URL = "https://www.myscheme.gov.in/sitemap-0.xml"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape() -> list:
    """Scrape myscheme.gov.in via its sitemap to bypass API blocks.
    Returns a combined list of schemes.
    """
    schemes = []
    
    try:
        resp = httpx.get(SITEMAP_URL, headers=HEADERS, timeout=30, follow_redirects=True)
        if resp.status_code != 200:
            logger.error(f"myscheme sitemap returned status {resp.status_code}")
            return schemes
            
        soup = BeautifulSoup(resp.content, "xml")
        urls = soup.find_all("loc")
        
        # We only want URLs that look like scheme pages, e.g., /schemes/
        for loc in urls:
            url = loc.text.strip()
            if "/schemes/" in url:
                # Extract a readable title from the URL slug
                # Example: https://www.myscheme.gov.in/schemes/pm-kisan -> pm-kisan
                slug = url.split("/schemes/")[-1].strip("/")
                if not slug:
                    continue
                
                # Convert slug to readable name: pm-kisan -> Pm Kisan
                title = " ".join(word.capitalize() for word in slug.split("-"))
                
                scheme = make_scheme({
                    "name": title,
                    "description": "Central Government Scheme sourced from MyScheme portal.",
                    "apply_link": url,
                    "state": "All", # The NLP or manual step can narrow this down later
                    "source": "myscheme.gov.in",
                    "category": "General"
                })
                schemes.append(scheme)
                
                # Limit to first 100 to prevent database flooding if there are thousands
                if len(schemes) >= 100:
                    break
                    
        logger.info(f"myscheme: scraped {len(schemes)} schemes from sitemap")
        
    except Exception as e:
        logger.error(f"myscheme sitemap scrape failed: {e}")
        
    return schemes