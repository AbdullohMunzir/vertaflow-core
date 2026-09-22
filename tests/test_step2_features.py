# tests/test_step2_features.py
"""
Automated Test Suite for Step 2 Enhancements in VertaFlow:
1. Voice STT (Telegram Voice Note via Gemini Multimodal STT, Bot text-only reply)
2. Smart Follow-Up Re-engagement Engine (Polite, consultative, non-intrusive)
3. Outbound Omnichannel Dispatcher (Telegram, Meta Instagram, WhatsApp)
4. Channel Quick Notes (Cheat-sheets for Telegram, Instagram, WhatsApp, Web)
5. Creator-Only Business Niche Templates (Mebel, IT Kurslar, Klinika, etc.)
"""

import os
import sys
import requests
import asyncio

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure root directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
CORE_DIR = os.path.join(BASE_DIR, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

import db
from api import send_outbound_channel_message, run_due_follow_ups, WARM_FOLLOW_UPS
from verta_gemini import VertaGeminiClient
from verta_templates import NICHE_TEMPLATES, get_all_templates, get_template

BASE_URL = "http://127.0.0.1:8000"

def test_gemini_voice_stt_method():
    """Verifies that VertaGeminiClient has transcribe_audio method and handles inputs."""
    client_gem = VertaGeminiClient(api_key="test_key")
    assert hasattr(client_gem, "transcribe_audio"), "VertaGeminiClient must have transcribe_audio method"
    
    # Test fallback on mock/invalid audio bytes (should return None or str without throwing)
    mock_audio = b"RIFF....WAVEfmt ...."
    result = client_gem.transcribe_audio(mock_audio, mime_type="audio/ogg")
    assert result is None or isinstance(result, str)
    print(f"STT Fallback transcription: {result}")

def test_channel_quick_notes_api():
    """Verifies channel quick notes endpoints return concise, non-verbose cheat sheets."""
    # Test all guides
    res = requests.get(f"{BASE_URL}/api/channels/guides/all")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "guides" in data
    guides = data["guides"]
    for ch in ["telegram", "instagram", "whatsapp", "web_widget"]:
        assert ch in guides, f"{ch} missing from guides"
        guide = guides[ch]
        assert "quick_notes" in guide
        assert len(guide["quick_notes"]) >= 2
        assert "api_source" in guide

    # Test single channel guide
    res_tg = requests.get(f"{BASE_URL}/api/channels/telegram/guide")
    assert res_tg.status_code == 200
    tg_data = res_tg.json()["guide"]
    assert tg_data["name"] == "Telegram Bot"
    assert "BotFather" in tg_data["quick_notes"][0]

def test_smart_follow_up_engine():
    """Verifies smart follow-up scheduling, database persistence, and execution."""
    session_id = "test_fu_session_001"
    
    # 1. Schedule follow-up via API
    res = requests.post(f"{BASE_URL}/api/follow_up/schedule_test", json={
        "session_id": session_id,
        "channel": "telegram",
        "delay_minutes": 0
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["status"] == "scheduled"
    assert "follow_up_id" in data

    # 2. Trigger due follow-ups
    res_trig = requests.post(f"{BASE_URL}/api/follow_up/trigger")
    assert res_trig.status_code == 200
    trig_data = res_trig.json()
    assert trig_data["status"] == "success"
    assert trig_data["processed_count"] >= 1

    # 3. Check follow-up logs
    res_logs = requests.get(f"{BASE_URL}/api/follow_up/logs")
    assert res_logs.status_code == 200
    logs = res_logs.json()["logs"]
    assert len(logs) > 0
    target_log = next((l for l in logs if l["session_id"] == session_id), None)
    assert target_log is not None
    assert target_log["status"] == "sent"
    assert "Assalomu alaykum" in target_log["follow_up_text"] or "Xayrli kun" in target_log["follow_up_text"]

def test_creator_niche_templates():
    """Verifies Creator Niche Templates repository and 1-click application."""
    # 1. List templates
    res = requests.get(f"{BASE_URL}/api/creator/templates")
    assert res.status_code == 200
    templates = res.json()["templates"]
    assert len(templates) >= 6
    ids = [t["id"] for t in templates]
    assert "mebel" in ids
    assert "oqim_kurs" in ids
    assert "klinika" in ids
    assert "avto" in ids
    assert "kiyim" in ids
    assert "real_estate" in ids

    # 2. Apply 'mebel' template
    res_apply = requests.post(f"{BASE_URL}/api/creator/templates/mebel/apply")
    assert res_apply.status_code == 200
    apply_data = res_apply.json()
    assert apply_data["status"] == "applied"
    assert apply_data["template_id"] == "mebel"

    # Verify business profile was updated
    biz = db.get_business_profile()
    assert "Mebel" in biz["business_name"]
    assert len(biz["faq_list"]) > 0

    # Verify persona was updated
    persona = db.get_agent_persona()
    assert persona["name"] == "Madina"
    assert "Mebel" in persona["role"]

    # Verify battlecards were added
    cards = db.get_battlecards()
    assert any("arzon sexlar" in c["name"].lower() or "bozor" in c["name"].lower() for c in cards)

async def test_outbound_channel_dispatcher():
    """Verifies outbound channel dispatcher executes gracefully for Telegram, Instagram, WhatsApp."""
    res_tg = await send_outbound_channel_message("telegram", "tg_123456", "Salom!")
    assert res_tg is True

    res_ig = await send_outbound_channel_message("instagram", "ig_987654", "Salom Instagram!")
    assert res_ig is True

    res_wa = await send_outbound_channel_message("whatsapp", "wa_998901234567", "Salom WhatsApp!")
    assert res_wa is True

def run_all():
    print("Testing test_gemini_voice_stt_method()...")
    test_gemini_voice_stt_method()
    print("  -> Passed!")

    print("Testing test_channel_quick_notes_api()...")
    test_channel_quick_notes_api()
    print("  -> Passed!")

    print("Testing test_smart_follow_up_engine()...")
    test_smart_follow_up_engine()
    print("  -> Passed!")

    print("Testing test_creator_niche_templates()...")
    test_creator_niche_templates()
    print("  -> Passed!")

    print("Testing test_outbound_channel_dispatcher()...")
    asyncio.run(test_outbound_channel_dispatcher())
    print("  -> Passed!")

    print("\n🎉 ALL STEP 2 TESTS PASSED PERFECTLY (100%)!")

if __name__ == "__main__":
    run_all()
