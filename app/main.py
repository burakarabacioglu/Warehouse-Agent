import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.models import Base, Product, TransactionLog
from app.services.ai_agent import extract_inventory_action

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database setup (synchronous, psycopg2)
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Detect stale connections
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌱 Agri-Flow starting up — creating tables if needed...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables ready.")
    yield
    logger.info("🛑 Agri-Flow shutting down.")


app = FastAPI(
    title="Agri-Flow API",
    description="Voice-to-inventory backend for agricultural businesses",
    version="0.1.0",
    lifespan=lifespan,
)