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

## Railway state (as of 2026-07-17 init)

Both envs (`dev`, `production`) are provisioned with api/worker/web + Postgres + Redis. Already set per env: DATABASE_URL and REDIS_URL (reference vars), JWT_SECRET (generated, distinct per env), ENVIRONMENT, CORS_ORIGINS, SUMMARY_MODEL, SUMMARY_CONCURRENCY, USE_MOCK_PLATFORM=false, RAILPACK_START_CMD per service, NEXT_PUBLIC_API_URL on web. Empty placeholders awaiting values: APIFY_API_TOKEN, APIFY_IG_ACTOR_ID, ANTHROPIC_API_KEY.

## Human actions required before Sprint 1

1. Copy `.env.example` → `.env`, fill local values (JWT_SECRET, APIFY_API_TOKEN, APIFY_IG_ACTOR_ID, ANTHROPIC_API_KEY).
2. In the Railway dashboard, fill APIFY_API_TOKEN, APIFY_IG_ACTOR_ID, ANTHROPIC_API_KEY on the **api and worker** services in **both** `dev` and `production` environments.
3. Create two Railway **project tokens** (dashboard → Settings → Tokens): one scoped to `dev`, one to `production`; add them as GitHub Actions secrets `RAILWAY_TOKEN_DEV` and `RAILWAY_TOKEN_PROD` at https://github.com/gobokobok/content-scout/settings/secrets/actions.
4. Pick the Apify IG actor (E3-S2 will validate the choice; a posts-scraper with per-result pricing) and note its id in APIFY_IG_ACTOR_ID.
