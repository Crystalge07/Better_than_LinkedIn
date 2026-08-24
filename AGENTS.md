# AGENTS.md

Cursor / Codex brief. Details live in `PROJECT.md`. Short version in `CLAUDE.md`.

- Product: intern + new-grad job board for large companies, all industries.
- Pipeline: feeds + ATS JSON -> Postgres -> FastAPI -> React. No live fetches from the UI.
- Company list: `backend/data/companies.json` (~3,100 probed boards). Names are not enough; need board slug or career URL. Add via `scripts/add_companies.py`.
- Docs: keep README, PROJECT.md, CLAUDE.md, AGENTS.md updated with every behavior change.
- Do not HTML-scrape career sites. Use public job-board JSON APIs.
