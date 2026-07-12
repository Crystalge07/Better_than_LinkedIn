# Job Aggregator

A job board that ingests community-maintained GitHub JSON feeds into Postgres and serves them via FastAPI + React.

**Current status: Step 2** — scheduled sync with freshness tracking (`first_seen` / `last_seen` / `active`).

## Architecture

```
GitHub JSON feeds → fetch → normalize (adapters) → sync (diff/upsert) → Postgres → serve (FastAPI) → React UI
```

The web layer reads **only** from Postgres. Feed fetching happens via the sync script (every 60 min in production).

## Prerequisites

- Postgres 16+ (Docker Compose **or** Homebrew: `brew install postgresql@16`)
- Python 3.10+
- Node.js 18+

## Setup

### 1. Start Postgres

**Docker:**

```bash
docker compose up -d
```

**Homebrew (macOS):**

```bash
brew services start postgresql@16
```

Create the app role/db if needed (defaults in `.env.example` use `jobboard` / `jobboard`).

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Set `DATABASE_URL` in `.env` (see `.env.example`). Swapping to hosted Postgres later is a one-line env change.

### 3. Sync jobs

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python3 scripts/sync.py
```

**Local loop (every 60 min):**

```bash
PYTHONPATH=. python3 scripts/sync.py --loop --interval 3600
```

`scripts/ingest.py` still works but prints a deprecation warning and delegates to sync.

### 4. Run API

```bash
cd backend
source .venv/bin/activate
uvicorn app.serve.main:app --reload --port 8000
```

### 5. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Project layout

```
backend/
  app/
    schemas/job.py              # Internal Job contract (Pydantic)
    fetch/client.py             # HTTP fetch for feed URLs
    normalize/
      fingerprint.py            # Basic fingerprint (expanded in step 3)
      adapters/
        base.py                 # FeedAdapter ABC
        listings_json.py        # Shared listings.json field mapping
        simplify_internships.py # SimplifyJobs Summer2026-Internships
    store/
      models.py                 # SQLAlchemy ORM
      database.py
      repository.py             # Sync diff/upsert + list
    sync/
      runner.py                 # Fetch feeds, orchestrate sync
    serve/main.py               # FastAPI app
  scripts/sync.py               # Scheduled sync entrypoint
  scripts/ingest.py             # Deprecated wrapper → sync
frontend/
  src/App.jsx                   # Plain job list
```

## Job schema notes

| Field | Meaning |
|-------|---------|
| `active` | Job is still present in a feed (sync-managed in step 2) |
| `posting_active` | Feed flag — applications open/closed on the source site |
| `source_job_id` | Native `id` from the feed JSON |
| `source` | Feed tag (e.g. `simplify_internships`) |

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/jobs?active_only=true&open_only=true&posted_within_days=30` | List open, in-feed jobs posted recently, newest first |

## Feed (step 1)

- https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json
