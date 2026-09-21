"""
Comprehensive Deep API & Database Test Suite for VertaFlow Platform
Covers:
- Auth, sessions, cookies, route guards, security, password hashing
- SQL Injection & malicious inputs
- Channels, channel gating, primary channel status
- Agent chat, conversation history, operator reply
- Leads & CRM operations
- Knowledge base CRUD
- Billing pricing verification (Free 0, Pro 249k, Business 590k)
- Workspaces and settings
"""

import sys
import uuid
import requests

BASE_URL = "http://127.0.0.1:8000"

def log_test(name, passed, details=""):
    mark = "✅ PASS" if passed else "❌ FAIL"
    print(f"[{mark}] {name} {details}")
    if not passed:
        raise AssertionError(f"Test failed: {name} - {details}")

def run_all_api_tests():
    print("=" * 60)
    print("RUNNING COMPREHENSIVE DEEP API TEST SUITE")
    print("=" * 60)
    
    session = requests.Session()
    
    # 1. Unauthenticated /api/auth/me
    res = session.get(f"{BASE_URL}/api/auth/me")
    log_test("Auth Me (Unauthenticated)", res.status_code == 200 and res.json().get("authenticated") is False)
    
    # 2. Unauthenticated /app redirection
    res = session.get(f"{BASE_URL}/app", allow_redirects=False)
    log_test("Route Guard /app (Expect 303 Redirect to /onboarding)", res.status_code == 303 and res.headers.get("location") == "/onboarding")
    
    # 3. Invalid Login (Nonexistent user)
    res = session.post(f"{BASE_URL}/api/auth/login", json={"auth_method": "email", "identifier": "nonexistent@gmail.com", "password": "wrong"})
    log_test("Login Nonexistent User (Expect 401)", res.status_code == 401)
    
    # 4. SQL Injection Attempt on Login
    res = session.post(f"{BASE_URL}/api/auth/login", json={"auth_method": "email", "identifier": "' OR '1'='1' --", "password": "' OR '1'='1"})
    log_test("SQL Injection Prevention on Login (Expect 401)", res.status_code == 401)
    
    # 5. Register with Email (Gmail)
    rand_email = f"test_agent_{uuid.uuid4().hex[:6]}@gmail.com"
    test_password = "SecurePassword!99"
    res = session.post(f"{BASE_URL}/api/auth/register", json={
        "auth_method": "email",
        "identifier": rand_email,
        "password": test_password,
        "full_name": "Deep Test User",
        "selected_plan": "pro"
    })
    log_test("Register User via Email", res.status_code == 200 and res.json().get("status") == "created")
    reg_data = res.json()
    log_test("Register Returns Session Cookie", "vertaflow_session" in session.cookies.get_dict())
    log_test("Password Hash Hidden in Register Response", "password_hash" not in reg_data.get("user", {}))
    
    # 6. Verify /api/auth/me with newly created session
    res = session.get(f"{BASE_URL}/api/auth/me")
    me_data = res.json()
    log_test("Auth Me (Authenticated)", me_data.get("authenticated") is True and me_data.get("user", {}).get("identifier") == rand_email)
    
    # 7. Authorized /app access with session cookie
    res = session.get(f"{BASE_URL}/app", allow_redirects=False)
    log_test("Route Guard /app (Authorized 200 OK)", res.status_code == 200 and "<html" in res.text.lower())
    
    # 8. Test Logout
    res = session.post(f"{BASE_URL}/api/auth/logout")
    log_test("Logout", res.status_code == 200 and res.json().get("status") == "logged_out")
    
    # 9. Verify session cleared
    res = session.get(f"{BASE_URL}/api/auth/me")
    log_test("Auth Me After Logout (Unauthenticated)", res.json().get("authenticated") is False)
    
    # 10. Re-login with created user
    res = session.post(f"{BASE_URL}/api/auth/login", json={
        "auth_method": "email",
        "identifier": rand_email,
        "password": test_password
    })
    log_test("Re-Login Valid Credentials", res.status_code == 200 and res.json().get("status") == "success")
    log_test("Password Hash Hidden in Login Response", "password_hash" not in res.json().get("user", {}))
    
    # 11. Test Login with WRONG password
    fresh_session = requests.Session()
    res = fresh_session.post(f"{BASE_URL}/api/auth/login", json={
        "auth_method": "email",
        "identifier": rand_email,
        "password": "WrongPasswordHere"
    })
    log_test("Login with Invalid Password (Expect 401)", res.status_code == 401)
    
    # 12. Channels API & Gating Verification
    res = session.get(f"{BASE_URL}/api/channels")
    channels = res.json().get("channels", [])
    log_test("Get Channels List", res.status_code == 200 and len(channels) >= 3)
    
    # Connect Instagram channel
    res = session.post(f"{BASE_URL}/api/channels/instagram", json={
        "is_connected": 1,
        "config": {"account_name": "@test_brand_uz", "auto_reply_direct": True}
    })
    log_test("Connect Instagram Channel", res.status_code == 200 and res.json().get("status") == "success")
    
    # Verify primary channel is now True
    res = session.get(f"{BASE_URL}/api/auth/me")
    log_test("Verify has_primary_channel is True after connecting Instagram", res.json().get("has_primary_channel") is True)
    
    # 13. Dashboard Stats
    res = session.get(f"{BASE_URL}/api/dashboard/stats")
    log_test("Dashboard Stats API", res.status_code == 200 and "total_conversations" in res.json())
    
    # 14. AI Chat Simulator & Lead Scoring
    chat_payload = {
        "message": "Assalomu alaykum, erkaklar kostyumi narxi qancha va yetkazib bera olasizmi?",
        "channel": "instagram",
        "session_id": "test_session_" + uuid.uuid4().hex[:6]
    }
    res = session.post(f"{BASE_URL}/api/chat", json=chat_payload)
    log_test("AI Chat Closer Response", res.status_code == 200 and "reply" in res.json())
    chat_resp = res.json()
    log_test("AI Lead Scoring Generated", "lead_score" in chat_resp and "lead_tier" in chat_resp)
    
    # 15. Conversations API
    res = session.get(f"{BASE_URL}/api/conversations")
    log_test("Get Conversations List", res.status_code == 200 and "conversations" in res.json())
    convs = res.json().get("conversations", [])
    if convs:
        sid = convs[0].get("session_id")
        res = session.get(f"{BASE_URL}/api/conversations/{sid}/messages")
        log_test("Get Conversation Messages", res.status_code == 200 and "messages" in res.json())
        
        # Test Operator Manual Reply
        res = session.post(f"{BASE_URL}/api/conversations/{sid}/operator_reply", json={
            "text": "Operator test xabari: tez orada yetkazamiz."
        })
        log_test("Post Operator Reply", res.status_code == 200)
    
    # 16. Leads CRM API
    res = session.get(f"{BASE_URL}/api/leads")
    leads = res.json().get("leads", [])
    log_test("Get Leads List", res.status_code == 200 and isinstance(leads, list))
    
    # Leads CSV Export
    res = session.get(f"{BASE_URL}/api/leads/export")
    log_test("Export Leads CSV", res.status_code == 200 and "text/csv" in res.headers.get("content-type", ""))
    
    # 17. Knowledge Base API (FAQ CRUD)
    faq_question = "Test savol: Kafolat muddati qancha?"
    faq_answer = "Barcha mahsulotlarimizga 1 yil rasmiy kafolat beriladi."
    res = session.post(f"{BASE_URL}/api/knowledge/faq", json={
        "question": faq_question,
        "answer": faq_answer,
        "category": "test"
    })
    log_test("Create Knowledge Base FAQ", res.status_code == 200 and res.json().get("status") == "success")
    
    # Check knowledge list
    res = session.get(f"{BASE_URL}/api/knowledge")
    items = res.json().get("items", [])
    created_item = next((item for item in items if item.get("title") == faq_question), None)
    log_test("FAQ Present in Knowledge List", created_item is not None)
    
    if created_item:
        item_id = created_item.get("id")
        res = session.delete(f"{BASE_URL}/api/knowledge/{item_id}")
        log_test("Delete FAQ item", res.status_code == 200 and res.json().get("status") == "success")
    
    # 18. Agent Persona API
    res = session.get(f"{BASE_URL}/api/agent/persona")
    log_test("Get Agent Persona", res.status_code == 200 and "name" in res.json())
    
    res = session.post(f"{BASE_URL}/api/agent/persona", json={
        "name": "VERTAFLOW Closer",
        "role": "Bosh savdo maslahatchisi",
        "tone": "friendly_closer",
        "avatar": "👩‍💼"
    })
    log_test("Update Agent Persona", res.status_code == 200 and res.json().get("status") == "success")
    
    # 19. Billing Checkout API (Pricing verification)
    res = session.post(f"{BASE_URL}/api/billing/checkout", json={"plan_id": "free", "period": "month"})
    log_test("Checkout Free Plan (0 so'm)", res.status_code == 200 and res.json().get("total_amount") == 0)
    
    res = session.post(f"{BASE_URL}/api/billing/checkout", json={"plan_id": "pro", "period": "month"})
    log_test("Checkout Pro Plan (249,000 so'm)", res.status_code == 200 and res.json().get("total_amount") == 249000)
    
    res = session.post(f"{BASE_URL}/api/billing/checkout", json={"plan_id": "business", "period": "month"})
    log_test("Checkout Business Plan (590,000 so'm)", res.status_code == 200 and res.json().get("total_amount") == 590000)
    
    # 20. Workspaces API
    res = session.get(f"{BASE_URL}/api/workspaces")
    log_test("Get Workspaces", res.status_code == 200 and "workspaces" in res.json())
    
    # 21. Settings API
    res = session.get(f"{BASE_URL}/api/settings")
    log_test("Get Settings", res.status_code == 200 and "llm_model" in res.json())
    
    # 22. Webhooks Verification
    res = session.get(f"{BASE_URL}/api/webhooks/instagram?hub.mode=subscribe&hub.challenge=test_challenge_123&hub.verify_token=verta_ig_token_99")
    log_test("Instagram Webhook Verification Challenge", res.status_code == 200 and res.text == "test_challenge_123")
    
    res = session.get(f"{BASE_URL}/api/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=wa_chal_456&hub.verify_token=verta_wa_token_77")
    log_test("WhatsApp Webhook Verification Challenge", res.status_code == 200 and res.text == "wa_chal_456")

    print("=" * 60)
    print("ALL 25+ DEEP API & DATABASE TESTS PASSED SUCCESSFULLY! 🚀")
    print("=" * 60)

if __name__ == "__main__":
    try:
        run_all_api_tests()
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
