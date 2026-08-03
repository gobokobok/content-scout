import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

from src.api.accounts import router as accounts_router
from src.api.admin import router as admin_router
from src.api.auth import router as auth_router
from src.api.billing import router as billing_router
from src.api.deep_analyses import router as deep_analyses_router
from src.api.export import router as export_router
from src.api.history import router as history_router
from src.api.items import router as items_router
from src.api.projects import router as projects_router
from src.api.runs import feed_router as runs_feed_router
from src.api.runs import router as runs_router
from src.api.scheduled_runs import alerts_router as scheduled_run_alerts_router
from src.api.scheduled_runs import router as scheduled_runs_router
from src.api.shortlist import router as shortlist_router
from src.api.telegram_webhook import router as telegram_router
from src.api.telegram_webhook import setup_webhook_and_menu
from src.api.usage import router as usage_router
from src.config import get_settings

# Neither uvicorn nor arq (worker.py) configures the root logger's handlers on our behalf —
# uvicorn's own dictConfig only sets up its own "uvicorn.*" namespace loggers, and arq's only
# configures "arq" — so every `logging.getLogger(__name__)` call in src/ was silently going
# nowhere (found 2026-08-03 debugging a deep-analysis failure with zero log trace anywhere).
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

_DEFAULT_JWT_SECRET = "local-dev-secret-do-not-use-in-prod"
if settings.environment != "local" and settings.jwt_secret == _DEFAULT_JWT_SECRET:
    raise RuntimeError("JWT_SECRET is set to the insecure default — configure it before deploying")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_webhook_and_menu()
    yield


app = FastAPI(title="content-scout api", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(projects_router)
app.include_router(accounts_router)
app.include_router(runs_router)
app.include_router(runs_feed_router)
app.include_router(deep_analyses_router)
app.include_router(scheduled_runs_router)
app.include_router(scheduled_run_alerts_router)
app.include_router(items_router)
app.include_router(export_router)
app.include_router(history_router)
app.include_router(shortlist_router)
app.include_router(usage_router)
app.include_router(admin_router)
app.include_router(telegram_router)


class _SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def _send(message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            await send(message)

        await self.app(scope, receive, _send)


app.add_middleware(_SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.environment}
