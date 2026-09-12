# jobless — backend

AI-powered job/internship application assistant. See the project brief for
full constraints; summary of what's here:

## Setup

```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY at minimum
docker compose up -d db
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Or run everything via `docker compose up`.

## What's implemented

- Full DB schema (profile, experiences, skills, education, certifications,
  search_profile, offers w/ pgvector embedding, documents, applications) +
  initial Alembic migration.
- Source adapters for the national employment agency API, an Adzuna-style
  aggregator, and public Greenhouse/Lever board endpoints — all official
  APIs, no scraping. Fill in the relevant `.env` keys to activate each; an
  unconfigured adapter just returns `[]` so the pipeline degrades gracefully.
- Normalizer, rapidfuzz-based cross-source deduplicator, embeddings
  (sentence-transformers), two-stage matching (pgvector cosine filter +
  Claude structured scoring).
- Generation (Claude structured output, hard-blocked from inventing profile
  content — see `services/generation.py` docstring) and docx rendering.
- Full CRUD/workflow routers: profile, offers (dashboard), documents
  (generate → edit → approve → download), applications (manual status
  tracking).
- APScheduler interval-based collection job (no Redis/worker queue).
- Tests for the ingestion, matching, and generation slices
  (`tests/test_sources.py`, `test_matching.py`, `test_generation.py`), with
  the Anthropic client mocked.

## Not yet built

- `core/security.py` is a placeholder shared-secret header check, not real
  auth — fine for a single-user local app, not for anything internet-facing.
- No frontend yet (Next.js, per the stack doc).
- No browser-extension autofill-assist.
- Source adapters use placeholder field mappings for the agency API until
  a real API key/response sample is available — verify against the live
  schema before trusting `to_common_dict`.
