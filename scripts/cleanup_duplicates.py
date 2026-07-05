from db_utils import get_mongo_client
import os
import re
from dotenv import load_dotenv

def _clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()

def cleanup_duplicates():
    load_dotenv()
    client = get_mongo_client(os.getenv("MONGODB_URI"))
    db = client["welfarebot"]
    
    schemes_coll = db["schemes"]
    staging_coll = db["staging"]
    
    # 1. Load existing identifiers from 'schemes' (live) collection
    existing_links = set()
    existing_names_norm = set()
    
    print("Loading verified schemes...")
    for doc in schemes_coll.find({}, {"apply_link": 1, "name": 1}):
        link = doc.get("apply_link")
        if link and isinstance(link, str) and link.strip():
            existing_links.add(link.strip())
        name = doc.get("name")
        if name and isinstance(name, str):
            existing_names_norm.add(_clean_name(name))
            
    print(f"Found {len(existing_links)} unique links and {len(existing_names_norm)} unique names in live schemes.")
    
    # 2. Iterate through 'staging' and remove duplicates
    print("Checking staging collection for duplicates...")
    staging_docs = list(staging_coll.find({}))
    
    duplicates_removed = 0
    kept = 0
    
    for doc in staging_docs:
        doc_id = doc["_id"]
        link = doc.get("apply_link")
        if link and isinstance(link, str):
            link = link.strip()
        else:
            link = ""
            
        name = doc.get("name")
        if name and isinstance(name, str):
            name_norm = _clean_name(name)
        else:
            name_norm = ""
            
        is_duplicate = False
        
        if link and link in existing_links:
            is_duplicate = True
            reason = f"Duplicate link: {link}"
        elif name_norm and name_norm in existing_names_norm:
            is_duplicate = True
            reason = f"Duplicate name: {name_norm}"
            
        if is_duplicate:
            staging_coll.delete_one({"_id": doc_id})
            print(f"Removed duplicate staging doc '{str(doc.get('name')).encode('ascii', 'ignore').decode()}': {reason.encode('ascii', 'ignore').decode()}")
            duplicates_removed += 1
        else:
            # Add to seen sets to remove duplicates WITHIN staging itself
            if link:
                existing_links.add(link)
            if name_norm:
                existing_names_norm.add(name_norm)
            kept += 1
            
    print(f"Cleanup complete! Removed {duplicates_removed} duplicates. {kept} genuinely new schemes remain in staging.")
    client.close()

if __name__ == "__main__":
    cleanup_duplicates()
