from db_utils import get_mongo_client
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from fastapi.testclient import TestClient
from main import app

client = get_mongo_client(os.getenv("MONGODB_URI"))
_db = client["welfarebot"]
raw_coll = _db["raw_schemes"]
schemes_coll = _db["schemes"]

client_app = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup():
    dummy = {"name": "Test Scheme", "apply_link": "http://example.com", "state": "", "caste_category": "", "max_income": None, "verified": False}
    inserted = raw_coll.insert_one(dummy)
    dummy_id = str(inserted.inserted_id)
    yield dummy_id
    raw_coll.delete_many({"_id": inserted.inserted_id})
    schemes_coll.delete_many({"name": "Test Scheme"})

def test_list_raw_schemes(cleanup):
    response = client_app.get("/admin/raw", headers={"X-Admin-API-Key": os.getenv("ADMIN_API_KEY", "admin-secret-key-123")})
    assert response.status_code == 200
    data = response.json()
    assert any(item["name"] == "Test Scheme" for item in data["raw_schemes"])

def test_edit_raw_scheme(cleanup):
    scheme_id = cleanup
    new_name = "Edited Scheme"
    response = client_app.put(f"/admin/raw/{scheme_id}", json={"name": new_name}, headers={"X-Admin-API-Key": os.getenv("ADMIN_API_KEY", "admin-secret-key-123")})
    assert response.status_code == 200
    edited = raw_coll.find_one({"_id": raw_coll.find_one({"name": new_name})["_id"]})
    assert edited["name"] == new_name

def test_verify_scheme(cleanup):
    scheme_id = cleanup
    response = client_app.post(f"/admin/raw/{scheme_id}/verify", headers={"X-Admin-API-Key": os.getenv("ADMIN_API_KEY", "admin-secret-key-123")})
    assert response.status_code == 200
    raw_doc = raw_coll.find_one({"_id": raw_coll.find_one({"name": "Test Scheme"})["_id"]})
    assert raw_doc["verified"] is True
    assert "verified_at" in raw_doc
    live = schemes_coll.find_one({"name": "Test Scheme"})
    assert live is not None
    assert live.get("verified") is True

def test_reject_scheme(cleanup):
    scheme_id = cleanup
    response = client_app.post(f"/admin/raw/{scheme_id}/reject", headers={"X-Admin-API-Key": os.getenv("ADMIN_API_KEY", "admin-secret-key-123")})
    assert response.status_code == 200
    raw_doc = raw_coll.find_one({"_id": raw_coll.find_one({"name": "Test Scheme"})["_id"]})
    assert raw_doc.get("rejected") is True
