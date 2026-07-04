import httpx
import json
import logging
from bs4 import BeautifulSoup
from scraper.base import make_scheme

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
        logger.info(f"vikaspedia_central: fetched {url} status {resp.status_code}")
        logger.debug(f"vikaspedia_central raw HTML (first 3000 chars): {resp.text[:3000]}")
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Print tag classes found as requested
        print(f"\nALL TAG CLASSES FOUND on {url}:")
        tags = set()
        for tag in soup.find_all(True):
            if tag.get("class"):
                tags.add(f"{tag.name}.{' '.join(tag['class'])}")
        for t in sorted(tags)[:20]:
            try:
                print("  ", t.encode('ascii', errors='ignore').decode('ascii'))
            except Exception:
                pass
            
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            logger.error(f"vikaspedia_central: no __NEXT_DATA__ script on {url}")
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
                "state": "All India",
                "source": "vikaspedia.in",
                "category": "Central",
            })
            schemes.append(scheme)
    except Exception as e:
        logger.error(f"vikaspedia_central failed to scrape {url}: {e}")
    return schemes

def scrape() -> list:
    """Scrape Central sector and government schemes from Vikaspedia using Next.js __NEXT_DATA__ JSON."""
    urls = [
        "https://en.vikaspedia.in/viewcontent/schemesall/central-sector-schemes",
        "https://en.vikaspedia.in/viewcontent/schemesall/central-government-schemes"
    ]
    all_schemes = []
    for url in urls:
        all_schemes.extend(_scrape_url(url))
    logger.info(f"vikaspedia_central: scraped {len(all_schemes)} schemes total")
    return all_schemes
