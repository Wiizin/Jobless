# jobless — frontend

Next.js (App Router) UI over the FastAPI backend in `../backend`. Review
surface only: it shows what the collector found, lets you edit generated
drafts, and records what you did. Nothing here submits an application
anywhere — that mirrors the backend's own human-in-the-loop design.

## Run it

```bash
npm install
cp .env.example .env.local   # defaults are fine for local dev
npm run dev                  # http://localhost:3000
```

The backend must be running on `http://localhost:8000` with CORS enabled for
`http://localhost:3000` (already added in `backend/app/main.py`).

### Environment

| Variable | Default | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the FastAPI app. |
| `NEXT_PUBLIC_SESSION_TOKEN` | unset | Sent as `x-session-token`. Only needed once the backend's `SESSION_SECRET` is changed away from `dev-secret-change-me`; until then `verify_session_token` is a no-op. |

## Layout

```
app/
  layout.tsx            fonts, providers, app shell
  globals.css           design tokens (light + dark), shared primitives
  lib/
    types.ts            hand-written mirrors of the Pydantic schemas
    api.ts              one typed function per endpoint
    hooks.ts            TanStack Query bindings + query-key conventions
    local-store.ts      browser-local profile id and document index
    format.ts           score/status → colour band, date formatting
  components/           Shell (sidebar + topbar), Pill, Ui primitives
  offers/               dashboard + offer detail
  documents/            draft list + review/approve/download screen
  applications/         status tracking
  profile/              profile, search profiles, CV import
```

State is TanStack Query only — reads are `useQuery`, writes are `useMutation`
that invalidate the keys whose server state actually changed. Styling is
plain CSS: tokens in `globals.css`, one CSS Module per component.

## Two things the API doesn't expose

Both are worked around client-side; replace the workaround if the backend
grows the endpoint.

**No way to list profiles.** A profile is only reachable at
`GET /profile/{id}`, so the id of the profile this browser works with is kept
in `localStorage`. `/profile` offers three ways to get one: create a profile,
import a CV, or paste an existing UUID.

**No way to list documents.** A document is only reachable at
`GET /documents/{id}`. Every id returned by `POST /documents/generate` is
recorded locally so `/documents` has something to enumerate; ids attached to
an application are folded in as well, which recovers drafts generated
elsewhere.

## Backend behaviour worth knowing

- `GET /offers` only returns offers that have **already been scored**
  (`match_score IS NOT NULL`). A posting added without a `profile_id` is
  stored unscored and will not appear in the list — the add-posting form warns
  about this when no profile is selected.
- `POST /documents/generate` and `POST /offers/manual` take `profile_id` as a
  **query** parameter, not in the body.
- `PATCH /documents/{id}` validates `cover_letter_sections` as a complete
  `CoverLetterSections`, so the review screen only sends that field for
  documents that actually have cover-letter content.
- Approved documents are immutable (`PATCH` returns 409) and only approved
  documents can be downloaded or attached to an application.
- `POST /offers/manual` uses the posting URL as its dedup key; re-adding the
  same URL returns 409.
