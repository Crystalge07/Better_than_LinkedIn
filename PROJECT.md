# PROJECT.md — Job Aggregator

> This is the canonical project doc. Any agent (Cursor or otherwise) working on this
> project should read this file top to bottom before doing anything. It contains the
> purpose, architecture, all fixed decisions, data sources, schema, build order, and
> working rules. Do not restate or re-derive these; follow them. If something here is
> ambiguous or you'd deviate, ASK first.

---

## 1. Purpose / What this is

A job board website that aggregates new-grad and internship postings from free
community GitHub JSON feeds **and** public company career-board APIs (Greenhouse, Lever,
Ashby, Workday CXS). It normalizes them into one schema, de-duplicates across sources,
keeps the data fresh via a scheduled background sync, and serves a filterable UI
with an application tracker still to come.

Coverage goal: huge companies across industries (CPG, industrials, healthcare, finance,
media, tech), not a tech-intern list.

**The core insight:** company career pages get posted to their ATS (Workday/Greenhouse/etc.)
first and syndicated to LinkedIn/Indeed weeks later. These community feeds pull from the
source early. Aggregating them = seeing jobs before the big boards do.

**What this is NOT (scope boundaries):**
- We do NOT HTML-scrape career pages or log into ATS products.
- We DO poll public job-board JSON APIs (Greenhouse/Lever/Ashby documented boards, Workday CXS)
  when a company is listed with a board slug or `*.myworkdayjobs.com` / `*.myworkdaysite.com`
  career URL.
- A list of 1,000 **names** is not enough. Each company needs its board identifier.
  `scripts/add_companies.py` probes the JSON API and only writes boards that respond.
- We are an aggregator + a good interface on top. That's the whole product.

---

## 2. Architecture (one direction of data flow)

```
GitHub JSON feeds + company ATS JSON
      |
      v
Ingestion pipeline  (fetch -> normalize -> dedupe -> diff -> upsert)   <-- the engine we build
      |
      v
Postgres database   (our single source of truth)
      |
      v
FastAPI backend
      |
      v
React frontend      (filter / search / application tracker)
```

**Hard rule:** the website reads ONLY from our Postgres DB. It NEVER fetches GitHub or
company boards live. Only the scheduled ingestion job touches those sources.

Keep these as SEPARATE modules — no god functions:
- fetching (get raw JSON from feeds)
- normalizing (feed shape -> our Job schema)
- deduping (merge duplicates across feeds)
- storing (DB read/write, diffing)
- serving (FastAPI + UI)

---

## 3. Fixed tech decisions (do not substitute without asking)

