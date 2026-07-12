# Job Aggregator

A job board that ingests community-maintained GitHub JSON feeds into Postgres and serves them via FastAPI + React.

**Current status: Step 4** — DB-side filter/search (title, location, date range, free-text).

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

**Existing DB from Step 1/2:** apply the Step 3 migration before syncing:

```bash
psql jobboard -f scripts/migrate_step3.sql
```

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
      fingerprint.py            # Normalization + fingerprint hash
      apply_url.py              # URL conflict guard + apply_url scoring
      dedupe.py                 # Pure merge_jobs / merge_job_group
      adapters/
        base.py                 # FeedAdapter ABC
        listings_json.py        # Shared listings.json field mapping
        simplify_internships.py # SimplifyJobs Summer2026-Internships
        vanshb03_new_grad.py    # vanshb03 New-Grad-2026
    store/
      models.py                 # SQLAlchemy ORM
      database.py
      repository.py             # Sync diff/upsert + list
    sync/
      runner.py                 # Fetch feeds, orchestrate sync
    serve/main.py               # FastAPI app
  scripts/sync.py               # Scheduled sync entrypoint
  scripts/migrate_step3.sql     # DB migration for dedupe URL guard
  scripts/ingest.py             # Deprecated wrapper → sync
  tests/                        # pytest (pure dedupe/fingerprint tests)
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
| `GET /api/jobs` | List jobs (filters applied in Postgres) |

### `/api/jobs` query params

| Param | Default | Description |
|-------|---------|-------------|
| `active_only` | `true` | Still present in a feed |
| `open_only` | `true` | Applications open on source site |
| `posted_within_days` | `30` | Used when `posted_after` / `posted_before` omitted |
| `posted_after` | — | ISO date; inclusive start of UTC day |
| `posted_before` | — | ISO date; inclusive end of UTC day |
| `title` | — | Case-insensitive substring on job title |
| `location` | — | Case-insensitive substring against `locations` array |
| `q` | — | Free-text over title **or** company |

All string filters are bound SQLAlchemy parameters (not interpolated into raw SQL).
Filtering happens in the database; the frontend must not filter the full dataset client-side.

## Feeds

| Tag | Feed |
|-----|------|
| `simplify_internships` | https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json |
| `vanshb03_new_grad` | https://raw.githubusercontent.com/vanshb03/New-Grad-2026/dev/.github/scripts/listings.json |

## Tests

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. pytest tests/
```
