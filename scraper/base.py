import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any
from datetime import datetime
import uuid

def fetch_html(url: str) -> BeautifulSoup:
    """Fetch a URL and return a BeautifulSoup object."""
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def make_scheme(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw scraped data into the required schema.

    Required keys: name, description, eligibility, benefits, apply_link, state,
    category, source, status, scraped_at.
    """
    scheme = {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "eligibility": data.get("eligibility", ""),
        "benefits": data.get("benefits", ""),
        "apply_link": data.get("apply_link", ""),
        "state": data.get("state", ""),
        "category": data.get("category", ""),
        "source": data.get("source", ""),
        "status": "pending",
        "scraped_at": datetime.utcnow().isoformat() + "Z",
    }
    # Ensure a unique identifier for internal use (not part of the required schema)
    scheme["_id"] = str(uuid.uuid4())
    return scheme
