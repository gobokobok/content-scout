from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.accounts import router as accounts_router
from src.api.auth import router as auth_router
from src.api.export import router as export_router
from src.api.history import router as history_router
from src.api.items import router as items_router
from src.api.projects import router as projects_router
from src.api.runs import router as runs_router
from src.api.shortlist import router as shortlist_router
from src.api.usage import router as usage_router
from src.config import get_settings

settings = get_settings()

app = FastAPI(title="content-scout api")
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(accounts_router)
app.include_router(runs_router)
app.include_router(items_router)
app.include_router(export_router)
app.include_router(history_router)
app.include_router(shortlist_router)
app.include_router(usage_router)

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
