# CLAUDE.md

Read `PROJECT.md` before changing architecture. This file is the short agent brief.

## What this is

A job board that aggregates **internship and new-grad / early-career** postings from:

1. Community feeds: Simplify internships (2026+2027), Simplify new-grad, vanshb03 (2026+2027), SpeedyApply SWE/AI markdown, WarpJobs, Heynish DACH
2. Public company career-board JSON APIs listed in `backend/data/companies.json`

Target: huge companies across CPG, industrials, healthcare, finance, media, and tech — not LinkedIn clones and not senior-role dumps.

The UI reads **only Postgres**. Ingestion is `backend/scripts/sync.py`.

## Layout

- `backend/app/normalize/adapters/` — GitHub feed adapters
- `backend/app/ats/` — Greenhouse / Lever / Ashby / Workday mappers + company runner
- `backend/data/companies.json` — company list (name + ATS board or career URL)
- `backend/app/sync/runner.py` — orchestrates feeds + boards into Postgres
- `frontend/src/App.jsx` — filterable list

## Working rules

- `PROJECT.md` is the spec; `README.md` is how to run it. Update those when behavior changes. Touch `CLAUDE.md` / `AGENTS.md` only when architecture or status changes.
- Do not HTML-scrape. Public JSON APIs only.
- You cannot ingest 1,000 companies from names alone. Each row needs `ats`+`board` or `career_url`.
- Per-source error isolation. Pure dedupe. No secrets in git.
- Plan non-trivial steps; if `PROJECT.md` is ambiguous, ask.

## Current status

Shipped: schema, scheduled sync, community feeds (Simplify, vanshb03, SpeedyApply, WarpJobs, Heynish), DB filters/search, company-board ingestion (Greenhouse/Lever/Ashby/Workday) with an early-career title filter and a 34-company seed list. `date_posted` is the company ATS first-published time when the apply URL is Greenhouse/Lever/Ashby; aggregator listing ages are fallback only.

Next: application tracker (accounts), hosted deploy, grow `companies.json` toward 1k firms with real career URLs. Workday custom domains (careers.nike.com) are not auto-discovered yet.
