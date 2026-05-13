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

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse



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

templates = Jinja2Templates(directory="templates")
@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.name).all()
    # Logic: TemplateResponse handles the "translation" of {% %} into HTML
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "products": products}
    )


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


@app.post("/webhook/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form("unknown"),
    db: Session = Depends(get_db),
):
    """
    Twilio WhatsApp webhook.
    Receives a voice-note transcript (Body) and sender (From),
    processes it through Gemini, and updates inventory.

    Returns a TwiML-compatible plain-text response that Twilio can forward
    back to the user as a WhatsApp message.
    """
    transcript = Body.strip()
    logger.info(f"Received from {From}: {transcript[:120]}")

    if not transcript:
        return PlainTextResponse("⚠️ Empty message received. Please send a voice note or text.", status_code=200)

    # --- AI extraction ---
    try:
        extracted = extract_inventory_action(transcript)
    except ValueError as e:
        logger.warning(f"Extraction failed: {e}")
        return (
            "⚠️ Could not understand the inventory action. "
            "Please try again. Example: '50 bags of wheat received today.'"
        )
    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    # --- DB upsert ---
    try:
        result = process_inventory_action(
            db=db,
            product_name=extracted["product_name"],
            quantity_change=extracted["quantity_change"],
            unit=extracted["unit"],
            transcript=transcript,
            from_number=From,
        )
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error while saving inventory")

    # --- Build human-friendly reply ---
    direction = "➕ Added" if result["quantity_change"] >= 0 else "➖ Removed"
    abs_change = abs(result["quantity_change"])

    reply = (
        f"✅ Inventory updated!\n"
        f"{direction} {abs_change} {result['unit']} of {result['product_name'].title()}.\n"
        f"📦 New stock: {result['new_quantity']} {result['unit']}"
    )

    return reply



@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Agri-Flow"}


@app.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    """Return all current product stock levels."""
    products = db.query(Product).order_by(Product.name).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "quantity": p.quantity,
            "unit": p.unit,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in products
    ]


@app.get("/inventory/{product_name}")
def get_product(product_name: str, db: Session = Depends(get_db)):
    """Get a specific product by name."""
    product = db.query(Product).filter(Product.name == product_name.lower()).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_name}' not found")
    return {
        "id": product.id,
        "name": product.name,
        "quantity": product.quantity,
        "unit": product.unit,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }


@app.get("/logs")
def get_logs(limit: int = 20, db: Session = Depends(get_db)):
    """Return the most recent transaction logs."""
    logs = (
        db.query(TransactionLog)
        .order_by(TransactionLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "product_id": log.product_id,
            "quantity_change": log.quantity_change,
            "from_number": log.from_number,
            "original_transcript": log.original_transcript,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]