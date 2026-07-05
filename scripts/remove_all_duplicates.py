from db_utils import get_mongo_client
import os
import re
from dotenv import load_dotenv

def _clean_name(name: str) -> str:
    if not name: return ""
    return re.sub(r"\s+", " ", name.strip()).lower()

def run_dedup():
    load_dotenv()
    client = get_mongo_client(os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"))
    db = client["welfarebot"]
    
    seen_names = set()
    total_deleted = 0
    
    # 1. Official Schemes (Highest Priority)
    print("Processing official schemes...")
    schemes = list(db["schemes"].find({}))
    for doc in schemes:
        name_norm = _clean_name(doc.get("name"))
        if name_norm in seen_names:
            db["schemes"].delete_one({"_id": doc["_id"]})
            total_deleted += 1
            print(f"Deleted duplicate from schemes: {doc.get('name')}")
        else:
            if name_norm: seen_names.add(name_norm)
            
    # 2. New Schemes (Medium Priority)
    print("Processing new schemes...")
    new_schemes = list(db["new_schemes"].find({}))
    for doc in new_schemes:
        name_norm = _clean_name(doc.get("name"))
        if name_norm in seen_names:
            db["new_schemes"].delete_one({"_id": doc["_id"]})
            total_deleted += 1
            print(f"Deleted duplicate from new_schemes: {doc.get('name')}")
        else:
            if name_norm: seen_names.add(name_norm)
            
    # 3. Raw Schemes (Lowest Priority)
    print("Processing raw schemes...")
    raw_schemes = list(db["raw_schemes"].find({}))
    for doc in raw_schemes:
        name_norm = _clean_name(doc.get("name"))
        if name_norm in seen_names:
            db["raw_schemes"].delete_one({"_id": doc["_id"]})
            total_deleted += 1
            print(f"Deleted duplicate from raw_schemes: {doc.get('name')}")
        else:
            if name_norm: seen_names.add(name_norm)
            
    # Also clear staging since it's legacy and causes duplicates
    staging_count = db["staging"].count_documents({})
    if staging_count > 0:
        db["staging"].delete_many({})
        print(f"Cleared {staging_count} documents from legacy 'staging' collection.")

    print(f"\nDone! Removed {total_deleted} duplicate schemes across active collections.")

if __name__ == "__main__":
    run_dedup()
