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


def send_message(base_url: str, transcript: str, from_number: str) -> requests.Response:
    """POST to the webhook with form-encoded body mimicking Twilio."""
    return requests.post(
        f"{base_url}{WEBHOOK_PATH}",
        data={
            "Body": transcript,
            "From": f"whatsapp:{from_number}",
        },
        timeout=30,
    )


def run_tests(base_url: str, single_message: str | None = None):
    sep = "─" * 60

    if single_message:
        cases = [("Custom", single_message, "+0000000000")]
    else:
        cases = TEST_CASES

    print(f"\n🌱  Agri-Flow Webhook Test Suite")
    print(f"   Target: {base_url}{WEBHOOK_PATH}\n")

    passed = 0
    failed = 0

    for label, transcript, phone in cases:
        print(sep)
        print(f"📋 Test : {label}")
        print(f"📞 From : {phone}")
        print(f"🎙️  Input: {transcript}")

        try:
            resp = send_message(base_url, transcript, phone)
            status_icon = "✅" if resp.status_code == 200 else "❌"
            print(f"{status_icon} Status: {resp.status_code}")
            print(f"💬 Reply :\n{resp.text}")
            if resp.status_code == 200:
                passed += 1
            else:
                failed += 1
        except requests.exceptions.ConnectionError:
            print("❌ ERROR: Could not connect. Is the server running?")
            print(f"   Run: uvicorn app.main:app --reload")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

        print()

    print(sep)
    print(f"Results: {passed} passed, {failed} failed out of {len(cases)} tests")

    # Print inventory snapshot after all tests
    if not single_message:
        print("\n📦 Current Inventory Snapshot:")
        try:
            inv = requests.get(f"{base_url}/inventory", timeout=10).json()
            if inv:
                for item in inv:
                    print(f"   • {item['name'].title():20s} {item['quantity']:>8.1f} {item['unit']}")
            else:
                print("   (empty)")
        except Exception as e:
            print(f"   Could not fetch inventory: {e}")

    print()
    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agri-Flow webhook tester")
    parser.add_argument("--url", default=BASE_URL, help="Base URL of the FastAPI server")
    parser.add_argument("--message", default=None, help="Single custom message to test")
    args = parser.parse_args()

    success = run_tests(args.url, args.message)
    sys.exit(0 if success else 1)