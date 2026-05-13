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

# ---------------------------------------------------------------------------
# Helper: upsert product and log transaction
# ---------------------------------------------------------------------------
def process_inventory_action(
    db: Session,
    product_name: str,
    quantity_change: float,
    unit: str,
    transcript: str,
    from_number: Optional[str] = None,
) -> dict:
    """
    Upsert a product and record a transaction log.
    Returns a summary dict for the API response.
    """
    product = db.query(Product).filter(Product.name == product_name).first()

    if product is None:
        # New product — quantity starts at the change value (can't go below 0 on first entry)
        initial_quantity = max(quantity_change, 0.0)
        product = Product(
            name=product_name,
            quantity=initial_quantity,
            unit=unit,
        )
        db.add(product)
        db.flush()  # Get the ID before committing
        action = "created"
        logger.info(f"New product created: {product_name} ({initial_quantity} {unit})")
    else:
        # Existing product — update quantity, protect against going below 0
        new_quantity = max(product.quantity + quantity_change, 0.0)
        product.quantity = new_quantity
        product.unit = unit  # Allow unit correction via transcript
        product.updated_at = datetime.utcnow()
        action = "updated"
        logger.info(f"Product updated: {product_name} → {new_quantity} {unit}")

    # Always log the transaction
    log_entry = TransactionLog(
        product_id=product.id,
        quantity_change=quantity_change,
        original_transcript=transcript,
        from_number=from_number,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(product)

    return {
        "action": action,
        "product_name": product.name,
        "new_quantity": product.quantity,
        "unit": product.unit,
        "quantity_change": quantity_change,
    }