- Backend: Python + FastAPI
- DB: Postgres (local during dev; hosted Postgres / Supabase later — same Postgres, one env change)
- ORM/driver: SQLAlchemy or psycopg (agent's choice, state which)
- Frontend: React tabs for Jobs, Applications, and Autofill profile. Tracker + profile persist in localStorage until accounts exist.
- Scheduled sync: standalone Python worker, runnable on a cron schedule
  (locally by hand during dev; GitHub Actions or Railway for unattended runs later)
- Config: DB connection read from `DATABASE_URL` env var from DAY ONE.
  Secrets in a gitignored `.env`, with a committed `.env.example`. Never commit secrets.

---

## 4. Data sources (feeds) — verified live, raw JSON, no auth

STEP 1 uses ONLY the first feed. Others come in at STEP 3.

| Use | Feed | URL |
|-----|------|-----|
| STEP 1 | SimplifyJobs internships | https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json |
| STEP 3 (2nd source, creates real dupes) | vanshb03 new-grad | https://raw.githubusercontent.com/vanshb03/New-Grad-2026/dev/.github/scripts/listings.json |
| STEP 3+ (now on) | SimplifyJobs new-grad | https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json |
| Extra community | Simplify internships 2027, vanshb03 2027, SpeedyApply SWE/AI markdown, WarpJobs JSON, Heynish DACH internships | see README Feeds table |
| Ongoing | Company boards | `backend/data/companies.json` (~3,100 probed Greenhouse / Lever / Ashby / Workday JSON boards). Grow with `scripts/add_companies.py`, not name lists. |

These feeds update roughly every 30 min. Poll no more often than every 30–60 min.
Trusted spine = SimplifyJobs. vanshb03 second. Others (zapply/jobright) are lead-gen for
paid products and give partial lists with tracking URLs — add later, weight trust lower.

Repos occasionally rename branches/move files. If a URL 404s, find the current raw path
and confirm it returns JSON before hardcoding.

---

## 5. Feed field shape (same across the 3 feeds above)

Raw feed entry looks like:
```json
{
  "company_name": "Great American Insurance Company",
  "title": "RPA Automation Developer Intern",
  "locations": ["Cincinnati, OH"],
  "url": "https://gaig.wd1.myworkdayjobs.com/.../R8206",
  "date_posted": 1763086480,
  "date_updated": 1763086480,
  "active": false,
  "id": "6e3cef00-04f4-42b8-bb64-7d9653cff91e",
  "source": "Simplify",
  "terms": ["Summer 2026"],
  "sponsorship": "Other"
}
```

Map to our Job schema:
- company_name (str)              -> company
- title (str)                     -> title
- locations (list[str])           -> locations   (already an array, already "City, ST")
- url (str)                       -> apply_url
- date_posted (int, UNIX SECONDS) -> date_posted  (CONVERT to datetime — not a string)
  After ingest, overwrite date_posted with the company's own posting time:
  Greenhouse/Lever/Ashby first-published / created / published; Workday dates
  copied from the matching company-board row; Tesla careers JSON when it
  exposes a published timestamp. Aggregator "listed 2d ago" ages are not the
  posting date. Keep the earliest date we have seen; never move date_posted
  forward because a third-party board recrawled it.
- active (bool)                   -> feed_active   (feed's own open/closed flag)
- id (str)                        -> source_native_id
- source (str)                    -> source tag

**Two `active` concepts — do NOT conflate:**
- `feed_active`: the feed says the job is closed on the company site (`active: false`).
- our `active`: the job disappeared from the feed entirely (we stop seeing it in a sync).
Track both separately.

---

## 6. Internal Job schema (the contract — define this FIRST, in code)

- company: str
- title: str
- locations: list[str]
- apply_url: str
- date_posted: datetime
- source: str            # feed this came from
- sources: list[str]     # all feeds it was found in (populated by dedupe)
- source_native_id: str  # the feed's own id
- feed_active: bool      # feed's open/closed flag
- active: bool           # true while present in feeds; false once it disappears
- first_seen: datetime   # first time WE ingested it
- last_seen: datetime    # most recent sync that still had it
- fingerprint: str       # dedupe key (see section 8)

---

## 7. Sync job behavior (idempotent + resilient)

Runs on a schedule (start: every 60 min). Each run:
1. Fetch every configured feed. If ONE feed fails (network/parse), log it and CONTINUE
   with the others. One bad feed must not abort the whole run.
2. Normalize all entries -> Job schema.
3. Merge + dedupe across feeds (section 8).
4. Diff against DB and upsert:
   - fingerprint new -> insert, first_seen = now, last_seen = now, active = true
   - fingerprint exists & still in feeds -> last_seen = now, active = true, refresh fields
   - in DB but gone from feeds -> active = false (do NOT delete — keep history)
5. Running the job twice back-to-back must produce NO additional changes (idempotent).

Optional efficiency: use GitHub ETag/commit info to skip a feed if unchanged since last pull.

---

## 8. Dedupe (the one genuinely hard part — needs tests)

Same job appears in multiple feeds with different title strings, different URLs, different
location formatting. CANNOT dedupe on URL or exact title.

Build `fingerprint` = hash of (normalized_company + normalized_title + normalized_location):
- normalize company: lowercase; strip suffixes ("Inc.", ", LLC", "Corp.", "Technologies")
- normalize title: lowercase; strip prefixes ("New Grad 2026:", etc.); strip seniority noise
- normalize location: canonical "City, ST"

Match on fingerprint. When multiple records share a fingerprint:
- keep earliest date_posted
- keep the most direct apply_url (prefer the employer's career posting over ATS
  job-board hosts, and those over tracking links)
- never send Apply through a middleman board (WarpJobs / AI Infra Jobs,
  Simplify.jobs, hosted Greenhouse/Lever/Ashby boards, etc.); resolve every
  listing to the company career posting when the employer publishes one
  (Tesla `/careers/search/job/{slug}-{id}`, Stripe `gh_jid` career pages,
  Workday, …)
- record ALL contributing feeds in `sources`

Dedupe logic must be PURE (no DB/network inside it) and UNIT-TESTED with REAL duplicate
pairs as fixtures (same job from two feeds). Cross-source agreement is also a quality
signal — a job in 3 feeds is real and fresh.

---

## 9. Build order — DO ONE STEP AT A TIME. STOP after each for review. DO NOT build ahead.

1. Define Job schema in code. Build ONE adapter (SimplifyJobs internships). Normalize ->
   store in Postgres -> display a plain list in the UI. No scheduler, no dedupe, no extra feeds.
2. Add the scheduled sync job with first_seen/last_seen/active tracking + diff/upsert.
3. Add a SECOND feed adapter (vanshb03) + the dedupe layer with unit tests.
4. Add filtering (role, location, company type) + search to the UI.
5. Add the application tracker (mark applied / status per job; needs user accounts).

Ship at step 1. Every later step is additive.

---

## 10. Must pass code review (non-negotiables)

- Idempotent, resilient sync (per-feed error isolation).
- Pure, unit-tested dedupe with real fixtures.
- Clean module separation (fetch / normalize / dedupe / store / serve).
- No live GitHub calls from the web layer.
- Proper error handling and structured logging in the sync job.
- Config via env vars; no committed secrets.
- date_posted stored as real datetime (converted from unix), not a string.

---

## 11. How to work with the human (agent working rules)

- Before writing code for a step, reply with your PLAN: file/folder structure, libraries
  (and why), and any assumptions. WAIT for "go" before writing code.
- Build only the CURRENT step. Do not scaffold or "prepare for" later steps.
- After a step, tell the human exactly how to run it locally and what they should see.
  Then STOP and wait for review before the next step.
- If the spec is ambiguous or you'd deviate, ASK first — don't guess, don't silently work around.
- If you think a decision here is wrong, say so and why.
- Be direct. Flag anything that wouldn't pass a professional code review.

---

## 12. Current status / progress log (update as you go)

- [x] Step 1 — schema + SimplifyJobs adapter + store + list UI
- [x] Step 2 — scheduled sync + freshness tracking
- [x] Step 3 — second feed + dedupe + tests
- [x] Step 4 — filtering + search
- [x] Step 4b — Simplify new-grad feed
- [x] Step 4c — company career-board JSON pulls (early-career title filter + seed list)
- [~] Step 5 — application tracker (spreadsheet in the web app; autofiller submit writes a row via `POST /api/applications`; accounts still to come)
- [ ] Deploy — Supabase (DB) + GitHub Actions or Railway (scheduled sync)
- [ ] Future — company-type filtering (tech/CPG/Fortune 500); needs company→category map not in feeds

**Notes (2026-07-11):** Step 1 shipped with API defaults: last 30 days, open postings only.
Step 2 adds `scripts/sync.py` — diff/upsert, `first_seen`/`last_seen`/`active` tracking,
per-feed error isolation, optional `--loop` for local dev.
Step 3: vanshb03 new-grad feed + pure dedupe — **exact fingerprint + URL-conflict guard,
no cross-host merge, no verified positive merge case in current two feeds** (cross-feed
duplication is rare here). Fixtures are four negatives only. DB unique key is
`(fingerprint, apply_url)`. Run `scripts/migrate_step3.sql` on existing DBs before syncing.

**Known miss (revisit after third feed):** AIG Early Career Gen AI / Data Engineering —
same Workday URL (`JR2505609`) in both feeds, but different titles → different fingerprints.
We deliberately don't merge on exact URL yet; revisit if same-URL dupes become common.

**Step 4:** API + UI filters for `q` (title/company), `title`, `location` (city substring on
`locations[]`), and date range (`posted_after` / `posted_before`, else `posted_within_days=30`).
All filtering runs in Postgres via SQLAlchemy bound parameters — never browser-side, never
raw-SQL string interpolation. UI result count uses `jobs.length` only until pagination.


**Notes (2026-08-23):** Simplify new-grad is on. Extra community feeds: 2027 Simplify/vanshb03
listings.json, SpeedyApply markdown (SWE + AI), WarpJobs, Heynish DACH. Company boards live in
`backend/data/companies.json` (~3,100 probed Greenhouse/Lever/Ashby/Workday boards, harvested from
community apply URLs + Fortune/CPG seeds). Titles from company boards must match intern /
new-grad / early-career (not "internal", not recruiters). Add boards with
`scripts/add_companies.py --url ... --write` or `--from-feeds --write`; the helper probes the
public JSON API and skips failures. Workday CXS searches intern / new grad / co-op / early career
(5 pages) so a multi-thousand-board sync stays tractable. Custom Workday marketing domains still
need the myworkdayjobs.com or myworkdaysite.com URL.
