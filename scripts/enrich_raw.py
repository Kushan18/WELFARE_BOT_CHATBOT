import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://127.0.0.1:27017')

client = MongoClient(MONGODB_URI)
_db = client["welfarebot"]
raw_schemes = _db["raw_schemes"]
schemes = _db["schemes"]

def _has_all_required_fields(doc: dict) -> bool:
    # Define required fields for a scheme to be considered complete
    required = ["name", "apply_link", "state", "caste_category", "max_income"]
    return all(doc.get(field) for field in required)

def _copy_to_live(raw_doc: dict):
    live_doc = raw_doc.copy()
    live_doc.pop("_id", None)
    live_doc["verified_at"] = datetime.utcnow()
    live_doc["verified"] = True
    live_doc["priority_score"] = 1.0
    schemes.insert_one(live_doc)
    return live_doc

def _copy_to_new(raw_doc: dict):
    new_doc = raw_doc.copy()
    new_doc.pop("_id", None)
    new_doc["status"] = "pending_approval"
    _db["new_schemes"].insert_one(new_doc)
    return new_doc

def _enrich_document(doc: dict) -> dict:
    # Placeholder enrichment – in a real scenario, you'd call an NLP model.
    # For demo, we simply ensure some fields exist with dummy values if missing.
    if not doc.get("state"):
        doc["state"] = "Telangana"
    if not doc.get("caste_category"):
        doc["caste_category"] = "General"
    if not doc.get("max_income"):
        doc["max_income"] = 250000
    # Mark as enriched
    doc["enriched"] = True
    doc["enriched_at"] = datetime.utcnow()
    return doc

def run_enrichment():
    """Run enrichment on raw schemes that have not been enriched yet.
    This function is intended to be scheduled via APScheduler.
    """
    cursor = raw_schemes.find({"enriched": {"$ne": True}})
    updated = 0
    verified = 0
    for doc in cursor:
        enriched_doc = _enrich_document(doc)
        updated += 1
        
        if _has_all_required_fields(enriched_doc):
            # Auto‑verify and copy to live collection
            _copy_to_live(enriched_doc)
            verified += 1
        else:
            # Move to new_schemes for manual admin verification
            _copy_to_new(enriched_doc)
            
        # Remove from raw_schemes to prevent duplicates
        raw_schemes.delete_one({"_id": doc["_id"]})
        
    print(f"Enrichment run: {updated} documents processed, {verified} auto-verified.")

if __name__ == "__main__":
    run_enrichment()
