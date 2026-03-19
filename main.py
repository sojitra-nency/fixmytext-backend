"""
FixMyText FastAPI Backend
=========================
Entry point — starts the ASGI application.

Run locally:
    uvicorn main:app --reload --port 8000
"""

import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from alembic import command
from alembic.config import Config as AlembicConfig

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import engine
from app.services.ai_service import init_groq_client, close_groq_client
from app.services.razorpay_service import init_razorpay
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


def _run_migrations() -> None:
    """Run Alembic migrations to head on startup."""
    alembic_cfg = AlembicConfig("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize/cleanup shared clients on startup/shutdown."""
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        await loop.run_in_executor(pool, _run_migrations)
    init_groq_client()
    init_razorpay()
    yield
    await close_groq_client()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Visitor-Id"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """Quick liveness probe used by Docker / k8s health checks."""
    return {"status": "ok", "version": settings.VERSION}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
