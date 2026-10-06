"""The Housey - prototype API. Payments and KYC are MOCKED."""
import json, os, sqlite3
from datetime import date, timedelta
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="The Housey")
HERE = os.path.dirname(os.path.abspath(__file__))

def db():
    c = sqlite3.connect(os.getenv("DB_PATH", "housey.db"))
    c.row_factory = sqlite3.Row
    return c

class Property(BaseModel):
    owner: str
    title: str
    area: str
    rent: int
    deposit: int
    distance_km: float
    girls_only: bool = False
    amenities: str = ""

def add_property(c, p):
    cur = c.execute("INSERT INTO properties(owner,title,area,rent,deposit,distance_km,girls_only,amenities,verified)"
                    " VALUES(?,?,?,?,?,?,?,?,0)",
                    (p["owner"], p["title"], p["area"], p["rent"], p["deposit"], p["distance_km"],
                     int(p.get("girls_only", False)), p.get("amenities", "")))
    return cur.lastrowid

def init():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS properties(id INTEGER PRIMARY KEY, owner TEXT, title TEXT, area TEXT, rent INT,
            deposit INT, distance_km REAL, girls_only INT, amenities TEXT, verified INT);
        CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY, property_id INT, student TEXT, escrow TEXT, agreement TEXT);
        CREATE TABLE IF NOT EXISTS complaints(id INTEGER PRIMARY KEY, booking_id INT, kind TEXT, details TEXT,
            status TEXT, room_change_by TEXT);
        CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, property_id INT, rating INT, comment TEXT);""")
        path = os.path.join(HERE, "sample_data.json")
        if c.execute("SELECT COUNT(*) FROM properties").fetchone()[0] == 0 and os.path.exists(path):
            for p in json.load(open(path)):
                pid = add_property(c, p)
                if p.get("verified"):
                    c.execute("UPDATE properties SET verified=1 WHERE id=?", (pid,))
init()

def row(c, sql, *a):
    r = c.execute(sql, a).fetchone()
    if not r:
        raise HTTPException(404, "Not found")
    return dict(r)

@app.get("/")
def home():
    return FileResponse(os.path.join(HERE, "index.html"))

@app.get("/properties")
def search(max_rent: int = 10**9, max_distance: float = 10**9, girls_only: bool = False, verified_only: bool = False):
    sql = ("SELECT p.*, (SELECT ROUND(AVG(rating),1) FROM reviews r WHERE r.property_id=p.id) AS avg_rating "
           "FROM properties p WHERE rent<=? AND distance_km<=?")
    if girls_only: sql += " AND girls_only=1"
    if verified_only: sql += " AND verified=1"
    with db() as c:
        return [dict(r) for r in c.execute(sql + " ORDER BY rent", (max_rent, max_distance))]

@app.post("/properties")
def create(p: Property):
    with db() as c:
        return {"id": add_property(c, p.model_dump()), "verified": False}

@app.post("/properties/{pid}/verify")
def verify(pid: int, x_admin_key: str = Header("")):
    if x_admin_key != os.getenv("ADMIN_KEY", "admin123"):
        raise HTTPException(403, "Admin key required")
    with db() as c:
        row(c, "SELECT id FROM properties WHERE id=?", pid)
        c.execute("UPDATE properties SET verified=1 WHERE id=?", (pid,))
    return {"id": pid, "verified": True}

@app.get("/compare")
def compare(ids: str):
    with db() as c:
        return [row(c, "SELECT * FROM properties WHERE id=?", int(i)) for i in ids.split(",")]

class Booking(BaseModel):
    property_id: int
    student: str

@app.post("/bookings")
def book(b: Booking):
    with db() as c:
        p = row(c, "SELECT * FROM properties WHERE id=?", b.property_id)
        text = (f"Agreement: {b.student} rents '{p['title']}' at Rs {p['rent']}/month, deposit Rs {p['deposit']}. "
                "Notice period: 30 days. House rules apply.")
        cur = c.execute("INSERT INTO bookings(property_id,student,escrow,agreement) VALUES(?,?,?,?)",
                        (b.property_id, b.student, "HELD", text))
        return {"id": cur.lastrowid, "escrow": "HELD", "agreement": text}

@app.post("/bookings/{bid}/release")
def release(bid: int):
    with db() as c:
        row(c, "SELECT id FROM bookings WHERE id=?", bid)
        c.execute("UPDATE bookings SET escrow='RELEASED' WHERE id=?", (bid,))
    return {"id": bid, "escrow": "RELEASED"}

class Complaint(BaseModel):
    booking_id: int
    kind: str  # safety | property | other
    details: str

@app.post("/complaints")
def complain(m: Complaint):
    due = str(date.today() + timedelta(days=3)) if m.kind == "safety" else None
    with db() as c:
        row(c, "SELECT id FROM bookings WHERE id=?", m.booking_id)
        cur = c.execute("INSERT INTO complaints(booking_id,kind,details,status,room_change_by) VALUES(?,?,?,?,?)",
                        (m.booking_id, m.kind, m.details, "OPEN", due))
    return {"id": cur.lastrowid, "status": "OPEN", "room_change_by": due}

class Review(BaseModel):
    property_id: int
    rating: int
    comment: str = ""

@app.post("/reviews")
def review(r: Review):
    if not 1 <= r.rating <= 5:
        raise HTTPException(422, "Rating must be 1-5")
    with db() as c:
        row(c, "SELECT id FROM properties WHERE id=?", r.property_id)
        c.execute("INSERT INTO reviews(property_id,rating,comment) VALUES(?,?,?)", (r.property_id, r.rating, r.comment))
    return {"ok": True}
