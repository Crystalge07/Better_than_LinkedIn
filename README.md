# Job Aggregator

A job board for internships and new-grad / early-career roles at large companies — CPG, industrials, healthcare, finance, and tech, not LinkedIn and not senior SWE spam.

It ingests community GitHub JSON feeds **and** public company career-board JSON (Greenhouse, Lever, Ashby, Workday) into Postgres, then serves them via FastAPI + React.

**Current status:** Steps 1–4 plus Simplify new-grad and company-board pulls. Application tracker and deploy are next.

## Architecture

```
GitHub JSON feeds + company ATS JSON → fetch → normalize → sync (diff/upsert) → Postgres → serve (FastAPI) → React UI
```

The web layer reads **only** from Postgres. GitHub feeds and company boards are fetched only by the sync script (every 60 min in production).

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
    schemas/job.py
    fetch/client.py             # GET/POST for feeds and ATS JSON
    normalize/
      fingerprint.py
      apply_url.py
      dates.py
      dedupe.py
      adapters/                 # GitHub / community JSON + markdown feeds
    ats/                        # Greenhouse / Lever / Ashby / Workday
    store/
    sync/runner.py              # Feeds + company boards → Postgres
    serve/main.py
  data/companies.json           # Company career boards to poll
  scripts/sync.py
  tests/
frontend/
  src/App.jsx
```

## Job schema notes

| Field | Meaning |
|-------|---------|
| `active` | Job is still present in a feed (sync-managed in step 2) |
| `posting_active` | Feed flag — applications open/closed on the source site |
| `source_job_id` | Native `id` from the feed JSON |
| `source` | Feed tag (e.g. `simplify_internships`) |
| `date_posted` | When the company posted the role on its ATS, not when an aggregator listed it |
| `apply_url` | Company career/ATS posting, not a middleman job board |

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
| `simplify_internships_2027` | https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json |
| `simplify_new_grad` | https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json |
| `vanshb03_new_grad` | https://raw.githubusercontent.com/vanshb03/New-Grad-2026/dev/.github/scripts/listings.json |
| `vanshb03_new_grad_2027` | https://raw.githubusercontent.com/vanshb03/New-Grad-2027/dev/.github/scripts/listings.json |
| `speedyapply_swe_2027` | SpeedyApply SWE markdown tables (USA/intl intern + new grad) |
| `speedyapply_ai_2027` | SpeedyApply AI/ML markdown tables (linked from the SWE repo) |
| `warpjobs` | https://warpjobs.com/jobs.json (from awesome-job-boards) |
| `heynish_dach` | https://raw.githubusercontent.com/heynish/werkstudent-praktikum-jobs/main/jobs.json (nested GitHub list) |
| `greenhouse:*` / `lever:*` / `ashby:*` / `workday:*` | Company boards in `backend/data/companies.json` |

LinkedIn / Indeed / Glassdoor from [awesome-job-boards](https://github.com/emredurukn/awesome-job-boards) are **not** scraped. We only ingest boards that publish a public JSON or GitHub markdown feed.

## Company boards

You cannot ingest ~1,000 companies from **names alone**. Each row in `backend/data/companies.json` needs the public job-board identity:

| ATS | What to put in the JSON |
|-----|-------------------------|
| greenhouse | `"ats": "greenhouse", "board": "stripe"` or `career_url` like `https://job-boards.greenhouse.io/stripe` |
| lever | `"ats": "lever", "board": "spotify"` or `https://jobs.lever.co/spotify` |
| ashby | `"ats": "ashby", "board": "openai"` or `https://jobs.ashbyhq.com/openai` |
| workday | `"ats": "workday", "career_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"` (host + site slug, not just "NVIDIA") |

Sync polls those JSON APIs, then **keeps intern / new-grad / early-career titles only**. Workday custom domains (e.g. careers.nike.com) are not auto-discovered; paste the underlying `*.myworkdayjobs.com/...` URL.

A seed list of large companies is already in `companies.json`. Add more rows there; do not invent 1k unverified slugs.

## Tests

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. pytest tests/
```
