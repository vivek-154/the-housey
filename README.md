# The Housey: Your Safe Home Away From Home

A student-focused accommodation platform prototype: verified owners and properties, transparent listings, girls' safety reporting, mock secure booking, digital agreements and ratings.

> Prototype note: KYC and payments are **mocked**. No real money or identity data is used.

## Features
- Search/filter by rent, distance, girls-only, verified-only
- Compare properties (`/compare?ids=1,2`)
- Admin verification badge
- Booking with mock escrow (HELD, then RELEASED) and an auto-generated agreement
- Safety complaints with a 3-day room-change target
- Ratings and reviews

## Setup
```bash
git clone https://github.com/vivek-154/the-housey.git
cd the-housey
pip install -r requirements.txt
cp env.example .env   # optional; defaults work
uvicorn app:app --reload
```
Open http://127.0.0.1:8000 (UI) or http://127.0.0.1:8000/docs (API docs).

## Environment variables
| Name | Default | Purpose |
|---|---|---|
| ADMIN_KEY | admin123 | Key for the verify endpoint (`X-Admin-Key` header) |
| DB_PATH | housey.db | SQLite file path |

## Tests
```bash
pytest
```

## Docs and data
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Sample data: `sample_data.json` (loaded automatically on first run)

## License
MIT
