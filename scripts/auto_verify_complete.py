from db_utils import get_mongo_client
import os
from datetime import datetime
from dotenv import load_dotenv

# Load env vars
load_dotenv()
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://127.0.0.1:27017')
client = get_mongo_client(MONGODB_URI)
_db = client['welfarebot']
raw_schemes = _db['raw_schemes']
schemes = _db['schemes']

REQUIRED_FIELDS = ['name', 'description', 'apply_link', 'state', 'caste_category', 'max_income']

def _has_all_required_fields(doc: dict) -> bool:
    return all(doc.get(f) for f in REQUIRED_FIELDS)

def _copy_to_live(raw_doc: dict):
    live_doc = raw_doc.copy()
    live_doc.pop('_id', None)
    live_doc['verified_at'] = datetime.utcnow()
    live_doc['verified'] = True
    # Higher priority for fully complete schemes
    live_doc['priority_score'] = 2.0
    schemes.insert_one(live_doc)
    return live_doc

def auto_verify_complete():
    """Find raw schemes that already have all required fields and verify them automatically.
    This runs after the scraper (or periodically) so that fully‑populated schemes go straight to the live collection.
    """
    cursor = raw_schemes.find({"verified": {"$ne": True}})
    count = 0
    for doc in cursor:
        if _has_all_required_fields(doc):
            _copy_to_live(doc)
            raw_schemes.update_one({"_id": doc['_id']}, {"$set": {"verified": True, "verified_at": datetime.utcnow()}})
            count += 1
    print(f"Auto-verified {count} fully-complete schemes.")

if __name__ == '__main__':
    auto_verify_complete()
