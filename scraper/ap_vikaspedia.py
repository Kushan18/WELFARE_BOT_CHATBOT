import httpx
import json
import logging
from bs4 import BeautifulSoup
from scraper.base import make_scheme

logger = logging.getLogger(__name__)
URL = "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-andhra-pradesh"

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

def scrape():
    """Scrape Andhra Pradesh welfare schemes from Vikaspedia using Next.js __NEXT_DATA__ JSON."""
    try:
        resp = httpx.get(URL, timeout=15, headers=HEADERS, follow_redirects=True)
        logger.info(f"ap_vikaspedia: fetched {URL} status {resp.status_code}")
        logger.debug(f"ap_vikaspedia raw HTML (first 3000 chars): {resp.text[:3000]}")
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            logger.error("ap_vikaspedia: could not find __NEXT_DATA__ script tag")
            return []
            
        data = json.loads(script.string)
        content_list = data.get("props", {}).get("pageProps", {}).get("ssrContentList", [])
        
        schemes = []
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
                "state": "Andhra Pradesh",
                "source": "vikaspedia.in",
                "category": "Welfare",
            })
            schemes.append(scheme)
            
        logger.info(f"ap_vikaspedia: scraped {len(schemes)} schemes")
        return schemes
    except Exception as e:
        logger.error(f"ap_vikaspedia failed: {e}")
        return []