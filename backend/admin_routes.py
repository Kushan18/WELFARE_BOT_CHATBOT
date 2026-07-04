from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from bson import ObjectId

# Import shared dependencies from main
from typing import Optional
from main import sync_mongo_client, verify_admin_key

router = APIRouter()

# Mongo collections
raw_schemes = sync_mongo_client["welfarebot"]["raw_schemes"]
new_schemes = sync_mongo_client["welfarebot"]["new_schemes"]
official_schemes = sync_mongo_client["welfarebot"]["schemes"]
deleted_schemes = sync_mongo_client["welfarebot"]["deleted_schemes"]
audit_logs = sync_mongo_client["welfarebot"]["audit_logs"]
feedbacks = sync_mongo_client["welfarebot"]["feedbacks"]

def log_audit(admin_id: str, action: str, target_type: str, target_id: str, target_name: str, details: str = ""):
    try:
        audit_logs.insert_one({
            "timestamp": datetime.utcnow(),
            "admin_id": admin_id,
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "target_name": target_name,
            "details": details
        })
    except Exception as e:
        print(f"Failed to write audit log: {e}")


# ---------------------------------------------------------------------------
# Admin Login
# ---------------------------------------------------------------------------
@router.post("/admin/login", dependencies=[Depends(verify_admin_key)])
async def admin_login(admin_key: str = Depends(verify_admin_key)):
    # If it reaches here, the admin_key is verified
    log_audit(
        admin_id=admin_key,
        action="login",
        target_type="system",
        target_id="N/A",
        target_name="Admin Dashboard",
        details="Admin logged in to the dashboard"
    )
    return {"success": True, "message": "Logged in successfully"}

# ---------------------------------------------------------------------------
# Merged listing endpoint (All Schemes)
# ---------------------------------------------------------------------------
@router.get("/admin/raw", dependencies=[Depends(verify_admin_key)])
async def list_raw_schemes(
    skip: int = 0,
    limit: int = 100,
    verified: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None  # "newest" or "oldest"
, admin_key: str = Depends(verify_admin_key)):
    log_audit(
        admin_id=admin_key,
        action="read",
        target_type="schemes",
        target_id="N/A",
        target_name="All Schemes Tab",
        details="Viewed all schemes (raw/new)"
    )

    """Return **raw** and **new** schemes combined.
    The admin UI expects to see both collections under the *All Schemes* tab.
    All filters (verified, date range, search, sort) apply to the combined result set.
    """
    # Build shared query
    base_query: dict = {}
    if verified is not None:
        base_query["verified"] = verified
    if start_date or end_date:
        date_query: dict = {}
        if start_date:
            date_query["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_query["$lte"] = datetime.fromisoformat(end_date)
        base_query["scraped_at"] = date_query
    if search:
        base_query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    sort_order = -1  # newest first by default
    if sort == "oldest":
        sort_order = 1

    # Query both collections
    raw_cursor = raw_schemes.find(base_query).sort("scraped_at", sort_order)
    new_cursor = new_schemes.find(base_query).sort("scraped_at", sort_order)
    raw_items = list(raw_cursor)
    new_items = list(new_cursor)
    # Tag source for UI distinction if needed
    for i in raw_items:
        i["_id"] = str(i.get("_id"))
        i["source"] = "raw"
    for i in new_items:
        i["_id"] = str(i.get("_id"))
        i["source"] = "new"
    combined = raw_items + new_items
    # Apply pagination after merging
    combined = combined[skip : skip + limit]
    return {"raw_schemes": combined, "count": len(combined)}


# ---------------------------------------------------------------------------
# Feedbacks Endpoint
# ---------------------------------------------------------------------------
@router.get("/admin/feedbacks", dependencies=[Depends(verify_admin_key)])
async def get_feedbacks(skip: int = 0, limit: int = 50, admin_key: str = Depends(verify_admin_key)):
    log_audit(
        admin_id=admin_key,
        action="read",
        target_type="feedbacks",
        target_id="N/A",
        target_name="Feedbacks Tab",
        details="Viewed feedbacks"
    )
    cursor = feedbacks.find().sort("timestamp", -1)
    results = list(cursor[skip : skip + limit])
    for f in results:
        f["_id"] = str(f["_id"])
    count = feedbacks.count_documents({})
    return {"feedbacks": results, "count": count}


# ---------------------------------------------------------------------------
# Audit Logs Endpoint
# ---------------------------------------------------------------------------
@router.get("/admin/audit_logs", dependencies=[Depends(verify_admin_key)])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    search: Optional[str] = None
):
    query = {}
    if action:
        query["action"] = action
    if target_type:
        query["target_type"] = target_type
    
    if from_date or to_date:
        date_query = {}
        if from_date:
            date_query["$gte"] = datetime.fromisoformat(from_date)
        if to_date:
            try:
                # If to_date is just YYYY-MM-DD, we want to include the whole day
                parsed_to = datetime.fromisoformat(to_date)
                if len(to_date) <= 10:
                    parsed_to = parsed_to.replace(hour=23, minute=59, second=59)
                date_query["$lte"] = parsed_to
            except Exception:
                pass
        if date_query:
            query["timestamp"] = date_query
            
    if search:
        search_words = search.strip().split()
        if search_words:
            query["$and"] = [
                {"$or": [
                    {"admin_id": {"$regex": word, "$options": "i"}},
                    {"target_name": {"$regex": word, "$options": "i"}},
                    {"details": {"$regex": word, "$options": "i"}}
                ]} for word in search_words
            ]
            
    cursor = audit_logs.find(query).sort("timestamp", -1)
    logs = list(cursor[skip : skip + limit])
    for log in logs:
        log["_id"] = str(log["_id"])
        
    total_count = audit_logs.count_documents(query)
    return {"audit_logs": logs, "count": total_count}

