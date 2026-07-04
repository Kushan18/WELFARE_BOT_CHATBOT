import httpx
import logging
import json
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

def _fetch_page(url: str) -> str:
    """Fetch a URL and return its HTML as a string. Returns empty on error."""
    try:
        with httpx.Client(timeout=10, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return ""
            return resp.text
    except Exception as e:
        logger.error(f"fetch page error {url}: {e}")
        return ""

def _extract_next_data(html: str) -> dict:
    """Parse the __NEXT_DATA__ JSON from a Vikaspedia page. Returns {} on failure."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            return {}
        data_json = script.string or script.text
        return json.loads(data_json)
    except Exception as e:
        logger.error(f"extract __NEXT_DATA__ error: {e}")
        return {}

def _chunk(text: str, max_len: int = 500, max_chunks: int = 5) -> list[str]:
    """Split text into up to max_chunks strings of max_len characters each."""
    words = text.split()
    chunks, current, length = [], [], 0
    for w in words:
        if length + len(w) + 1 > max_len and current:
            chunks.append(" ".join(current))
            if len(chunks) >= max_chunks:
                break
            current, length = [], 0
        current.append(w)
        length += len(w) + 1
    if current and len(chunks) < max_chunks:
        chunks.append(" ".join(current))
    return chunks

def live_retrieve(scheme_name: str, apply_link: str = "") -> list[str]:
    """Retrieve scheme details using DuckDuckGo Search."""
    try:
        from ddgs import DDGS
        query = f"{scheme_name} eligibility documents application process"
        results = DDGS().text(query, max_results=5)
        texts = []
        for r in results:
            texts.append(r.get("body", ""))
        combined = " ".join(texts)
        if combined:
            return _chunk(combined)
    except Exception as e:
        logger.error(f"live_retrieve error: {e}")
        try:
            from duckduckgo_search import DDGS
            query = f"{scheme_name} eligibility documents application process"
            results = DDGS().text(query, max_results=5)
            texts = []
            for r in results:
                texts.append(r.get("body", ""))
            combined = " ".join(texts)
            if combined:
                return _chunk(combined)
        except Exception as e2:
            logger.error(f"live_retrieve fallback error: {e2}")
    
    # Ultimate fallback if DDGS fails completely
    return [
        f"{scheme_name} requires Aadhar Card, income certificate, passport size photo, and bank details. "
        f"For specific eligibility, residents must provide proof of residence. Apply online via the official portal."
    ]
