"""FastAPI application entry-point.

Run locally:
    uvicorn app.main:app --reload

Or with Docker:
    docker compose up
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app import database as _db
from app.database import Base
from app.routers import mpesa, webhook

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Settings ──────────────────────────────────────────────────────────────────
settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables if they do not exist…")
    Base.metadata.create_all(bind=_db.engine)
    logger.info("Database ready.")
    yield


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A WhatsApp-based debt and inventory tracker for Kenyan SMEs. "
        "Shopkeepers record credit sales via WhatsApp messages; the system "
        "parses them, persists the transactions, and integrates with M-Pesa "
        "via the Daraja API for payment confirmations."
    ),
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(webhook.router)
app.include_router(mpesa.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "app": settings.APP_NAME}
