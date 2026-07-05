from db_utils import get_mongo_client
import logging
import re
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def _clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()

def compute_quality_score(scheme: dict) -> int:
    score = 0
    if scheme.get("description") and len(scheme["description"].strip()) >= 40:
        score += 30
    if scheme.get("eligibility") and scheme["eligibility"].strip():
        score += 25
    if scheme.get("apply_link") and scheme["apply_link"].strip():
        score += 25
    if scheme.get("deadline") and scheme["deadline"].strip():
        score += 20
    return score



def run_scraper():
    import uuid
    from datetime import datetime
    from pymongo import ReturnDocument
    from scraper import ts_official, ts_vikaspedia, ap_official, ap_vikaspedia, data_gov, pmindia, vikaspedia_central, myscheme, hf_dataset, schemesinindia, nsp, dbtbharat, india_gov, schemes_vikaspedia
    
    started_at = datetime.utcnow()
    run_id = str(uuid.uuid4())
    status = "success"
    error_message = None
    
    client = get_mongo_client(os.getenv("MONGODB_URI"))
    db = client["welfarebot"]
    staging = db["staging"]
    raw_schemes = db["raw_schemes"]
    scrape_runs = db["scrape_runs"]
    
    # Ensure unique index on apply_link + normalized name for duplicate prevention
    raw_schemes.create_index([("apply_link", 1), ("name_norm", 1)], unique=True)
    
    added = 0
    skipped = 0
    sources = [
        ("hf_dataset", hf_dataset.scrape),
        ("myscheme", myscheme.scrape),
        ("ts_official", ts_official.scrape),
        ("ts_vikaspedia", ts_vikaspedia.scrape),
        ("ap_official", ap_official.scrape),
        ("ap_vikaspedia", ap_vikaspedia.scrape),
        ("data_gov", data_gov.scrape),
        ("pmindia", pmindia.scrape),
        ("vikaspedia_central", vikaspedia_central.scrape),
        ("schemesinindia", schemesinindia.scrape),
        ("nsp", nsp.scrape),
        ("dbtbharat", dbtbharat.scrape),
        ("india_gov", india_gov.scrape),
        ("schemes_vikaspedia", schemes_vikaspedia.scrape),
    ]
    
    # Collect all schemes
    all_schemes = []
    for name, fn in sources:
        try:
            schemes = fn()
            logger.info(f"{name}: got {len(schemes)} schemes")
            all_schemes.extend(schemes)
        except Exception as e:
            logger.error(f"{name} failed: {e}")
            status = "partial"
            if not error_message:
                error_message = f"{name} failed: {str(e)}"
            else:
                error_message += f" | {name} failed: {str(e)}"

    # Add source field to all schemes missing it
    for scheme in all_schemes:
        if not scheme.get('source') or scheme['source'] == '':
            scheme['source'] = scheme.get('state', 'unknown').lower().replace(' ', '') + '.gov.in'

    # Deduplicate by normalized name in current batch
    seen = set()
    deduped = []
    for s in all_schemes:
        norm = _clean_name(s.get("name", ""))
        if norm in seen:
            continue
        seen.add(norm)
        deduped.append(s)
        
    new_count = 0
    auto_verified_count = 0
    pending_count = 0
    run_scheme_ids = []

    from scripts.enrich_raw import _enrich_document
    REQUIRED_FIELDS = ['name', 'description', 'apply_link', 'state', 'gender', 'caste_category', 'max_income']

    def _has_all_required_fields(doc: dict) -> bool:
        return all(doc.get(f) for f in REQUIRED_FIELDS)

    official_schemes = db["schemes"]

    # Process each scheme
    for raw in deduped:
        try:
            apply_link = raw.get("apply_link")
            name_norm = _clean_name(raw.get("name", ""))

            # 1. Global Deduplication
            existing_live = None
            existing_raw = None
            if apply_link:
                existing_live = official_schemes.find_one({"apply_link": apply_link})
                existing_raw = raw_schemes.find_one({"apply_link": apply_link})
            if not existing_live and not existing_raw:
                existing_live = official_schemes.find_one({"name_norm": name_norm})
                existing_raw = raw_schemes.find_one({"name_norm": name_norm})
                
            if existing_live or existing_raw:
                continue # Reject duplicate directly
                
            new_count += 1
            raw_clean = {k: v for k, v in raw.items() if k not in ("_id", "scraped_at", "last_updated")}
            raw_clean["name_norm"] = name_norm
            raw_clean["scraped_at"] = datetime.utcnow()
            
            # 2. Immediate Completeness Check
            if _has_all_required_fields(raw_clean):
                raw_clean["verified"] = True
                raw_clean["verified_at"] = datetime.utcnow()
                inserted = official_schemes.insert_one(raw_clean)
                run_scheme_ids.append(str(inserted.inserted_id))
                auto_verified_count += 1
            else:
                # 3. NLP Enrichment Fallback
                raw_clean = _enrich_document(raw_clean)
                
                # 4. Post-Enrichment Verification
                if _has_all_required_fields(raw_clean):
                    raw_clean["verified"] = True
                    raw_clean["verified_at"] = datetime.utcnow()
                    inserted = official_schemes.insert_one(raw_clean)
                    run_scheme_ids.append(str(inserted.inserted_id))
                    auto_verified_count += 1
                else:
                    raw_clean["verified"] = False
                    inserted = raw_schemes.insert_one(raw_clean)
                    run_scheme_ids.append(str(inserted.inserted_id))
                    pending_count += 1
                    
        except Exception as e:
            logger.error(f"Failed to process scheme {raw.get('apply_link', 'unknown')}: {e}")
            
    logger.info(f"Scraper Run complete. New: {new_count}, Verified: {auto_verified_count}, Pending: {pending_count}")
    
    # Save Scraper Run History
    finished_at = datetime.utcnow()
    try:
        run_record = {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "total_found": len(deduped),
            "new_count": new_count,
            "auto_verified_count": auto_verified_count,
            "pending_count": pending_count,
            "scheme_ids": run_scheme_ids,
            "error_message": error_message
        }
        scrape_runs.insert_one(run_record)
        logger.info(f"Saved run {run_id} to scrape_runs collection.")
    except Exception as e:
        logger.error(f"Failed to save scraper run history: {e}")
        
    client.close()