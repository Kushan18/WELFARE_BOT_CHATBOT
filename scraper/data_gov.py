import httpx
from scraper.base import make_scheme
import logging

logger = logging.getLogger(__name__)
BASE = "https://data.gov.in/api/datastore/resource.json"
SEARCH_API = "https://data.gov.in/api/3/action/package_search"

def _discover_resource_id() -> str:
    """Discover the current resource ID for welfare schemes dataset.
    Returns the resource ID or empty string if not found.
    """
    try:
        # Search for welfare schemes dataset
        search_url = f"{SEARCH_API}?q=welfare+schemes&rows=10"
        resp = httpx.get(search_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        
        # Look for the first matching package
        results = data.get("result", {}).get("results", [])
        if results:
            # Get the first result's resources
            resources = results[0].get("resources", [])
            if resources:
                # Return the most recent resource ID
                resource_id = resources[0].get("id", "")
                logger.info(f"data_gov: discovered resource_id={resource_id}")
                return resource_id
    except Exception as e:
        logger.error(f"data_gov: failed to discover resource_id - {e}")
    
    # Fallback to hardcoded ID
    logger.warning("data_gov: using fallback resource_id")
    return "6176b896-d8c2-4426-b3db-4cf6bf585e16"

def scrape():
    schemes = []
    resource_id = _discover_resource_id()
    if not resource_id:
        logger.error("data_gov: no resource_id available, skipping")
        return schemes
    
    offset = 0
    while True:
        try:
            url = f"{BASE}?resource_id={resource_id}&limit=100&offset={offset}"
            resp = httpx.get(url, timeout=15, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                break
            data = resp.json()
            records = data.get("records") or []
            if not records:
                break
            for r in records:
                schemes.append(make_scheme({
                    "name": str(r.get("scheme_name") or r.get("title") or ""),
                    "description": str(r.get("description") or ""),
                    "eligibility": str(r.get("eligibility") or ""),
                    "benefits": str(r.get("benefits") or ""),
                    "apply_link": str(r.get("url") or r.get("apply_link") or "https://data.gov.in"),
                    "state": str(r.get("state") or "Central"),
                    "source": "data.gov.in",
                    "category": str(r.get("category") or "General"),
                }))
            offset += 100
            if len(records) < 100:
                break
        except Exception as e:
            logger.error(f"data_gov offset {offset} failed: {e}")
            break
    logger.info(f"data_gov: scraped {len(schemes)} schemes")
    return schemes
