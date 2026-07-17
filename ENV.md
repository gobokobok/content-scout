# ENV — content-scout

All environment variables. No values here — see `.env.example` for the template; real values live in `.env` (local) and the Railway dashboard (DEV/PROD).

## Backend

| Variable | Description | Local | DEV | PROD |
|---|---|---|---|---|
| ENVIRONMENT | `local` / `dev` / `prod` | ✔ | ✔ | ✔ |
| DATABASE_URL | PostgreSQL DSN | docker-compose | Railway plugin | Railway plugin |
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

## Human actions required before Sprint 1

1. Copy `.env.example` → `.env`, fill local values (JWT_SECRET, APIFY_API_TOKEN, APIFY_IG_ACTOR_ID, ANTHROPIC_API_KEY).
2. After `railway init`: add all backend vars to Railway DEV and PROD services (distinct JWT_SECRET per env).
3. Pick the Apify IG actor (E3-S2 will validate the choice; a posts-scraper with per-result pricing) and note its id in APIFY_IG_ACTOR_ID.
