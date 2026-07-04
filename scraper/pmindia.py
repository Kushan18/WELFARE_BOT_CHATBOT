import logging
import httpx
from bs4 import BeautifulSoup
from scraper.base import make_scheme

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def scrape() -> list:
    """Fetch schemes from PM Modi Yojana portal (or sarkariyojana.com fallback).
    Returns list of scheme dicts via make_scheme.
    """
    target_url = "https://pmmodiyojana.in/"
    fallback_url = "https://sarkariyojana.com/"
    
    html_content = ""
    used_url = ""
    
    # Try pmmodiyojana.in first
    try:
        logger.info(f"pmindia: trying to fetch {target_url}")
        resp = httpx.get(target_url, timeout=10, headers=HEADERS, follow_redirects=True)
        resp.raise_for_status()
        html_content = resp.text
        used_url = target_url
        logger.info(f"pmindia: successfully fetched {target_url}")
    except Exception as e:
        logger.warning(f"pmindia: failed to fetch {target_url} ({e}). Falling back to {fallback_url}")
        try:
            resp = httpx.get(fallback_url, timeout=15, headers=HEADERS, follow_redirects=True)
            resp.raise_for_status()
            html_content = resp.text
            used_url = fallback_url
            logger.info(f"pmindia: successfully fetched fallback {fallback_url}")
        except Exception as fe:
            logger.error(f"pmindia: failed to fetch fallback {fallback_url}: {fe}")
            return []
            
    # Log/Print first 3000 characters of raw HTML to logs as required
    print(f"\nPMINDIA/FALLBACK RAW HTML (first 3000 chars):")
    try:
        print(html_content[:3000].encode('ascii', errors='ignore').decode('ascii'))
    except Exception:
        pass
    logger.debug(f"pmindia raw HTML (first 3000 chars): {html_content[:3000].encode('utf-8', errors='ignore').decode('utf-8')}")
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Print all tag classes found as requested
    print(f"\nALL TAG CLASSES FOUND on {used_url}:")
    tags = set()
    for tag in soup.find_all(True):
        if tag.get("class"):
            tags.add(f"{tag.name}.{' '.join(tag['class'])}")
    for t in sorted(tags)[:30]:
        try:
            print("  ", t.encode('ascii', errors='ignore').decode('ascii'))
        except Exception:
            pass
        
    schemes = []
    
    # Parse <article> elements or <div class="post"> elements
    items = soup.find_all(["article", "div"], class_=lambda c: c and ("post" in c.lower() or "article" in c.lower()))
    if not items:
        # Fallback if classes didn't match
        items = soup.find_all("article")
        
    for item in items:
        try:
            heading_tag = item.find(["h2", "h1", "h3"])
            name = heading_tag.get_text(strip=True) if heading_tag else ""
            
            desc_tag = item.find("p") or item.find(class_=lambda c: c and ("summary" in c.lower() or "content" in c.lower()))
            description = desc_tag.get_text(strip=True) if desc_tag else ""
            
            if not name or len(name) < 8:
                continue
            if not description or len(description) < 40:
                continue
                
            link_tag = item.find("a", href=True)
            href = link_tag["href"] if link_tag else used_url
            apply_link = href if href.startswith("http") else f"{used_url.rstrip('/')}{href}"
            
            from urllib.parse import urlparse
            source_domain = urlparse(used_url).netloc.replace("www.", "") or "sarkariyojana.com"
            scheme = make_scheme({
                "name": name,
                "description": description,
                "apply_link": apply_link,
                "state": "All India",
                "category": "Central",
                "source": source_domain,
            })
            schemes.append(scheme)
        except Exception as item_err:
            logger.error(f"pmindia: error processing article/post: {item_err}")
            
    logger.info(f"pmindia: scraped {len(schemes)} schemes from {used_url}")
    return schemes
