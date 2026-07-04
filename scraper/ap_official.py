import httpx
import logging
from bs4 import BeautifulSoup
import pandas as pd
from scraper.base import make_scheme

logger = logging.getLogger(__name__)

# Primary and additional source URLs
URL_MAIN = "https://socialwelfare.apcfss.in/schemes.html"
URL_AP_EWALFARE = "https://apewalfare.ap.gov.in/"
URL_WOMEN_AP = "https://women.ap.gov.in/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _is_noise(name: str, description: str) -> bool:
    if len(name.strip()) < 8:
        return True
    keywords = ["directory", "link", "navigation", "menu", "click here", "read more", "view details", "website"]
    if any(k in name.lower() for k in keywords):
        return True
    if len(description.strip()) < 40:
        return True
    return False

def _scrape_ap_welfare_page(url: str) -> list:
    """Specialized parser for socialwelfare.apcfss.in/schemes.html based on actual div.captions class structure."""
    schemes = []
    try:
        resp = httpx.get(url, timeout=15, headers=HEADERS, follow_redirects=True)
        logger.info(f"ap_official ap_welfare: fetched {url} status {resp.status_code}")
        logger.debug(f"ap_official ap_welfare raw HTML (first 3000 chars): {resp.text[:3000]}")
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Find all caption divs
        captions = soup.find_all("div", class_=lambda c: c and "caption" in c.lower())
        for c in captions:
            name = c.get_text(strip=True)
            desc_parts = []
            
            # Find subsequent p.desc-para or p siblings
            nxt = c.next_sibling
            while nxt and not (nxt.name and "caption" in "".join(nxt.get("class", [])).lower()):
                if nxt.name == "p":
                    desc_parts.append(nxt.get_text(strip=True))
                nxt = nxt.next_sibling
                
            description = " ".join(desc_parts).strip()
            
            if _is_noise(name, description):
                continue
                
            schemes.append(make_scheme({
                "name": name,
                "description": description,
                "eligibility": "",
                "benefits": "",
                "apply_link": url,
                "state": "Andhra Pradesh",
                "source": "apcfss.in",
                "category": "Social Welfare",
            }))
    except Exception as e:
        logger.error(f"ap_official ap_welfare page scrape failed: {e}")
    return schemes

def _scrape_generic(url: str) -> list:
    """Fallback HTML parsing for other sites using heading tags and adjacent paragraphs."""
    schemes = []
    try:
        resp = httpx.get(url, timeout=15, headers=HEADERS, follow_redirects=True)
        logger.info(f"ap_official generic: fetched {url} status {resp.status_code}")
        logger.debug(f"ap_official generic raw HTML (first 3000 chars): {resp.text[:3000]}")
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        for heading in soup.find_all(["h2", "h3", "h4"]):
            name = heading.get_text(strip=True)
            if not name:
                continue
            desc = ""
            eligibility = ""
            nxt = heading.find_next_sibling()
            while nxt and nxt.name in ["p", "ul", "ol"]:
                txt = nxt.get_text(strip=True)
                if "eligib" in txt.lower():
                    eligibility = txt
                elif not desc:
                    desc = txt
                nxt = nxt.find_next_sibling()
            if _is_noise(name, desc):
                continue
            schemes.append(make_scheme({
                "name": name,
                "description": desc,
                "eligibility": eligibility,
                "benefits": "",
                "apply_link": url,
                "state": "Andhra Pradesh",
                "source": "apcfss.in",
                "category": "Social Welfare",
            }))
    except Exception as e:
        logger.error(f"ap_official generic scrape failed for {url}: {e}")
    return schemes

def scrape() -> list:
    all_schemes = []
    # Try the custom captions-based scraping for the main page
    all_schemes.extend(_scrape_ap_welfare_page(URL_MAIN))
    
    # Try table-based / generic fallbacks only if we got nothing
    if not all_schemes:
        try:
            tables = pd.read_html(URL_MAIN)
            for df in tables:
                cols = {c.lower(): c for c in df.columns}
                if not any(k in cols for k in ["scheme", "name", "title"]):
                    continue
                for _, row in df.iterrows():
                    name = row.get(cols.get("scheme")) or row.get(cols.get("name")) or row.get(cols.get("title")) or ""
                    description = row.get(cols.get("description")) or ""
                    if _is_noise(str(name), str(description)):
                        continue
                    all_schemes.append(make_scheme({
                        "name": str(name),
                        "description": str(description),
                        "eligibility": str(row.get(cols.get("eligibility"), "")),
                        "benefits": str(row.get(cols.get("benefits"), "")),
                        "apply_link": str(row.get(cols.get("apply_link"), URL_MAIN)),
                        "state": "Andhra Pradesh",
                        "source": "apcfss.in",
                        "category": "Social Welfare",
                    }))
        except Exception as e:
            logger.debug(f"Table scrape fallback skipped: {e}")
            
    # Additional Andhra Pradesh sources
    all_schemes.extend(_scrape_generic(URL_AP_EWALFARE))
    all_schemes.extend(_scrape_generic(URL_WOMEN_AP))
    
    logger.info(f"ap_official: scraped total {len(all_schemes)} schemes across sources")
    return all_schemes
