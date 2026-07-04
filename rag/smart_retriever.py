import logging
from rag.live_retriever import live_retrieve
from rag.cached_retriever import cached_retrieve
from rag.sources import STATE_SOURCE_MAP, ALL_SOURCES

logger = logging.getLogger(__name__)

def detect_state(query, user_state=None):
    if user_state:
        return user_state.lower()
    q = query.lower()
    if "telangana" in q:
        return "telangana"
    if "andhra" in q or "ap" in q:
        return "andhra pradesh"
    if "central" in q or "pm " in q:
        return "central"
    return None

def smart_retrieve(query, user_state=None):
    """Retrieve scheme information.

    1. Try cached retrieval (ChromaDB) for up to 3 matches.
    2. For each cached result that includes an ``apply_link``, fetch fresh content
       via ``live_retrieve``.
    3. If live content is available, return it with source_type "live".
    4. Otherwise fall back to the cached textual result with source_type "cached".
    5. If nothing is found, return empty list and source_type "none".
    """
    state = detect_state(query, user_state)
    logger.info(f"smart_retrieve: state={state}")

    cached = cached_retrieve(query, n=3)
    if cached:
        logger.info(f"smart_retrieve: ChromaDB returned {len(cached)} results")
        # cached is a list of documents (strings). In our embedding pipeline we store JSON‑serialised dicts.
        for doc_str in cached:
            try:
                import json
                doc = json.loads(doc_str)
            except Exception:
                continue
            apply_link = doc.get("apply_link") or doc.get("application_link") or doc.get("official_link")
            scheme_name = doc.get("name", "unknown scheme")
            if apply_link:
                live = live_retrieve(scheme_name, apply_link)
                if live:
                    return live, "live"
        # No live data found – return the raw cached text snippets
        return cached, "cached"

    logger.warning("smart_retrieve: ChromaDB empty, falling back to live")
    urls = STATE_SOURCE_MAP.get(state, ALL_SOURCES)
    for url in urls:
        live = live_retrieve(query, url)
        if live:
            return live, "live"
    return [], "none"
