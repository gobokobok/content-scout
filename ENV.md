# ENV — content-scout

All environment variables. No values here — see `.env.example` for the template; real values live in `.env` (local) and the Railway dashboard (DEV/PROD).

## Backend

| Variable | Description | Local | DEV | PROD |
|---|---|---|---|---|
| ENVIRONMENT | `local` / `dev` / `prod` | ✔ | ✔ | ✔ |
| DATABASE_URL | PostgreSQL DSN (Railway provides `postgres://` — backend config must rewrite scheme to `postgresql+asyncpg://`) | docker-compose | Railway plugin | Railway plugin |
| REDIS_URL | Redis DSN (arq queue) | docker-compose | Railway plugin | Railway plugin |
| JWT_SECRET | HS256 signing secret, ≥32 random chars | ✔ | ✔ | ✔ (distinct) |
| ACCESS_TOKEN_EXPIRE_MINUTES | JWT lifetime (default 1440) | ✔ | ✔ | ✔ |
| CORS_ORIGINS | comma-separated frontend origins | ✔ | ✔ | ✔ |
| APIFY_API_TOKEN | Apify account token | ✔ | ✔ | ✔ |
| APIFY_IG_ACTOR_ID | Apify actor for IG profile posts scraping | ✔ | ✔ | ✔ |
| ANTHROPIC_API_KEY | Claude API key | ✔ | ✔ | ✔ |
| SUMMARY_MODEL | default `claude-haiku-4-5-20251001` | ✔ | ✔ | ✔ |
| SUMMARY_CONCURRENCY | parallel Claude calls in worker (default 5) | ✔ | ✔ | ✔ |
| USE_MOCK_PLATFORM | `true` to use fixture scraper (never in PROD) | ✔ | optional | ✘ |

## Frontend

| Variable | Description | Local | DEV | PROD |
|---|---|---|---|---|
| NEXT_PUBLIC_API_URL | Backend base URL | http://localhost:8000 | Railway DEV api | Railway PROD api |

## Railway state (as of 2026-07-18, verified during E1-S1)

Both envs (`dev`, `production`) are provisioned with api/worker/web + Postgres + Redis. Confirmed set on `dev` (verified 2026-07-18 during E3-S2 via `railway variables`): DATABASE_URL and REDIS_URL (reference vars), JWT_SECRET, ENVIRONMENT, CORS_ORIGINS, SUMMARY_MODEL, SUMMARY_CONCURRENCY, USE_MOCK_PLATFORM=false, NEXT_PUBLIC_API_URL on web, APIFY_API_TOKEN, ANTHROPIC_API_KEY (this doc previously listed these three as empty placeholders — stale). APIFY_IG_ACTOR_ID was actually missing and has now been set to `apify/instagram-scraper` on `api`/`worker` in `dev` (Apify's general-purpose IG posts scraper, per-result pricing — see BACKLOG.md E3-S2 changelog). **`production` env vars not yet verified** — check before the first `v*` tag.

**Correction:** this doc previously claimed `RAILPACK_START_CMD` was already set per service — it was not (confirmed by a real `deploy-dev` build failure: "No start command detected"). Railway's builder is Railpack, which only auto-detects a Python start command from `main.py`/`app.py` at the service's build root; since `api`/`worker`'s code lives under `backend/src/`, this must be set explicitly per service:
- `api`: `RAILPACK_START_CMD=uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- `worker`: `RAILPACK_START_CMD=arq src.worker.WorkerSettings` (this will still crash-loop until `backend/src/worker.py` exists — expected until that story lands)

Confirmed set now on `dev` (verified 2026-07-18: `curl <dev-api>/health` → `{"status":"ok","env":"dev"}`). **Not yet set on `production`** — must be added before the first `v*` tag is pushed, or `cd.yml`'s deploy will fail identically.

## Human actions required before Sprint 1

1. Copy `.env.example` → `.env`, fill local values (JWT_SECRET, APIFY_API_TOKEN, APIFY_IG_ACTOR_ID, ANTHROPIC_API_KEY).
2. In the Railway dashboard, fill APIFY_API_TOKEN, APIFY_IG_ACTOR_ID, ANTHROPIC_API_KEY on the **api and worker** services in **both** `dev` and `production` environments.
3. ~~Create two Railway **project tokens**...~~ — done (as GitHub **Environment** secrets on `DEV`/`PROD`, not plain repo secrets; both `ci.yml`/`cd.yml` jobs now declare `environment:` accordingly).
4. ~~Pick the Apify IG actor...~~ — done: `apify/instagram-scraper`, set on `dev` during E3-S2 (2026-07-18).
5. Set `RAILPACK_START_CMD` on `api`/`worker` in the **`production`** environment (see above) — before the first `v*` tag / PROD deploy.
