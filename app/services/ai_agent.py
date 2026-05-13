import json
import re
import logging
from typing import Optional
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini once at import time
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

SYSTEM_PROMPT = """
You are an inventory management assistant for an agricultural business called Agri-Flow.
Your job is to parse voice-to-text transcripts (which may be messy or informal) and extract inventory actions.

The transcript may be in Turkish or English. Understand both languages fluently.

You MUST respond with ONLY a valid JSON object — no explanation, no markdown, no code fences.

JSON schema:
{
  "product_name": "<normalized product name in English, lowercase>",
  "quantity_change": <float — POSITIVE for stock additions/receipts, NEGATIVE for removals/sales/usage>,
  "unit": "<unit of measurement: kg, bags, liters, tons, pieces, etc.>"
}

Rules:
- Normalize product names to English and lowercase (e.g., "buğday" → "wheat", "mısır" → "corn")
- If no unit is mentioned, infer the most common unit for that agricultural product (e.g., wheat → kg, milk → liters)
- Words like "added", "received", "eklendi", "geldi", "aldık" → POSITIVE quantity
- Words like "sold", "removed", "used", "sattık", "gitti", "kullandık", "çıktı" → NEGATIVE quantity
- If quantity is ambiguous, default to a positive change
- Always return a float for quantity_change, never a string

Examples:
Transcript: "bugün 50 çuval buğday aldık" → {"product_name": "wheat", "quantity_change": 50.0, "unit": "bags"}
Transcript: "we sold 200 kg of corn today" → {"product_name": "corn", "quantity_change": -200.0, "unit": "kg"}
Transcript: "uh... like 30 liters of milk came in this morning" → {"product_name": "milk", "quantity_change": 30.0, "unit": "liters"}
"""


def parse_json_safely(text: str) -> Optional[dict]:
    """Robustly extract JSON from model output, even if wrapped in markdown."""
    # Strip markdown code fences if present
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON object anywhere in the text
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


def validate_extraction(data: dict) -> dict:
    """Validate and coerce extracted fields to correct types."""
    if not isinstance(data.get("product_name"), str) or not data["product_name"].strip():
        raise ValueError("Missing or invalid product_name")

    try:
        data["quantity_change"] = float(data["quantity_change"])
    except (TypeError, ValueError):
        raise ValueError(f"Invalid quantity_change: {data.get('quantity_change')}")

    if not isinstance(data.get("unit"), str) or not data["unit"].strip():
        data["unit"] = "units"  # Safe fallback

    data["product_name"] = data["product_name"].strip().lower()
    data["unit"] = data["unit"].strip().lower()

    return data


def extract_inventory_action(transcript: str):
    # Use a highly structured prompt to keep the AI focused
    prompt = f"JSON ONLY: '{transcript}'. Schema: {{'product_name': str, 'quantity_change': float, 'unit': str}}"

    try:
        # 2. Add generation_config to prevent cut-offs
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                stop_sequences=['}'],  # Stop exactly at the end of JSON
                temperature=0.1,  # Make it predictable
            )
        )

        if not response.text:
            return None

        # Add the closing bracket if Gemini cut it off (common with rate limits)
        text = response.text.strip()
        if text.startswith("{") and not text.endswith("}"):
            text += '}'

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))

    except Exception as e:
        if "429" in str(e):
            raise RuntimeError("Rate limit hit. Slow down!")
        raise e