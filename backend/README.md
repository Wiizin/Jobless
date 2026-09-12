# jobless — backend

AI-powered job/internship application assistant. See the project brief for
full constraints; summary of what's here:

## Setup

```bash
cp .env.example .env   # fill in OPENROUTER_API_KEY and DATABASE_URL at minimum
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Database (Supabase)

The database is Supabase (managed Postgres with pgvector), not a local
Postgres container.

1. In Supabase → Project Settings → Database, copy the **Session Pooler**
   connection string (host `aws-0-<region>.pooler.supabase.com`, port
   `5432`). Do *not* use the Direct connection string — it's IPv6-only and
   won't resolve from most networks/CI.
2. Change the scheme from `postgres://` to `postgresql+asyncpg://` so
   SQLAlchemy uses the asyncpg driver, and put the result in
   `DATABASE_URL`.

   ```
   DATABASE_URL=postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```
3. Run this once in the Supabase SQL editor, **before** the first
   `alembic upgrade head` — the offers table has a `vector` column and the
   migration fails without the extension:

   ```sql
   create extension if not exists vector;
   ```

Then `alembic upgrade head`.

The `db` service in `docker-compose.yml` is optional now — it's kept for
running a throwaway local Postgres, but normal dev points `DATABASE_URL` at
Supabase and skips it. `docker compose up backend` runs just the API (note
the `backend` service still hardcodes a local `DATABASE_URL` override;
remove or repoint that env var if you use compose against Supabase).

### LLM provider (OpenRouter)

All model calls go through OpenRouter's OpenAI-compatible API via the
`openai` SDK — see `app/services/llm_client.py`. Set `OPENROUTER_API_KEY`;
`OPENROUTER_MODEL` defaults to `anthropic/claude-sonnet-4.5` and can be
pointed at any OpenRouter model that supports tool calling.
`OPENROUTER_SITE_URL` / `OPENROUTER_APP_NAME` are optional attribution
headers OpenRouter recommends.

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
  LLM structured scoring via OpenRouter).
- Generation (LLM structured output, hard-blocked from inventing profile
  content — see `services/generation.py` docstring) and docx rendering.
- Full CRUD/workflow routers: profile, offers (dashboard), documents
  (generate → edit → approve → download), applications (manual status
  tracking).
- APScheduler interval-based collection job (no Redis/worker queue).
- Tests for the ingestion, matching, and generation slices
  (`tests/test_sources.py`, `test_matching.py`, `test_generation.py`), with
  the OpenRouter client mocked.

## Not yet built

- `core/security.py` is a placeholder shared-secret header check, not real
  auth — fine for a single-user local app, not for anything internet-facing.
- No frontend yet (Next.js, per the stack doc).
- No browser-extension autofill-assist.
- Source adapters use placeholder field mappings for the agency API until
  a real API key/response sample is available — verify against the live
  schema before trusting `to_common_dict`.
