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
import os
import pymongo

_mongo_client = None

def get_schemes_db():
    global _mongo_client
    if not _mongo_client:
        uri = os.getenv("MONGODB_URI")
        if uri:
            _mongo_client = pymongo.MongoClient(uri)
    if _mongo_client:
        return _mongo_client["welfarebot"]["schemes"]
    return None

def smart_retrieve(query, user_state=None):
    """Retrieve scheme information lightning-fast from MongoDB."""
    logger.info(f"smart_retrieve (MongoDB optimized): query={query}")
    try:
        db = get_schemes_db()
        if db is None:
            return [], "none"
            
        import re
        import json
        
        words = [w for w in query.split() if len(w) > 3]
        if not words:
            words = [query]
            
        pattern = "|".join([re.escape(w) for w in words])
        
        results = db.find({
            "$or": [
                {"name": {"$regex": pattern, "$options": "i"}},
                {"description": {"$regex": pattern, "$options": "i"}},
                {"benefits": {"$regex": pattern, "$options": "i"}}
            ]
        }).limit(3)
        
        docs = []
        for doc in results:
            docs.append(json.dumps({
                "name": doc.get("name", ""),
                "description": doc.get("description", ""),
                "benefits": doc.get("benefits", ""),
                "eligibility": doc.get("eligibility", ""),
                "application_process": doc.get("application_process", ""),
                "apply_link": doc.get("application_link", "")
            }))
            
        if docs:
            return docs, "mongo"
            
    except Exception as e:
        logger.error(f"mongo_retrieve error: {e}")
        
    return [], "none"
