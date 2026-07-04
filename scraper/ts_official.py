import logging
import httpx
import time
from bs4 import BeautifulSoup
from scraper.base import make_scheme

# Shared request headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

logger = logging.getLogger(__name__)

def _is_noise(name: str, description: str) -> bool:
    if len(name.strip()) < 8:
        return True
    blacklist = [
        "website",
        "overview",
        "activities",
        "contact",
        "services",
        "directory",
        "navigation",
        "menu",
        "home",
        "about",
        "login",
        "initiatives",
        "media",
        "contacts",
        "link",
        "click here",
        "read more",
        "view details"
    ]
    name_lower = name.lower()
    if any(word in name_lower for word in blacklist):
        return True
    if len(description.strip()) < 40:
        return True
    return False

def _scrape_page(url: str, state: str) -> list:
    from urllib.parse import urlparse
    source_domain = urlparse(url).netloc.replace("www.", "") or "telangana.gov.in"
    schemes = []
    try:
        resp = httpx.get(url, timeout=15, headers=HEADERS, follow_redirects=True)
        logger.info(f"ts_official: fetched {url} status {resp.status_code}")
        logger.debug(f"ts_official raw HTML (first 1000 chars): {resp.text[:1000]}")
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # If this is the main initiatives page, use h4 tags
        if "government-initiatives" in url:
            headings = soup.find_all("h4")
            for heading in headings:
                name = heading.get_text(strip=True)
                desc_parts = []
                nxt = heading.next_sibling
                while nxt and not (nxt.name and nxt.name in ["h4", "h3", "h2", "h1"]):
                    if nxt.name == "p":
                        desc_parts.append(nxt.get_text(strip=True))
                    nxt = nxt.next_sibling
                description = " ".join(desc_parts).strip()
                
                if _is_noise(name, description):
                    continue
                
                scheme = make_scheme({
                    "name": name,
                    "description": description,
                    "apply_link": url,
                    "state": state,
                    "category": "General",
                    "source": source_domain,
                })
                schemes.append(scheme)
        else:
            # Fallback/generic scraping for other pages
            content = soup.find("div", class_="entry-content") or soup.find("div", class_="post-content") or soup.find("div", class_="article") or soup.find("body")
            if content:
                headings = content.find_all(["h2", "h3", "h4", "strong"])
                for heading in headings:
                    name = heading.get_text(strip=True)
                    desc_parts = []
                    nxt = heading.next_sibling
                    while nxt and not (nxt.name and nxt.name in ["h2", "h3", "h4", "strong"]):
                        if nxt.name == "p":
                            desc_parts.append(nxt.get_text(strip=True))
                        nxt = nxt.next_sibling
                    description = " ".join(desc_parts).strip()
                    
                    if _is_noise(name, description):
                        continue
                    
                    scheme = make_scheme({
                        "name": name,
                        "description": description,
                        "apply_link": url,
                        "state": state,
                        "category": "General",
                        "source": source_domain,
                    })
                    schemes.append(scheme)
    except Exception as e:
        logger.error(f"ts_official scrape error for {url}: {e}")
    logger.info(f"ts_official: scraped {len(schemes)} schemes from {url}")
    return schemes

def scrape() -> list:
    """Scrape schemes from the Telangana government initiatives page."""
    URL_TELANGANA = "https://www.telangana.gov.in/government-initiatives/"
    URL_TSCIE = "https://tscie.telangana.gov.in/"
    URL_WDCW = "https://wdcw.tg.nic.in/"
    
    all_schemes = []
    all_schemes.extend(_scrape_page(URL_TELANGANA, "Telangana"))
    time.sleep(0.5)
    all_schemes.extend(_scrape_page(URL_TSCIE, "Telangana"))
    time.sleep(0.5)
    all_schemes.extend(_scrape_page(URL_WDCW, "Telangana"))
    
    logger.info(f"ts_official: total scraped {len(all_schemes)} schemes across sources")
    return all_schemes
