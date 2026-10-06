import os, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["ADMIN_KEY"] = "k"
from fastapi.testclient import TestClient
from app import app

c = TestClient(app)

def test_sample_data_loaded():
    assert len(c.get("/properties").json()) == 6

def test_filters():
    cheap = c.get("/properties", params={"max_rent": 5000}).json()
    assert all(p["rent"] <= 5000 for p in cheap)
    girls = c.get("/properties", params={"girls_only": True, "verified_only": True}).json()
    assert girls and all(p["girls_only"] and p["verified"] for p in girls)

def test_verify_needs_admin_key():
    pid = c.post("/properties", json={"owner": "O", "title": "T", "area": "A", "rent": 1, "deposit": 1, "distance_km": 1}).json()["id"]
    assert c.post(f"/properties/{pid}/verify").status_code == 403
    assert c.post(f"/properties/{pid}/verify", headers={"x-admin-key": "k"}).json()["verified"] is True

def test_booking_and_escrow():
    b = c.post("/bookings", json={"property_id": 1, "student": "Asha"}).json()
    assert b["escrow"] == "HELD" and "Agreement" in b["agreement"]
    assert c.post(f"/bookings/{b['id']}/release").json()["escrow"] == "RELEASED"

def test_safety_complaint_sets_3_day_target():
    b = c.post("/bookings", json={"property_id": 1, "student": "Asha"}).json()
    r = c.post("/complaints", json={"booking_id": b["id"], "kind": "safety", "details": "x"}).json()
    assert r["room_change_by"] is not None

def test_review_rating():
    assert c.post("/reviews", json={"property_id": 1, "rating": 9}).status_code == 422
    c.post("/reviews", json={"property_id": 1, "rating": 5})
    assert [p for p in c.get("/properties").json() if p["id"] == 1][0]["avg_rating"] == 5
