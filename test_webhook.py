import argparse
import sys
import requests

BASE_URL = "http://localhost:8000"
WEBHOOK_PATH = "/webhook/whatsapp"

# ---------------------------------------------------------------------------
# Test cases: (description, transcript, from_number)
# ---------------------------------------------------------------------------
TEST_CASES = [
    # --- English additions ---
    (
        "EN | Add wheat (bags)",
        "we received 50 bags of wheat today",
        "+1234567890",
    ),
    (
        "EN | Add corn (kg)",
        "200 kg of corn just came in from the supplier",
        "+1234567890",
    ),
    (
        "EN | Add milk (liters, messy transcript)",
        "uh... like 30 liters of milk came in this morning, maybe 30",
        "+9876543210",
    ),
    # --- Turkish additions ---
    (
        "TR | Buğday ekle",
        "bugün 50 çuval buğday aldık",
        "+905551234567",
    ),
    (
        "TR | Mısır ekle",
        "depoya 300 kilo mısır geldi",
        "+905551234567",
    ),
    # --- Removals ---
    (
        "EN | Remove wheat (sold)",
        "sold 20 bags of wheat to the market",
        "+1234567890",
    ),
    (
        "TR | Satış — mısır",
        "bugün 100 kilo mısır sattık",
        "+905551234567",
    ),
    # --- Edge cases ---
    (
        "EN | Ambiguous product with no unit",
        "added some fertilizer, about 5 tons",
        "+1111111111",
    ),
    (
        "TR | Süt kullanımı",
        "sabah 10 litre süt kullandık",
        "+905559876543",
    ),
]

