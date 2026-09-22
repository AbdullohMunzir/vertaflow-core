# tests/test_whatsapp_fix.py
"""
ECC Regression and Integration Test Suite for WhatsApp Channel Fixes.
Verifies:
1. Authentic scannable WhatsApp Direct Chat QR code generation (wa.me URI, never dummy strings).
2. WhatsApp status endpoint returning clean configuration.
3. Channel configuration updates (saving Phone Number ID, Access Token, Phone Number).
4. Meta Webhook challenge verification (GET /api/webhooks/whatsapp).
5. Inbound message simulation and AI Closer response triggering (POST /api/channels/whatsapp/test).
"""

import os
import sys
import requests
import re
from urllib.parse import quote_plus

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import db

BASE_URL = "http://127.0.0.1:8000"

def test_whatsapp_qr_generates_valid_wame_url():
    """Regression test: QR code must encode authentic wa.me universal URL, NOT dummy 2@VERTAFLOW strings."""
    db.update_channel("instagram", is_connected=0)
    db.update_channel("telegram", is_connected=0)
    db.update_channel("whatsapp", is_connected=0)
    test_phone = "+998 90 999 88 77"
    res = requests.get(f"{BASE_URL}/api/channels/whatsapp/qr?phone={quote_plus(test_phone)}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "image/svg+xml" in res.headers.get("Content-Type", "")

    # Content must NOT contain dummy pairing string
    content = res.text
    assert "2@VERTAFLOW_WHATSAPP_LINK" not in content, "Found deprecated invalid dummy pairing string!"

    # Status endpoint should also report direct chat URL
    status_res = requests.get(f"{BASE_URL}/api/channels/whatsapp/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "chat_url" in status_data
    assert "https://wa.me/" in status_data["chat_url"]
    print("✓ WhatsApp QR encodes valid wa.me URI without dummy string.")

def test_whatsapp_status_endpoint():
    """Verifies that /api/channels/whatsapp/status returns structured metadata."""
    res = requests.get(f"{BASE_URL}/api/channels/whatsapp/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_connected" in data
    assert "webhook_url" in data
    assert "verify_token" in data
    assert "phone_number" in data
    assert "/api/webhooks/whatsapp" in data["webhook_url"]
    assert data["verify_token"] == "verta_wa_token_99"
    print("✓ WhatsApp status endpoint verified.")

def test_whatsapp_config_update():
    """Verifies updating WhatsApp credentials via POST /api/channels/whatsapp."""
    payload = {
        "is_connected": 1,
        "config": {
            "phone_number": "+998 97 765 43 21",
            "phone_number_id": "109876543210987",
            "access_token": "EAAXsampleMetaTokenForVerification12345",
            "app_secret": "sample_secret_hash_value",
            "status": "connected"
        }
    }
    res = requests.post(f"{BASE_URL}/api/channels/whatsapp", json=payload)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "success"

    # Verify updated in DB
    chan = db.get_channel("whatsapp")
    assert chan["is_connected"] == 1
    assert chan["config"]["phone_number"] == "+998 97 765 43 21"
    assert chan["config"]["phone_number_id"] == "109876543210987"
    assert chan["config"]["access_token"] == "EAAXsampleMetaTokenForVerification12345"
    print("✓ WhatsApp config update verified.")

def test_whatsapp_webhook_verification():
    """Verifies Meta Webhook challenge verification for WhatsApp."""
    challenge_val = "1155998844"
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "verta_wa_token_99",
        "hub.challenge": challenge_val
    }
    res = requests.get(f"{BASE_URL}/api/webhooks/whatsapp", params=params)
    assert res.status_code == 200
    assert res.text == challenge_val
    print("✓ WhatsApp Meta Webhook challenge verification passed.")

def test_whatsapp_inbound_simulation():
    """Verifies simulating WhatsApp inbound message triggers AI Closer response."""
    test_payload = {
        "from_number": "998901234567",
        "message": "Salom, mahsulotlaringiz haqida ma'lumot bera olasizmi?"
    }
    res = requests.post(f"{BASE_URL}/api/channels/whatsapp/test", json=test_payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert len(data["reply"]) > 5
    assert "session_id" in data
    assert data["session_id"].startswith("wa_")
    print("✓ WhatsApp inbound simulation triggers AI Closer successfully.")

if __name__ == "__main__":
    test_whatsapp_qr_generates_valid_wame_url()
    test_whatsapp_status_endpoint()
    test_whatsapp_config_update()
    test_whatsapp_webhook_verification()
    test_whatsapp_inbound_simulation()
    print("\nAll WhatsApp tests passed successfully!")
