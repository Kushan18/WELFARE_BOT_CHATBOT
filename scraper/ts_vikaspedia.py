import httpx
import json
import logging
from bs4 import BeautifulSoup
from scraper.base import make_scheme
import time

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _is_noise(name: str, description: str) -> bool:
    if len(name.strip()) < 8:
        return True
    keywords = ["directory", "link", "navigation", "menu", "click here"]
    if any(k in name.lower() for k in keywords):
        return True
    if len(description.strip()) < 40:
        return True
    return False

def _scrape_url(url: str) -> list:
    schemes = []
    try:
        resp = httpx.get(url, timeout=15, headers=HEADERS, follow_redirects=True)
        logger.info(f"ts_vikaspedia: fetched {url} status {resp.status_code}")
        logger.debug(f"ts_vikaspedia raw HTML (first 3000 chars): {resp.text[:3000]}")
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            logger.error(f"ts_vikaspedia: could not find __NEXT_DATA__ script tag on {url}")
            return []
            
        data = json.loads(script.string)
        content_list = data.get("props", {}).get("pageProps", {}).get("ssrContentList", [])
        
        for item in content_list:
            name = item.get("title", "").strip()
            desc = item.get("summery", "").strip()
            
            if _is_noise(name, desc):
                continue
                
            path = item.get("context_path", "")
            apply_link = f"https://en.vikaspedia.in{path}" if path.startswith("/") else path
            
            scheme = make_scheme({
                "name": name,
                "description": desc,
                "eligibility": "",
                "benefits": "",
                "apply_link": apply_link,
                "state": "Telangana",
                "source": "vikaspedia.in",
                "category": "Welfare",
            })
            schemes.append(scheme)
    except Exception as e:
        logger.error(f"ts_vikaspedia: failed to scrape {url}: {e}")
    return schemes

def scrape() -> list:
    """Scrape multiple Telangana welfare scheme directories from Vikaspedia."""
    urls = [
        "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-telangana",
        "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-telangana/sc-welfare-schemes-telangana",
        "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-telangana/bc-welfare-schemes-telangana",
        "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-telangana/women-welfare-schemes-telangana"
    ]
    
    all_schemes = []
    for url in urls:
        all_schemes.extend(_scrape_url(url))
        time.sleep(0.5)  # Be polite to the server
        
    logger.info(f"ts_vikaspedia: scraped {len(all_schemes)} schemes total across categories")
    return all_schemes