# ---------------------------------------------------------------------------
# Raw scheme actions
# ---------------------------------------------------------------------------
@router.post("/admin/raw/{scheme_id}/verify", dependencies=[Depends(verify_admin_key)])
async def verify_raw_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    scheme = raw_schemes.find_one({"_id": ObjectId(scheme_id)})
    if not scheme:
        raise HTTPException(status_code=404, detail="Raw scheme not found")
    
    # Copy to official schemes
    scheme.pop("_id", None)
    scheme["verified"] = True
    scheme["verified_at"] = datetime.utcnow()
    official_schemes.insert_one(scheme)
    
    # Update raw scheme status by deleting it (move complete)
    raw_schemes.delete_one({"_id": ObjectId(scheme_id)})
    target_name = scheme.get("name", "Unknown Scheme") if "scheme" in locals() and scheme else "Unknown Scheme"
    log_audit(admin_key, "verify", "scheme", scheme_id, target_name, "verified raw scheme")
    return {"status": "success", "message": "Scheme verified and moved to official"}

@router.post("/admin/raw/{scheme_id}/reject", dependencies=[Depends(verify_admin_key)])
async def reject_raw_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    result = raw_schemes.update_one({"_id": ObjectId(scheme_id)}, {"$set": {"verified": False, "rejected": True, "rejected_at": datetime.utcnow()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Raw scheme not found")
    target_name = "Unknown Scheme"
    log_audit(admin_key, "reject", "scheme", scheme_id, target_name, "rejected raw scheme")
    return {"status": "success", "message": "Scheme marked as unverified"}

@router.delete("/admin/raw/{scheme_id}", dependencies=[Depends(verify_admin_key)])
async def delete_raw_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    scheme = raw_schemes.find_one({"_id": ObjectId(scheme_id)})
    if not scheme:
        raise HTTPException(status_code=404, detail="Raw scheme not found")
    scheme["source"] = "raw"
    deleted_schemes.insert_one(scheme)
    raw_schemes.delete_one({"_id": ObjectId(scheme_id)})
    target_name = scheme.get("name", "Unknown Scheme") if "scheme" in locals() and scheme else "Unknown Scheme"
    log_audit(admin_key, "delete", "scheme", scheme_id, target_name, "deleted raw scheme")
    return {"status": "success", "message": "Raw scheme moved to deleted"}

# ---------------------------------------------------------------------------
# New scheme actions (CRUD)
# ---------------------------------------------------------------------------
@router.put("/admin/new/{scheme_id}", dependencies=[Depends(verify_admin_key)])
async def edit_new_scheme(scheme_id: str, updates: dict, admin_key: str = Depends(verify_admin_key)):
    result = new_schemes.update_one({"_id": ObjectId(scheme_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="New scheme not found")
    target_name = "Unknown Scheme"
    log_audit(admin_key, "edit", "scheme", scheme_id, target_name, f"updated fields: {list(updates.keys())}")
    return {"status": "success", "message": "New scheme updated"}

@router.post("/admin/new/{scheme_id}/verify", dependencies=[Depends(verify_admin_key)])
async def verify_new_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    scheme = new_schemes.find_one({"_id": ObjectId(scheme_id)})
    if not scheme:
        raise HTTPException(status_code=404, detail="New scheme not found")
    
    scheme.pop("_id", None)
    scheme["verified"] = True
    scheme["verified_at"] = datetime.utcnow()
    official_schemes.insert_one(scheme)
    
    new_schemes.delete_one({"_id": ObjectId(scheme_id)})
    target_name = scheme.get("name", "Unknown Scheme") if "scheme" in locals() and scheme else "Unknown Scheme"
    log_audit(admin_key, "verify", "scheme", scheme_id, target_name, "verified new scheme")
    return {"status": "success", "message": "New scheme verified and moved to official"}

@router.post("/admin/new/{scheme_id}/reject", dependencies=[Depends(verify_admin_key)])
async def reject_new_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    result = new_schemes.update_one({"_id": ObjectId(scheme_id)}, {"$set": {"verified": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="New scheme not found")
    target_name = "Unknown Scheme"
    log_audit(admin_key, "reject", "scheme", scheme_id, target_name, "rejected new scheme")
    return {"status": "success", "message": "New scheme marked as unverified"}

@router.delete("/admin/new/{scheme_id}", dependencies=[Depends(verify_admin_key)])
async def delete_new_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    scheme = new_schemes.find_one({"_id": ObjectId(scheme_id)})
    if not scheme:
        raise HTTPException(status_code=404, detail="New scheme not found")
    scheme["source"] = "new"
    deleted_schemes.insert_one(scheme)
    new_schemes.delete_one({"_id": ObjectId(scheme_id)})
    target_name = scheme.get("name", "Unknown Scheme") if "scheme" in locals() and scheme else "Unknown Scheme"
    log_audit(admin_key, "delete", "scheme", scheme_id, target_name, "deleted new scheme")
    return {"status": "success", "message": "New scheme moved to deleted"}

# ---------------------------------------------------------------------------
# Existing admin routes (users, conversations, analytics, etc.)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# New combined All Schemes endpoint (official + raw + new)
# ---------------------------------------------------------------------------
@router.get("/admin/all_schemes", dependencies=[Depends(verify_admin_key)])
def list_all_schemes(
    skip: int = 0,
    limit: int = 1000,
    verified: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None  # "newest" or "oldest"
):
    """Return combined list of official, raw, and new schemes with pagination and filters."""

    # Build shared query for raw and new schemes
    base_query: dict = {}
    if verified is not None:
        if verified is True:
            base_query["verified"] = True
        else:
            base_query["$or"] = [{"verified": False}, {"verified": {"$exists": False}}]
    
    if start_date or end_date:
        pass # Ignore date filters for now to avoid hiding items without scraped_at
        
    if search:
        search_or = {
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"state": {"$regex": search, "$options": "i"}},
            ]
        }
        if "$or" in base_query:
            base_query = {"$and": [base_query, search_or]}
        else:
            base_query.update(search_or)
    sort_order = -1 if sort != "oldest" else 1

    # Official schemes (respect verified and search filters, but skip date filters)
    official_query: dict = {}
    if verified is not None:
        if verified is True:
            official_query["verified"] = True
        else:
            official_query["$or"] = [{"verified": False}, {"verified": {"$exists": False}}]

    if search:
        search_or = {
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"state": {"$regex": search, "$options": "i"}},
            ]
        }
        if "$or" in official_query:
            official_query = {"$and": [official_query, search_or]}
        else:
            official_query.update(search_or)

    official_items = []
    for doc in official_schemes.find(official_query):
        doc["_id"] = str(doc.get("_id"))
        doc["source"] = "official"
        # Preserve existing scraped_at if present, otherwise None for sorting
        doc["scraped_at"] = doc.get("scraped_at")
        official_items.append(doc)
    # Apply same sort order as raw/new schemes (by scraped_at, falling back to _id)
    official_items.sort(key=lambda x: (x.get("scraped_at") or datetime.min), reverse=(sort_order == -1))

    # Raw and new schemes with filters
    raw_items = list(raw_schemes.find(base_query).sort("scraped_at", sort_order))
    new_items = list(new_schemes.find(base_query).sort("scraped_at", sort_order))

    for i in official_items:
        i["_id"] = str(i.get("_id"))
        i["source"] = "official"
    for i in raw_items:
        i["_id"] = str(i.get("_id"))
        i["source"] = "raw"
    for i in new_items:
        i["_id"] = str(i.get("_id"))
        i["source"] = "new"

    combined = official_items + raw_items + new_items
    total_count = len(combined)
    combined = combined[skip : skip + limit]
    return {"all_schemes": combined, "count": total_count}


# ---------------------------------------------------------------------------
# Raw Scheme edit endpoint (allows admin to modify fields)
# ---------------------------------------------------------------------------
@router.put("/admin/raw/{scheme_id}", dependencies=[Depends(verify_admin_key)])
async def edit_raw_scheme(scheme_id: str, updates: dict, admin_key: str = Depends(verify_admin_key)):
    result = raw_schemes.update_one({"_id": ObjectId(scheme_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Raw scheme not found")
    target_name = "Unknown Scheme"
    log_audit(admin_key, "edit", "scheme", scheme_id, target_name, f"updated fields: {list(updates.keys())}")
    return {"status": "success", "message": "Raw scheme updated"}

# ---------------------------------------------------------------------------
# Official Scheme edit endpoint (admin can edit official schemes)
# ---------------------------------------------------------------------------
# Removed duplicate official get route; unified get_scheme below

@router.put("/admin/schemes/{scheme_id}", dependencies=[Depends(verify_admin_key)])
async def edit_official_scheme(scheme_id: str, updates: dict, admin_key: str = Depends(verify_admin_key)):
    result = official_schemes.update_one({"_id": ObjectId(scheme_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Scheme not found")
    target_name = "Unknown Scheme"
    log_audit(admin_key, "edit", "scheme", scheme_id, target_name, f"updated fields: {list(updates.keys())}")
    return {"status": "success", "message": "Scheme updated"}
@router.get("/admin/schemes/{scheme_id}", dependencies=[Depends(verify_admin_key)])
async def get_scheme(scheme_id: str):
    # Search across official, raw, and new collections
    for coll, src in ((official_schemes, "official"), (raw_schemes, "raw"), (new_schemes, "new")):
        doc = coll.find_one({"_id": ObjectId(scheme_id)})
        if doc:
            doc["_id"] = str(doc.get("_id"))
            doc["source"] = src
            return {"success": True, "data": doc}
    raise HTTPException(status_code=404, detail="Scheme not found")
# The rest of the file (users, analytics, etc.) remains unchanged and is imported

# ---------------------------------------------------------------------------
# Official Scheme delete and restore endpoints
# ---------------------------------------------------------------------------
@router.delete("/admin/schemes/{scheme_id}", dependencies=[Depends(verify_admin_key)])
async def delete_official_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    scheme = official_schemes.find_one({"_id": ObjectId(scheme_id)})
    if not scheme:
        raise HTTPException(status_code=404, detail="Official scheme not found")
    # Tag source for restoration
    scheme["source"] = "official"
    # Move to deleted collection
    deleted_schemes.insert_one(scheme)
    # Delete from official collection
    official_schemes.delete_one({"_id": ObjectId(scheme_id)})
    target_name = scheme.get("name", "Unknown Scheme") if "scheme" in locals() and scheme else "Unknown Scheme"
    log_audit(admin_key, "delete", "scheme", scheme_id, target_name, "deleted official scheme")
    return {"status": "success", "message": "Scheme moved to deleted"}

@router.post("/admin/deleted/{scheme_id}/restore", dependencies=[Depends(verify_admin_key)])
async def restore_deleted_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    doc = deleted_schemes.find_one({"_id": ObjectId(scheme_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Deleted scheme not found")
    source = doc.get("source")
    # Remove source metadata before reinserting
    doc.pop("source", None)
    if source == "official":
        official_schemes.insert_one(doc)
    elif source == "raw":
        raw_schemes.insert_one(doc)
    elif source == "new":
        new_schemes.insert_one(doc)
    else:
        # Fallback to official if unknown source
        official_schemes.insert_one(doc)
    # Remove from deleted collection
    deleted_schemes.delete_one({"_id": ObjectId(scheme_id)})
    target_name = doc.get("name", "Unknown Scheme") if "doc" in locals() and doc else "Unknown Scheme"
    log_audit(admin_key, "restore", "scheme", scheme_id, target_name, "restored scheme")
    return {"status": "success", "message": "Scheme restored"}

@router.delete("/admin/deleted/{scheme_id}/hard", dependencies=[Depends(verify_admin_key)])
async def hard_delete_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    doc = deleted_schemes.find_one({"_id": ObjectId(scheme_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Deleted scheme not found")
    
    deleted_schemes.delete_one({"_id": ObjectId(scheme_id)})
    target_name = doc.get("name", "Unknown Scheme")
    log_audit(
        admin_id=admin_key,
        action="delete",
        target_type="scheme",
        target_id=scheme_id,
        target_name=target_name,
        details="permanently deleted scheme"
    )
    return {"status": "success", "message": "Scheme permanently deleted"}

@router.post("/admin/schemes/bulk_delete", dependencies=[Depends(verify_admin_key)])
async def bulk_delete_schemes(items: list, admin_key: str = Depends(verify_admin_key)):
    # items should be a list of {"id": "str", "source": "str"}
    deleted_count = 0
    for item in items:
        scheme_id = item.get("id")
        source = item.get("source", "official")
        try:
            doc = None
            if source == "raw":
                doc = raw_schemes.find_one({"_id": ObjectId(scheme_id)})
                if doc:
                    doc["source"] = "raw"
                    raw_schemes.delete_one({"_id": ObjectId(scheme_id)})
            elif source == "new":
                doc = new_schemes.find_one({"_id": ObjectId(scheme_id)})
                if doc:
                    doc["source"] = "new"
                    new_schemes.delete_one({"_id": ObjectId(scheme_id)})
            else:
                doc = official_schemes.find_one({"_id": ObjectId(scheme_id)})
                if doc:
                    doc["source"] = "official"
                    official_schemes.delete_one({"_id": ObjectId(scheme_id)})
                    
            if doc:
                doc["deleted_at"] = datetime.utcnow()
                deleted_schemes.insert_one(doc)
                deleted_count += 1
                log_audit(admin_key, "delete", "scheme", scheme_id, doc.get("name", "Unknown Scheme"), "bulk deleted scheme")
        except Exception:
            continue
    return {"status": "success", "message": f"{deleted_count} schemes deleted successfully."}

@router.post("/admin/deleted/bulk_hard_delete", dependencies=[Depends(verify_admin_key)])
async def bulk_hard_delete_schemes(items: list, admin_key: str = Depends(verify_admin_key)):
    # items should be a list of strings (ids)
    deleted_count = 0
    for scheme_id in items:
        try:
            doc = deleted_schemes.find_one({"_id": ObjectId(scheme_id)})
            if doc:
                deleted_schemes.delete_one({"_id": ObjectId(scheme_id)})
                deleted_count += 1
                log_audit(admin_key, "delete", "scheme", scheme_id, doc.get("name", "Unknown Scheme"), "bulk permanently deleted scheme")
        except Exception:
            continue
    return {"status": "success", "message": f"{deleted_count} schemes permanently deleted."}

# The rest of the file (users, analytics, etc.) remains unchanged and is imported

# ---------------------------------------------------------------------------
# Deleted schemes listing endpoint (with filters)
# ---------------------------------------------------------------------------
@router.get("/admin/deleted", dependencies=[Depends(verify_admin_key)])
def list_deleted_schemes(
    skip: int = 0,
    limit: int = 100,
    verified: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None  # "newest" or "oldest"
):
    """Return list of deleted schemes with optional filters"""
    base_query: dict = {}
    if verified is not None:
        base_query["verified"] = verified
    if start_date or end_date:
        pass # Ignore date filters for deleted items as they may not have scraped_at
    if search:
        base_query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    sort_order = -1 if sort != "oldest" else 1
    cursor = deleted_schemes.find(base_query).sort("scraped_at", sort_order)
    items = list(cursor)[skip : skip + limit]
    for i in items:
        i["_id"] = str(i.get("_id"))
    return {"deleted_schemes": items, "count": len(items)}

# ------------------------------------------------------------
# Scraped schemes statistics endpoint
# ------------------------------------------------------------
@router.get("/admin/scraped", dependencies=[Depends(verify_admin_key)])
def get_scraped_stats():
    """
    Return statistics about scraped schemes.
    """
    verified_official = official_schemes.count_documents({"verified": True})
    verified_raw = raw_schemes.count_documents({"verified": True})
    verified_new = new_schemes.count_documents({"verified": True})
    verified = verified_official + verified_raw + verified_new
    
    unverified_official = official_schemes.count_documents({"verified": {"$ne": True}})
    unverified_raw = raw_schemes.count_documents({"verified": {"$ne": True}})
    unverified_new = new_schemes.count_documents({"verified": {"$ne": True}})
    unverified = unverified_official + unverified_raw + unverified_new
    
    total = verified + unverified
    
    recent_cursor = raw_schemes.find().sort("scraped_at", -1).limit(5)
    recent = []
    for s in recent_cursor:
        s["_id"] = str(s.get("_id"))
        recent.append(s)
    return {"total": total, "verified": verified, "unverified": unverified, "recent": recent}

# ------------------------------------------------------------
# Clear scraped data endpoint (admin)
# ------------------------------------------------------------
@router.post("/admin/clear_scraped", dependencies=[Depends(verify_admin_key)])
async def clear_scraped_data():
    raw_deleted = raw_schemes.delete_many({})
    new_deleted = new_schemes.delete_many({})
    return {"success": True, "message": f"Cleared {raw_deleted.deleted_count} raw and {new_deleted.deleted_count} new schemes"}

# ------------------------------------------------------------
# New schemes listing endpoint
# ------------------------------------------------------------
@router.get("/admin/new", dependencies=[Depends(verify_admin_key)])
def list_new_schemes(
    skip: int = 0,
    limit: int = 100,
    verified: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None  # "newest" or "oldest"
):
    """Return new/unverified schemes with optional filters across all collections."""
    base_query: dict = {}
    
    # If no verified filter is specified, only fetch unverified schemes
    if verified is not None:
        base_query["verified"] = verified
    else:
        base_query["verified"] = {"$ne": True}
        
    if start_date or end_date:
        date_query: dict = {}
        if start_date:
            date_query["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_query["$lte"] = datetime.fromisoformat(end_date)
        base_query["scraped_at"] = date_query
        
    if search:
        base_query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"state": {"$regex": search, "$options": "i"}},
        ]
        
    sort_order = -1 if sort != "oldest" else 1
    
    # Query official schemes (excluding date filters to not hide manually added unverified schemes)
    official_query = dict(base_query)
    if "scraped_at" in official_query:
        del official_query["scraped_at"]
        
    official_items = []
    for doc in official_schemes.find(official_query):
        doc["_id"] = str(doc.get("_id"))
        doc["source"] = "official"
        doc["scraped_at"] = doc.get("scraped_at")
        official_items.append(doc)
        
    official_items.sort(key=lambda x: (x.get("scraped_at") or datetime.min), reverse=(sort_order == -1))
    
    # Query raw and new collections
    raw_items = list(raw_schemes.find(base_query).sort("scraped_at", sort_order))
    new_items = list(new_schemes.find(base_query).sort("scraped_at", sort_order))
    
    for i in raw_items:
        i["_id"] = str(i.get("_id"))
        i["source"] = "raw"
    for i in new_items:
        i["_id"] = str(i.get("_id"))
        i["source"] = "new"
        
    combined = official_items + raw_items + new_items
    total_count = len(combined)
    combined = combined[skip : skip + limit]
    
    return {"new_schemes": combined, "count": total_count}

# The rest of the file (users, analytics, etc.) remains unchanged and is imported
# from the original implementation further down in this module.
