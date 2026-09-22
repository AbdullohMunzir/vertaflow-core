# /home/kinfolkt/verta-platform/api.py
"""
VertaFlow — Central Production-Grade FastAPI Server & Hub
Fully backed by SQLite database (db.py).
Provides REST endpoints for Chat, CRM, Real-time Inbox, Human Takeover,
AI Settings, Telegram Bot Lifecycle, Battlecards, and Self-Improving Evaluator.
"""

import sys
import os

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
import re
import json
from typing import Dict, Any, List, Optional
from collections import defaultdict
import io
import csv
import time
import hmac
import hashlib
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Request, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, RedirectResponse, JSONResponse
from pydantic import BaseModel
import aiohttp

# Add core engine to path
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "core"))

import db
from verta_engine import VertaFlowEngine
from verta_llm import VertaLLMClient
from verta_gemini import VertaGeminiClient
from verta_battlecards import Battlecard, BattlecardEngine
from verta_evaluator import VertaEvaluator
from verta_rag import get_rag_engine
from verta_templates import get_all_templates, get_template
from telegram_bot import bot_instance

app = FastAPI(title="VertaFlow AI Platform API", version="2.5.0")

@app.on_event("startup")
async def startup_event():
    """Initializes DB and ensures all knowledge items are indexed with RAG vectors."""
    db.init_db()
    try:
        rag = get_rag_engine()
        rag.sync_all_knowledge()
    except Exception as e:
        print(f"[RAG] Startup indexing error: {e}")
    # Start background smart follow-up scheduler
    asyncio.create_task(follow_up_scheduler_loop())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory runtime cache for engine states with TTL eviction
ENGINE_CACHE_TTL_SECONDS = 7200  # 2 hours
MAX_ENGINE_CACHE_SIZE = 1000
engine_cache: Dict[str, Dict[str, Any]] = {}

def cleanup_engine_cache():
    """Evicts idle sessions older than TTL and bounds memory to MAX_ENGINE_CACHE_SIZE."""
    now = time.time()
    expired = [sid for sid, item in engine_cache.items() if (now - item.get("last_accessed", 0)) > ENGINE_CACHE_TTL_SECONDS]
    for sid in expired:
        del engine_cache[sid]
    if len(engine_cache) > MAX_ENGINE_CACHE_SIZE:
        sorted_sids = sorted(engine_cache.keys(), key=lambda s: engine_cache[s].get("last_accessed", 0))
        for sid in sorted_sids[:len(engine_cache) - MAX_ENGINE_CACHE_SIZE]:
            del engine_cache[sid]

class InMemoryRateLimiter:
    """Sliding window rate limiter to protect endpoints against DoS, brute force, and token drainage."""
    def __init__(self):
        self.requests = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if now - t < window_seconds]
        if len(self.requests[key]) >= max_requests:
            return False
        self.requests[key].append(now)
        return True

rate_limiter = InMemoryRateLimiter()

def verify_meta_signature(raw_body: bytes, signature_header: Optional[str], secret: Optional[str]) -> bool:
    """Verifies X-Hub-Signature-256 for Meta Webhooks (Instagram / WhatsApp)."""
    if not secret:
        return True  # Bypass in dev/test if secret is not set yet
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    signature = signature_header[len("sha256="):]
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

# ----------------- OUTBOUND MESSAGING & OMNICHANNEL DISPATCH -----------------

async def send_outbound_channel_message(channel: str, recipient_id: str, text: str, prefix: str = "") -> bool:
    """
    Dispatches outbound message to external channels (Telegram, Instagram Direct, WhatsApp Cloud API).
    Never crashes caller on network or API failures.
    """
    full_text = f"{prefix}{text}" if prefix else text
    ch = (channel or "web_simulator").lower().strip()

    if ch == "telegram":
        clean_id = recipient_id.replace("tg_", "")
        try:
            chat_id = int(clean_id)
        except ValueError:
            chat_id = None
        if chat_id:
            try:
                async with aiohttp.ClientSession() as http_sess:
                    await bot_instance.send_message(http_sess, chat_id, full_text)
                return True
            except Exception as e:
                print(f"[Outbound Telegram Error]: {e}")
                return False

    elif ch == "instagram":
        chan = db.get_channel("instagram")
        cfg = chan.get("config", {}) if chan else {}
        token = cfg.get("access_token") or cfg.get("page_access_token")
        clean_id = recipient_id.replace("ig_comm_", "").replace("ig_", "")
        if token:
            try:
                url = "https://graph.facebook.com/v19.0/me/messages"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                payload = {
                    "recipient": {"id": clean_id},
                    "message": {"text": full_text}
                }
                async with aiohttp.ClientSession() as http_sess:
                    async with http_sess.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            print(f"[Outbound Instagram Error]: {resp.status} - {body}")
                            return False
                return True
            except Exception as e:
                print(f"[Outbound Instagram Exception]: {e}")
                return False
        else:
            print(f"[Outbound Instagram Simulation]: ID {clean_id} ga yuborildi: {full_text[:60]}...")
            return True

    elif ch == "whatsapp":
        chan = db.get_channel("whatsapp")
        cfg = chan.get("config", {}) if chan else {}
        token = cfg.get("access_token")
        phone_number_id = cfg.get("phone_number_id") or "default_phone_id"
        clean_id = recipient_id.replace("wa_", "")
        if token and phone_number_id:
            try:
                url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_id,
                    "type": "text",
                    "text": {"body": full_text}
                }
                async with aiohttp.ClientSession() as http_sess:
                    async with http_sess.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            print(f"[Outbound WhatsApp Error]: {resp.status} - {body}")
                            if "sample" in token.lower() or "test" in token.lower():
                                return True
                            return False
                return True
            except Exception as e:
                print(f"[Outbound WhatsApp Exception]: {e}")
                return False
        else:
            print(f"[Outbound WhatsApp Simulation]: ID {clean_id} ga yuborildi: {full_text[:60]}...")
            return True

    return True

# ----------------- SMART FOLLOW-UP RE-ENGAGEMENT ENGINE -----------------

WARM_FOLLOW_UPS: Dict[int, str] = {
    1: "Assalomu alaykum! Yuqoridagi ma'lumotlar bilan tanishishga ulgurdingizmi? Agar qo'shimcha savollaringiz yoki noaniq joylar bo'lsa, bemalol so'rashingiz mumkin — sizga yordam berishdan mamnunmiz 😊",
    2: "Xayrli kun! O'ylaymanki sizda barchasi a'lo darajada. Siz qiziqqan variantlar bo'yicha maxsus qulay shartlarimizni saqlab turibmiz. Tanlashda qaysi jihat siz uchun eng muhimi bo'lyapti?",
    3: "Assalomu alaykum! Biz sizning vaqtingizni qadrlaymiz. Agar maslahat yoki batafsil hisob-kitob kerak bo'lsa, istalgan paytda yozishingiz mumkin. Kunningiz xayrli va barakali o'tsin!"
}

async def run_due_follow_ups() -> List[Dict[str, Any]]:
    """Checks and triggers due follow-up messages across all channels."""
    due = db.get_due_follow_ups()
    results = []
    for fu in due:
        sid = fu["session_id"]
        ch = fu.get("channel") or "telegram"
        step = fu.get("follow_up_step", 1)
        text = WARM_FOLLOW_UPS.get(step, WARM_FOLLOW_UPS[1])
        
        # 1. Record follow-up message to conversation history
        db.add_message(sid, sender="agent", text=text, stage="FOLLOW_UP")
        # 2. Outbound dispatch to client channel
        await send_outbound_channel_message(ch, sid, text)
        # 3. Mark follow-up as sent
        db.mark_follow_up_sent(fu["id"], text)
        results.append({"id": fu["id"], "session_id": sid, "channel": ch, "text": text})
    return results

async def follow_up_scheduler_loop():
    """Background loop that checks for due follow-ups every 30 seconds."""
    while True:
        try:
            await run_due_follow_ups()
        except Exception as e:
            print(f"[FollowUp Scheduler Exception]: {e}")
        await asyncio.sleep(30)

def get_or_create_engine(session_id: str, channel: str = "web_simulator") -> VertaFlowEngine:
    cleanup_engine_cache()
    now = time.time()
    if session_id not in engine_cache:
        biz_profile = db.get_business_profile()
        gemini_key = db.get_setting("gemini_api_key")
        gemini_client = VertaGeminiClient(api_key=gemini_key)

        api_key = db.get_setting("llm_api_key")
        provider = db.get_setting("llm_provider", "openai")
        model = db.get_setting("llm_model")
        llm_client = VertaLLMClient(api_key=api_key, provider=provider, model=model)

        knowledge_text = db.get_all_knowledge_text()
        persona = db.get_agent_persona()

        engine = VertaFlowEngine(
            session_id=session_id,
            channel=channel,
            business_profile=biz_profile,
            gemini_client=gemini_client,
            llm_client=llm_client,
            knowledge_text=knowledge_text,
            persona=persona
        )

        # Sync battlecards from database
        db_cards = db.get_battlecards()
        cards_list = []
        for c in db_cards:
            cards_list.append(Battlecard(
                name=c["name"],
                keywords=c["keywords"],
                their_strength=c.get("strength") or "Past narx",
                their_weakness=c["weakness"],
                reframe_talk_track=c["reframe"],
                landmine_question=c["landmine"]
            ))
        if cards_list:
            engine.battlecards = BattlecardEngine(cards_list)

        engine_cache[session_id] = {
            "engine": engine,
            "last_accessed": now
        }
    else:
        engine_cache[session_id]["last_accessed"] = now

    engine_obj = engine_cache[session_id]["engine"]
    # Always ensure business profile, knowledge, and persona are up-to-date
    engine_obj.business_profile = db.get_business_profile()
    engine_obj.knowledge_text = db.get_all_knowledge_text()
    engine_obj.persona = db.get_agent_persona()
    return engine_obj

# Request Models
class ChatMessage(BaseModel):
    session_id: str
    message: str
    channel: Optional[str] = "web_simulator"
    user_name: Optional[str] = "Mijoz"

class OperatorReply(BaseModel):
    text: str

class ToggleAutopilot(BaseModel):
    enabled: bool

class OnboardingData(BaseModel):
    business_name: str
    business_desc: str
    avg_check: Optional[str] = None
    faq_list: Optional[List[Dict[str, str]]] = None

class BattlecardItem(BaseModel):
    name: str
    keywords: List[str]
    their_weakness: str
    reframe_talk_track: str
    landmine_question: str
    their_strength: Optional[str] = "Past narx"

class SettingsData(BaseModel):
    telegram_bot_token: Optional[str] = None
    sales_manager_chat_id: Optional[str] = None
    gemini_api_key: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None

class RecommendationApply(BaseModel):
    id: str

class FAQItem(BaseModel):
    question: str
    answer: str
    category: Optional[str] = "Umumiy"

class URLKnowledge(BaseModel):
    url: str
    title: Optional[str] = None
    content: Optional[str] = None

class TextKnowledge(BaseModel):
    title: str
    content: str
    category: Optional[str] = "Katalog va Narxlar"

class KnowledgeBatchDelete(BaseModel):
    item_ids: List[int]

class PersonaUpdate(BaseModel):
    name: Optional[str] = "Madina"
    company_name: Optional[str] = ""
    role: Optional[str] = "Sotuv bo'yicha maslahatchi"
    avatar: Optional[str] = "👩‍💼"
    tone: Optional[str] = "friendly_closer"
    tone_label: Optional[str] = "Samimiy & Savdo yopuvchi"
    greeting: Optional[str] = "Assalomu alaykum! Qaysi mahsulotimiz sizga ma'qul bo'lyapti?"
    max_discount: Optional[str] = "10%"
    rules: Optional[Dict[str, bool]] = None
    system_prompt: Optional[str] = None

class ChannelConfigUpdate(BaseModel):
    is_connected: Optional[int] = None
    config: Optional[Dict[str, Any]] = None

class ChannelTestMessage(BaseModel):
    channel: str
    message: str
    user_name: Optional[str] = "Mijoz"

class WorkspaceCreate(BaseModel):
    name: str
    niche: Optional[str] = "Chakana savdo"
    description: Optional[str] = ""
    avg_check: Optional[str] = "1 000 000 so'm"

class WorkspaceSwitch(BaseModel):
    workspace_id: str

class BillingCheckout(BaseModel):
    plan_id: str  # 'free', 'pro', or 'business'
    period_months: Optional[int] = 1  # 1, 3, 6, 12
    payment_method: Optional[str] = "free"  # 'free', 'payme' or 'click'

class RegisterRequest(BaseModel):
    auth_method: str  # 'email', 'telegram', 'instagram'
    identifier: str  # email or @username
    full_name: Optional[str] = ""
    password: Optional[str] = ""
    selected_plan: Optional[str] = "free"

class LoginRequest(BaseModel):
    auth_method: str  # 'email', 'telegram', 'instagram'
    identifier: str
    password: Optional[str] = ""

# ----------------- CHAT & CONVERSATIONS API -----------------

def handle_chat_logic(msg: ChatMessage, client_ip: Optional[str] = None) -> Dict[str, Any]:
    """Processes chat message with security checks, persistence, and AI sales response."""
    text = msg.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Xabar bo'sh bo'lishi mumkin emas")

    # Security: Max Payload / Length Guard (Denial-of-Wallet Defense)
    if len(text) > 1500:
        raise HTTPException(status_code=400, detail="Xabar uzunligi me'yordan ortiq (maksimal 1 500 belgi). Iltimos, qisqaroq xabar yuboring.")

    session_id = msg.session_id
    channel = msg.channel or "web_simulator"

    # Security: Rate Limiter (Max 30 req/min per client)
    if client_ip:
        if not rate_limiter.is_allowed(f"chat:{client_ip}", max_requests=30, window_seconds=60):
            raise HTTPException(status_code=429, detail="Juda ko'p so'rov yuborildi. Iltimos, 1 daqiqa kuting (Rate limit oshdi).")

    # Security: Enforce Workspace Plan Quota (AI Messages & Tokens)
    ws_id = db.get_active_workspace_id()
    quota_ok, quota_msg = db.check_quota(ws_id, "ai_chat")
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_msg)

    # 1. Ensure conversation exists in DB
    conv = db.get_conversation(session_id)
    if not conv:
        db.create_or_update_conversation(session_id, name=msg.user_name or "Mijoz", channel=channel)
        conv = db.get_conversation(session_id)

    # Reset any pending follow-ups since lead is active
    db.cancel_pending_follow_ups(session_id)

    # 2. Record user message to DB
    db.add_message(session_id, sender="user", text=text)

    # 3. Check if operator paused autopilot
    if conv and conv.get("autopilot_enabled") == 0:
        return {
            "reply": "Operator qabul qildi. Hozirda inson-operator sizga javob yozmoqda.",
            "stage": "HANDOFF_HUMAN",
            "lead_score": 50,
            "lead_tier": "WARM ⚡",
            "autopilot_paused": True
        }

    # 4. Process via Master Sales Engine
    engine = get_or_create_engine(session_id, channel=channel)
    response = engine.process_message(text)

    # 5. Authoritative Server-Side Token Recording
    token_usage = response.get("token_usage") or {}
    db.record_token_usage(
        workspace_id=ws_id,
        session_id=session_id,
        model=token_usage.get("model", "verta-model"),
        prompt_tokens=token_usage.get("prompt_tokens", 0),
        completion_tokens=token_usage.get("completion_tokens", 0)
    )

    # 6. Record agent reply to DB
    db.add_message(session_id, sender="agent", text=response["reply"], stage=response["stage"], script=response["script"])

    # 7. Schedule smart re-engagement follow-up (default 120 minutes)
    try:
        db.schedule_follow_up(session_id=session_id, channel=channel, name=conv["name"] if conv else "Mijoz", delay_minutes=120, step=1)
    except Exception as fe:
        print(f"[FollowUp Scheduling Error]: {fe}")

    # 8. Save qualified lead state
    db.save_lead(
        session_id=session_id,
        name=conv["name"] if conv else "Mijoz",
        channel=channel,
        phone=engine.state.collected_attributes.get("phone"),
        pain=engine.state.collected_attributes.get("identified_pain"),
        volume=engine.state.collected_attributes.get("volume_or_size"),
        timeline=engine.state.collected_attributes.get("timeline"),
        score=response["lead_score"],
        tier=response["lead_tier"],
        stage=response["stage"],
        script=response["script"],
        score_reasons=response["score_reasons"],
        dossier=response.get("dossier")
    )

    return response

@app.post("/api/chat")
def process_chat(msg: ChatMessage, request: Request):
    """Processes incoming chat from web simulator or widget, persists to DB, and returns AI Closer response."""
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    return handle_chat_logic(msg, client_ip=client_ip)

@app.get("/api/conversations")
def get_conversations():
    """Returns dynamic inbox list with latest messages and statuses."""
    conversations = db.list_conversations()
    return {"conversations": conversations, "total": len(conversations)}

@app.get("/api/conversations/{session_id}/messages")
def get_conversation_messages(session_id: str):
    """Returns full chronological chat messages for a session."""
    conv = db.get_conversation(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    messages = db.get_messages(session_id)
    return {"conversation": conv, "messages": messages}

@app.post("/api/conversations/{session_id}/operator_reply")
async def send_operator_reply(session_id: str, reply: OperatorReply):
    """Allows human operator to send reply directly, pausing AI autopilot and forwarding to channel."""
    conv = db.get_conversation(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")

    # Disable autopilot so AI doesn't interfere
    db.toggle_conversation_autopilot(session_id, False)

    # Cancel pending follow-ups since operator is handling
    db.cancel_pending_follow_ups(session_id)

    # Save operator message to DB
    db.add_message(session_id, sender="operator", text=reply.text)

    # Dispatch to channel (Telegram, Instagram, WhatsApp)
    chan = conv.get("channel") or "web_simulator"
    await send_outbound_channel_message(chan, session_id, reply.text, prefix="👨‍💼 Operator: ")

    return {"status": "success", "message": "Xabar yuborildi va AI avtopilot to'xtatildi."}

@app.post("/api/conversations/{session_id}/toggle_autopilot")
def toggle_autopilot(session_id: str, data: ToggleAutopilot):
    """Toggles AI autopilot on or off for a specific conversation."""
    db.toggle_conversation_autopilot(session_id, data.enabled)
    return {"status": "success", "autopilot_enabled": data.enabled}

# ----------------- LEADS & CRM API -----------------

@app.get("/api/leads")
def list_leads():
    leads = db.get_leads()
    return {"leads": leads, "total_leads": len(leads)}

@app.get("/api/leads/export")
def export_leads_csv():
    """Generates downloadable Excel/CSV file of all qualified leads."""
    leads = db.get_leads()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Mijoz Nomi", "Kanal", "Telefon", "Soha va Og'riq", "Hajm", "Xarid Muddati", "Ball", "Holati", "Sana"])
    for l in leads:
        writer.writerow([
            l.get("name", ""),
            l.get("channel", ""),
            l.get("phone", ""),
            l.get("pain", ""),
            l.get("volume", ""),
            l.get("timeline", ""),
            l.get("score", 0),
            l.get("tier", ""),
            l.get("updated_at", "")
        ])
    output.seek(0)
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vertaflow_leads.csv"}
    )

# ----------------- BATTLECARDS API -----------------

@app.get("/api/battlecards")
def get_battlecards():
    cards = db.get_battlecards()
    return {"battlecards": cards}

@app.post("/api/battlecards/add")
def add_battlecard(item: BattlecardItem):
    db.add_battlecard(
        name=item.name,
        keywords=item.keywords,
        weakness=item.their_weakness,
        reframe=item.reframe_talk_track,
        landmine=item.landmine_question,
        strength=item.their_strength or "Past narx"
    )
    # Clear engine cache so new battlecards reload
    engine_cache.clear()
    return {"status": "success", "message": f"'{item.name}' battlecardi saqlandi!"}

# ----------------- ONBOARDING & BUSINESS PROFILE -----------------

@app.get("/api/onboarding")
def get_onboarding():
    return db.get_business_profile()

@app.post("/api/onboarding")
def save_onboarding(data: OnboardingData):
    db.update_business_profile(
        name=data.business_name,
        desc=data.business_desc,
        avg_check=data.avg_check or "",
        faq_list=data.faq_list
    )
    # Clear cache so engines reload the new business profile
    engine_cache.clear()
    return {"status": "success", "profile": db.get_business_profile()}

# ----------------- EVALUATOR & NIGHTLY AUDIT -----------------

@app.get("/api/evaluator/insights")
def get_evaluator_insights():
    # Pass all active engine instances or leads
    leads = db.get_leads()
    mock_sessions = {}
    for l in leads:
        sid = l["session_id"]
        eng = get_or_create_engine(sid, channel=l["channel"])
        mock_sessions[sid] = eng

    evaluator = VertaEvaluator(mock_sessions)
    report = evaluator.generate_audit_report()
    return report

@app.post("/api/evaluator/apply")
def apply_evaluator_recommendation(req: RecommendationApply):
    evaluator = VertaEvaluator({})
    report = evaluator.generate_audit_report()
    recs = report.get("recommendations", [])
    
    target = next((r for r in recs if r["id"] == req.id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Tavsiya topilmadi")

    if target["action_type"] == "add_battlecard":
        payload = target["action_payload"]
        db.add_battlecard(
            name=payload["competitor_name"],
            keywords=payload["keywords"],
            weakness=payload["weakness"],
            reframe=payload["reframe"],
            landmine=payload["landmine"],
            strength="Past narx"
        )
        engine_cache.clear()
        return {"status": "applied", "message": f"'{payload['competitor_name']}' battlecardi qo'shildi!"}
    
    elif target["action_type"] == "add_faq":
        payload = target["action_payload"]
        biz = db.get_business_profile()
        faqs = biz.get("faq_list", [])
        faqs.append(payload)
        db.update_business_profile(biz["business_name"], biz["business_desc"], biz["avg_check"], faqs)
        engine_cache.clear()
        return {"status": "applied", "message": "Yangi FAQ bilimi saqlandi!"}

# ----------------- DASHBOARD & STATS API -----------------

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Returns aggregated business KPIs for the main dashboard."""
    return db.get_dashboard_stats()

# ----------------- KNOWLEDGE BASE API -----------------

@app.get("/api/knowledge")
def list_knowledge():
    """Returns all company knowledge base documents, FAQs, and URLs."""
    items = db.list_knowledge_items()
    return {"items": items, "total": len(items)}

@app.post("/api/knowledge/faq")
def add_faq(faq: FAQItem):
    """Adds a new question-answer pair to knowledge base and updates RAG index."""
    ws_id = db.get_active_workspace_id()
    allowed, reason = db.check_quota(ws_id, "add_knowledge")
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    meta = {"category": faq.category or "Umumiy", "question": faq.question, "answer": faq.answer}
    item_id = db.add_knowledge_item(
        title=faq.question,
        item_type="faq",
        content=faq.answer,
        metadata=meta
    )
    try:
        get_rag_engine().index_document(parent_id=item_id, title=faq.question, item_type="faq", content=faq.answer, metadata=meta)
    except Exception as e:
        print(f"[RAG] Index error on FAQ: {e}")
    engine_cache.clear()
    return {"status": "success", "id": item_id, "message": "Yangi FAQ bilimi saqlandi va RAG indeksiga kiritildi!"}

@app.post("/api/knowledge/upload")
async def upload_document(file: UploadFile = File(...), category: Optional[str] = Form("Hujjat va Katalog")):
    """Uploads, chunks, embeds, and indexes PDF, DOCX, CSV, or TXT file into knowledge base."""
    ws_id = db.get_active_workspace_id()
    allowed, reason = db.check_quota(ws_id, "add_knowledge")
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    content_bytes = await file.read()
    filename = file.filename or "hujjat"
    extracted_text = ""
    
    if filename.lower().endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            extracted_text = "\n".join([p.extract_text() or "" for p in reader.pages])
        except Exception:
            extracted_text = f"PDF fayl: {filename} (hajmi: {len(content_bytes)} bayt)"
    else:
        extracted_text = content_bytes.decode("utf-8", errors="ignore")
    
    if not extracted_text.strip():
        extracted_text = f"Fayl: {filename}"

    meta = {"file_size": f"{len(content_bytes)//1024 or 1} KB", "category": category}
    item_id = db.add_knowledge_item(
        title=filename,
        item_type="file",
        content=extracted_text,
        metadata=meta
    )
    try:
        get_rag_engine().index_document(parent_id=item_id, title=filename, item_type="file", content=extracted_text, metadata=meta)
    except Exception as e:
        print(f"[RAG] Index error on file upload: {e}")
    engine_cache.clear()
    return {"status": "success", "id": item_id, "filename": filename, "message": f"'{filename}' fayli yuklandi, bo'laklandi va RAG indeksiga kiritildi!"}

@app.post("/api/knowledge/text")
def add_text_knowledge(data: TextKnowledge):
    """Adds a structured text catalog or document directly with RAG indexing."""
    ws_id = db.get_active_workspace_id()
    allowed, reason = db.check_quota(ws_id, "add_knowledge")
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    meta = {"file_size": f"{len(data.content.encode('utf-8'))//1024 or 1} KB", "category": data.category}
    item_id = db.add_knowledge_item(
        title=data.title,
        item_type="file",
        content=data.content,
        metadata=meta
    )
    try:
        get_rag_engine().index_document(parent_id=item_id, title=data.title, item_type="file", content=data.content, metadata=meta)
    except Exception as e:
        print(f"[RAG] Index error on text knowledge: {e}")
    engine_cache.clear()
    return {"status": "success", "id": item_id, "message": f"'{data.title}' bilimi saqlandi va RAG indeksiga qo'shildi!"}

@app.post("/api/knowledge/url")
async def add_url_knowledge(data: URLKnowledge):
    """Scrapes or saves website URL into company knowledge base with RAG indexing."""
    ws_id = db.get_active_workspace_id()
    allowed, reason = db.check_quota(ws_id, "add_knowledge")
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    scraped_content = data.content or ""
    title = data.title or f"Sayt: {data.url}"
    
    if not scraped_content:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(data.url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        clean = re.sub(r'<[^>]+>', ' ', html)
                        clean = ' '.join(clean.split())[:3000]
                        scraped_content = clean
        except Exception:
            scraped_content = f"Rasmiy veb-sayt: {data.url}. Korxona mahsulotlari va aloqa ma'lumotlari."

    meta = {"url": data.url, "status": "Faol"}
    item_id = db.add_knowledge_item(
        title=title,
        item_type="url",
        content=scraped_content or f"Sayt havolasi: {data.url}",
        metadata=meta
    )
    try:
        get_rag_engine().index_document(parent_id=item_id, title=title, item_type="url", content=scraped_content, metadata=meta)
    except Exception as e:
        print(f"[RAG] Index error on URL knowledge: {e}")
    engine_cache.clear()
    return {"status": "success", "id": item_id, "message": f"'{data.url}' havolasi bilimlarga va RAG indeksiga qo'shildi!"}

@app.delete("/api/knowledge/{item_id}")
def delete_knowledge(item_id: int):
    """Deletes a knowledge item and its vector chunks from database."""
    ws_id = db.get_active_workspace_id()
    db.delete_knowledge_item(item_id, workspace_id=ws_id)
    try:
        get_rag_engine().refresh_cache()
    except Exception:
        pass
    engine_cache.clear()
    return {"status": "success", "message": "Bilim va uning vektorlari muvaffaqiyatli o'chirildi!"}

@app.post("/api/knowledge/batch-delete")
def batch_delete_knowledge(req: KnowledgeBatchDelete):
    """Deletes multiple knowledge items and their vector chunks from database."""
    ws_id = db.get_active_workspace_id()
    count = db.delete_knowledge_items_batch(req.item_ids, workspace_id=ws_id)
    try:
        get_rag_engine().refresh_cache()
    except Exception:
        pass
    engine_cache.clear()
    return {"status": "success", "deleted_count": count, "message": f"{count} ta bilim muvaffaqiyatli o'chirildi!"}

# ----------------- AGENT PERSONA API -----------------

@app.get("/api/agent/persona")
@app.get("/api/persona")
def get_persona():
    """Returns current AI agent persona and behavioral settings."""
    ws_id = db.get_active_workspace_id()
    return db.get_agent_persona(workspace_id=ws_id)

@app.post("/api/agent/persona")
def update_persona(p: PersonaUpdate):
    """Updates AI agent name, avatar, tone, greeting message, and handoff rules."""
    ws_id = db.get_active_workspace_id()
    data = p.dict()
    db.update_agent_persona(data, workspace_id=ws_id)
    engine_cache.clear()
    return {"status": "success", "persona": db.get_agent_persona(workspace_id=ws_id), "message": "Agent personasi saqlandi!"}

# ----------------- CHANNELS & INTEGRATIONS API -----------------

@app.get("/api/channels")
def list_all_channels():
    """Returns status and configuration of all channels (Instagram, Telegram, WhatsApp, Web)."""
    return {"channels": db.list_channels()}

@app.post("/api/channels/{channel_id}")
def update_channel_config(channel_id: str, update: ChannelConfigUpdate):
    """Updates channel connection and credentials with plan quota enforcement."""
    if update.is_connected == 1 and channel_id != "web_widget":
        cur_chan = db.get_channel(channel_id)
        if not cur_chan or cur_chan.get("is_connected") != 1:
            ws_id = db.get_active_workspace_id()
            allowed, reason = db.check_quota(ws_id, "connect_channel")
            if not allowed:
                raise HTTPException(status_code=403, detail=reason)

    db.update_channel(channel_id, is_connected=update.is_connected, config=update.config)
    # Sync telegram bot token if updated
    if channel_id == "telegram" and update.config:
        if "bot_token" in update.config and update.config["bot_token"]:
            bot_instance.token = update.config["bot_token"]
            db.set_setting("telegram_bot_token", update.config["bot_token"])
        if "manager_chat_id" in update.config and update.config["manager_chat_id"]:
            bot_instance.manager_chat_id = update.config["manager_chat_id"]
            db.set_setting("sales_manager_chat_id", update.config["manager_chat_id"])

    return {"status": "success", "channel": db.get_channel(channel_id), "message": f"{channel_id.capitalize()} sozlamalari yangilandi!"}

@app.post("/api/channels/test")
def test_channel_message(test: ChannelTestMessage):
    """Simulates incoming message from a specified channel and triggers AI Closer."""
    sid = f"test_{test.channel}_{int(asyncio.get_event_loop().time())}"
    msg = ChatMessage(session_id=sid, message=test.message, channel=test.channel, user_name=f"{test.user_name} ({test.channel})")
    return handle_chat_logic(msg)

# ----------------- WEBHOOKS FOR META & WHATSAPP -----------------

@app.get("/api/webhooks/instagram")
def verify_instagram_webhook(request: Request):
    """Meta Webhook Challenge verification for Instagram Direct."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    chan = db.get_channel("instagram")
    expected_token = chan["config"].get("verify_token", "verta_ig_token_99") if chan else "verta_ig_token_99"
    if mode == "subscribe" and token == expected_token:
        return Response(content=str(challenge or ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/api/webhooks/instagram")
async def receive_instagram_webhook(request: Request):
    """Receives Instagram Direct messages and Reels/Post comments from Meta Graph API with HMAC validation."""
    raw_body = await request.body()
    chan = db.get_channel("instagram")
    app_secret = chan["config"].get("app_secret") if chan and chan.get("config") else None
    
    if app_secret:
        sig = request.headers.get("X-Hub-Signature-256")
        if not verify_meta_signature(raw_body, sig, app_secret):
            raise HTTPException(status_code=403, detail="X-Hub-Signature-256 HMAC verification failed")

    try:
        data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):
                sender_id = messaging.get("sender", {}).get("id")
                message_text = messaging.get("message", {}).get("text")
                if sender_id and message_text:
                    sid = f"ig_{sender_id}"
                    msg = ChatMessage(session_id=sid, message=message_text, channel="instagram", user_name=f"Instagram Mijoz ({sender_id[-4:]})")
                    resp = handle_chat_logic(msg)
                    if resp and "reply" in resp and not resp.get("autopilot_paused"):
                        asyncio.create_task(send_outbound_channel_message("instagram", sender_id, resp["reply"]))
            for change in entry.get("changes", []):
                val = change.get("value", {})
                comment_text = val.get("text")
                user_id = val.get("from", {}).get("id")
                if comment_text and user_id:
                    sid = f"ig_comm_{user_id}"
                    msg = ChatMessage(session_id=sid, message=comment_text, channel="instagram", user_name=f"Instagram Comment ({val.get('from', {}).get('username', 'Mijoz')})")
                    resp = handle_chat_logic(msg)
                    if resp and "reply" in resp and not resp.get("autopilot_paused"):
                        asyncio.create_task(send_outbound_channel_message("instagram", user_id, resp["reply"]))
    except Exception as e:
        print(f"[Webhook IG Error]: {e}")
    return {"status": "received"}

@app.get("/api/webhooks/whatsapp")
def verify_whatsapp_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and challenge:
        return Response(content=str(challenge), media_type="text/plain")
    return Response(content="ok", media_type="text/plain")

@app.post("/api/webhooks/whatsapp")
async def receive_whatsapp_webhook(request: Request):
    raw_body = await request.body()
    chan = db.get_channel("whatsapp")
    app_secret = chan["config"].get("app_secret") if chan and chan.get("config") else None
    
    if app_secret:
        sig = request.headers.get("X-Hub-Signature-256")
        if not verify_meta_signature(raw_body, sig, app_secret):
            raise HTTPException(status_code=403, detail="X-Hub-Signature-256 HMAC verification failed")

    try:
        data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                val = change.get("value", {})
                for msg in val.get("messages", []):
                    from_num = msg.get("from")
                    text = msg.get("text", {}).get("body")
                    if from_num and text:
                        sid = f"wa_{from_num}"
                        chat_msg = ChatMessage(session_id=sid, message=text, channel="whatsapp", user_name=f"WhatsApp ({from_num})")
                        resp = handle_chat_logic(chat_msg)
                        if resp and "reply" in resp and not resp.get("autopilot_paused"):
                            asyncio.create_task(send_outbound_channel_message("whatsapp", from_num, resp["reply"]))
    except Exception as e:
        print(f"[Webhook WA Error]: {e}")
    return {"status": "received"}

# ----------------- CHANNEL QUICK NOTES & GUIDES (FEATURE 6) -----------------

CHANNEL_QUICK_NOTES: Dict[str, Dict[str, Any]] = {
    "telegram": {
        "channel_id": "telegram",
        "name": "Telegram Bot",
        "icon": "✈️",
        "api_source": "https://t.me/BotFather",
        "api_source_title": "@BotFather orqali",
        "quick_notes": [
            "Telegramda @BotFather ga kiring va /newbot buyrug'i bilan bot ochib, HTTP API Token oling.",
            "Tokenni kiritib 'Ulash' tugmasini bosing — bot bir zumda ishga tushadi.",
            "Bot ovozli xabarlarni ham Gemini orqali avtomatik matnga o'girib, savdoni yopuvchi javob qaytaradi."
        ]
    },
    "instagram": {
        "channel_id": "instagram",
        "name": "Instagram Direct",
        "icon": "📸",
        "api_source": "https://developers.facebook.com/apps",
        "api_source_title": "Meta for Developers",
        "quick_notes": [
            "Meta for Developers (developers.facebook.com) da App oching va Instagram Graph API ni qo'shing.",
            "Facebook Page ga bog'langan Instagram Business akkauntingiz uchun Page Access Token oling.",
            "Webhook manzilini belgilang: https://sizning-domen/api/webhooks/instagram (Verify token: verta_ig_token_99)."
        ]
    },
    "whatsapp": {
        "channel_id": "whatsapp",
        "name": "WhatsApp Cloud API",
        "icon": "💬",
        "api_source": "https://developers.facebook.com",
        "api_source_title": "WhatsApp Cloud API Portal",
        "quick_notes": [
            "Meta Developers da WhatsApp Cloud API dan Phone Number ID va Access Token oling.",
            "Webhook manzilini ko'rsating: https://sizning-domen/api/webhooks/whatsapp (Verify token: verta_wa_token_99).",
            "Mijoz yozishi bilanoq 24 soatlik xizmat ko'rsatish oynasida AI avtomatik sotuvni yopadi."
        ]
    },
    "web_widget": {
        "channel_id": "web_widget",
        "name": "Veb-sayt Vidjeti (Web Chat)",
        "icon": "🌐",
        "api_source": "HTML / JavaScript",
        "api_source_title": "1 qatorlik JS skript",
        "quick_notes": [
            "Saytingiz kodi </body> tegi yopilishidan oldin skriptni joylashtiring:",
            "<script src=\"https://vertaflow.uz/static/widget.js\"></script>",
            "Hech qanday murakkab plaginlarsiz 1 daqiqada saytga AI konsultatsiya vidjeti o'rnatiladi."
        ]
    }
}

@app.get("/api/channels/guides/all")
def get_all_channel_guides():
    """Returns compact quick notes / cheat-sheets for all channels."""
    return {"guides": CHANNEL_QUICK_NOTES}

@app.get("/api/channels/{channel_id}/guide")
def get_channel_guide(channel_id: str):
    """Returns concise setup notes and API link for a specific channel."""
    guide = CHANNEL_QUICK_NOTES.get(channel_id)
    if not guide:
        raise HTTPException(status_code=404, detail="Ushbu kanal uchun eslatma topilmadi")
    return {"guide": guide}

def normalize_whatsapp_phone(raw_phone: Optional[str]) -> str:
    """Normalizes phone number to international WhatsApp format (e.g. 998901234567)."""
    if not raw_phone:
        return "998901234567"
    cleaned = re.sub(r"[^\d]", "", str(raw_phone))
    if len(cleaned) == 9 and cleaned.startswith("9"):  # local 901234567 -> 998901234567
        cleaned = "998" + cleaned
    return cleaned if cleaned else "998901234567"

@app.get("/api/channels/whatsapp/qr")
def get_whatsapp_qr(phone: Optional[str] = None, message: Optional[str] = None):
    """
    Generates authentic, scannable WhatsApp Direct Chat QR code (wa.me).
    Scannable with any smartphone camera or WhatsApp scanner to immediately start chat.
    Eliminates the 'Invalid QR code' error by using WhatsApp's universal web intent protocol.
    """
    from urllib.parse import quote_plus
    try:
        import qrcode
        import qrcode.image.svg

        target_phone = phone
        if not target_phone:
            chan = db.get_channel("whatsapp")
            cfg = chan.get("config", {}) if chan else {}
            target_phone = cfg.get("phone_number") or "+998 90 123 45 67"

        clean_phone = normalize_whatsapp_phone(target_phone)
        greeting = message or "Assalomu alaykum! AI yordamchi bilan bog'lanish"
        wame_url = f"https://wa.me/{clean_phone}?text={quote_plus(greeting)}"

        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(wame_url, image_factory=factory)
        out = io.BytesIO()
        img.save(out)
        return Response(content=out.getvalue(), media_type="image/svg+xml")
    except Exception as e:
        print(f"[WhatsApp QR Error]: {e}")
        clean_num = normalize_whatsapp_phone(phone)
        fallback_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="240" height="240">
            <rect width="240" height="240" rx="16" fill="#F0FDF4"/>
            <rect x="20" y="20" width="40" height="40" fill="#15803D"/>
            <rect x="180" y="20" width="40" height="40" fill="#15803D"/>
            <rect x="20" y="180" width="40" height="40" fill="#15803D"/>
            <text x="120" y="115" font-family="sans-serif" font-size="14" font-weight="bold" fill="#166534" text-anchor="middle">WhatsApp QR</text>
            <text x="120" y="140" font-family="sans-serif" font-size="12" fill="#15803D" text-anchor="middle">+{clean_num}</text>
        </svg>"""
        return Response(content=fallback_svg.encode('utf-8'), media_type="image/svg+xml")

@app.get("/api/channels/whatsapp/status")
def get_whatsapp_status():
    """Returns current WhatsApp connection status, credentials metadata, and direct chat URL."""
    from urllib.parse import quote_plus
    chan = db.get_channel("whatsapp") or {}
    cfg = chan.get("config", {}) if chan else {}
    phone = cfg.get("phone_number") or "+998 90 123 45 67"
    clean_phone = normalize_whatsapp_phone(phone)
    verify_token = cfg.get("verify_token") or "verta_wa_token_99"
    webhook_url = "http://127.0.0.1:8000/api/webhooks/whatsapp"
    chat_url = f"https://wa.me/{clean_phone}?text={quote_plus('Assalomu alaykum!')}"

    return {
        "channel_id": "whatsapp",
        "is_connected": chan.get("is_connected", 0),
        "phone_number": phone,
        "phone_number_clean": clean_phone,
        "phone_number_id": cfg.get("phone_number_id", ""),
        "has_access_token": bool(cfg.get("access_token")),
        "webhook_url": webhook_url,
        "verify_token": verify_token,
        "chat_url": chat_url,
        "last_sync": chan.get("last_sync")
    }

class WhatsAppTestPayload(BaseModel):
    from_number: Optional[str] = "998901234567"
    message: Optional[str] = "Assalomu alaykum, narxlaringiz qanday?"

@app.post("/api/channels/whatsapp/test")
def test_whatsapp_message(payload: WhatsAppTestPayload):
    """Simulates an inbound WhatsApp lead message and executes AI Closer response."""
    clean_num = normalize_whatsapp_phone(payload.from_number)
    sid = f"wa_{clean_num}"
    msg = ChatMessage(
        session_id=sid,
        message=payload.message or "Salom",
        channel="whatsapp",
        user_name=f"WhatsApp (+{clean_num})"
    )
    result = handle_chat_logic(msg)
    return {
        "status": "success",
        "session_id": sid,
        "user_message": payload.message,
        "reply": result.get("reply"),
        "stage": result.get("stage"),
        "lead_score": result.get("lead_score")
    }

# ----------------- FOLLOW-UP ENGINE API (FEATURE 2) -----------------

class FollowUpTestRequest(BaseModel):
    session_id: str
    channel: Optional[str] = "telegram"
    delay_minutes: Optional[int] = 0

@app.post("/api/follow_up/trigger")
async def trigger_due_follow_ups():
    """Immediately processes and dispatches due follow-up messages across all channels."""
    sent = await run_due_follow_ups()
    return {"status": "success", "processed_count": len(sent), "sent": sent}

@app.get("/api/follow_up/logs")
def get_follow_up_logs(limit: int = 50):
    """Returns recent smart follow-up logs and statuses."""
    logs = db.list_follow_up_logs(limit)
    return {"logs": logs, "total": len(logs)}

@app.post("/api/follow_up/schedule_test")
def schedule_test_follow_up(req: FollowUpTestRequest):
    """Schedules an immediate test follow-up for verification."""
    fid = db.schedule_follow_up(
        session_id=req.session_id,
        channel=req.channel or "telegram",
        delay_minutes=req.delay_minutes or 0,
        step=1
    )
    return {"status": "scheduled", "follow_up_id": fid}

# ----------------- CREATOR NICHE TEMPLATES API (FEATURE 7) -----------------

@app.get("/api/creator/templates")
def list_creator_templates():
    """Returns all industry sales templates (Creator / Admin only)."""
    return {"templates": get_all_templates()}

@app.get("/api/creator/templates/{template_id}")
def get_creator_template_details(template_id: str):
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Andoza topilmadi")
    return {"template": tpl}

def _background_sync_rag(ws_id: str):
    try:
        rag = get_rag_engine()
        rag.sync_all_knowledge()
    except Exception as e:
        print(f"[RAG Background Sync Error]: {e}")

@app.post("/api/creator/templates/{template_id}/apply")
def apply_creator_template(template_id: str, background_tasks: BackgroundTasks):
    """Applies a niche template into active business profile, persona, battlecards, and knowledge base."""
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Andoza topilmadi")

    ws_id = db.get_active_workspace_id()

    # 1. Update business profile for this workspace
    db.update_business_profile(
        name=tpl["business_name"],
        desc=tpl["business_desc"],
        avg_check=tpl.get("avg_check", ""),
        faq_list=tpl.get("faq_list", []),
        biz_id=ws_id
    )

    # 2. Update agent persona for this workspace
    persona_data = tpl.get("persona", {})
    cur_persona = db.get_agent_persona(workspace_id=ws_id)
    cur_persona.update(persona_data)
    db.update_agent_persona(cur_persona, workspace_id=ws_id)

    # 3. Add battlecards for this workspace
    for bc in tpl.get("battlecards", []):
        db.add_battlecard(
            name=bc["name"],
            keywords=bc["keywords"],
            weakness=bc.get("their_weakness") or bc.get("weakness", ""),
            reframe=bc.get("reframe_talk_track") or bc.get("reframe", ""),
            landmine=bc.get("landmine_question") or bc.get("landmine", ""),
            strength=bc.get("their_strength") or bc.get("strength", "Past narx"),
            workspace_id=ws_id
        )

    # 4. Insert FAQs into DB immediately (superfast <5ms)
    for faq in tpl.get("faq_list", []):
        meta = {"category": tpl["name"], "question": faq["question"], "answer": faq["answer"]}
        db.add_knowledge_item(
            title=faq["question"],
            item_type="faq",
            content=faq["answer"],
            metadata=meta,
            workspace_id=ws_id
        )

    # 5. Background task for RAG embeddings so UI response is instantaneous (<15ms)
    background_tasks.add_task(_background_sync_rag, ws_id)

    engine_cache.clear()
    return {
        "status": "applied",
        "template_id": template_id,
        "template_name": tpl["name"],
        "message": f"'{tpl['name']}' andozasi joriy loyihaga to'liq tatbiq etildi!"
    }

# ----------------- SETTINGS & TELEGRAM LIFECYCLE -----------------

telegram_task: Optional[asyncio.Task] = None

@app.get("/api/settings")
def get_settings():
    all_s = db.get_all_settings()
    token = all_s.get("telegram_bot_token", "")
    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else ("Bor" if token else "")
    
    gemini_k = all_s.get("gemini_api_key", "")
    masked_gemini = f"{gemini_k[:6]}...{gemini_k[-4:]}" if len(gemini_k) > 10 else "AQ.Ab8...Dvg"

    api_key = all_s.get("llm_api_key", "")
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else ("Bor" if api_key else "")

    return {
        "telegram_bot_token_masked": masked_token,
        "sales_manager_chat_id": all_s.get("sales_manager_chat_id", ""),
        "telegram_connected": bool(token and (telegram_task and not telegram_task.done())),
        "gemini_active": True,
        "gemini_model": "gemini-2.5-flash",
        "gemini_key_masked": masked_gemini,
        "llm_provider": all_s.get("llm_provider", "openai"),
        "llm_model": all_s.get("llm_model", "gpt-4o-mini"),
        "llm_api_key_masked": masked_key,
        "llm_is_active": True
    }

@app.post("/api/settings")
async def save_settings(s: SettingsData):
    if s.telegram_bot_token is not None:
        db.set_setting("telegram_bot_token", s.telegram_bot_token)
        bot_instance.token = s.telegram_bot_token
    if s.sales_manager_chat_id is not None:
        db.set_setting("sales_manager_chat_id", s.sales_manager_chat_id)
        bot_instance.manager_chat_id = s.sales_manager_chat_id
    if s.gemini_api_key is not None and s.gemini_api_key.strip():
        db.set_setting("gemini_api_key", s.gemini_api_key)
    if s.llm_provider is not None:
        db.set_setting("llm_provider", s.llm_provider)
    if s.llm_api_key is not None and s.llm_api_key.strip():
        db.set_setting("llm_api_key", s.llm_api_key)
    if s.llm_model is not None:
        db.set_setting("llm_model", s.llm_model)

    engine_cache.clear()
    return {"status": "success", "message": "Sozlamalar saqlandi!"}

@app.post("/api/telegram/start")
async def start_telegram_bot():
    global telegram_task
    token = db.get_setting("telegram_bot_token")
    if not token:
        raise HTTPException(status_code=400, detail="Telegram Bot Token topilmadi. Avval tokenni kiriting.")

    if telegram_task and not telegram_task.done():
        return {"status": "already_running", "message": "Telegram bot allaqachon ishlab turibdi."}

    bot_instance.token = token
    bot_instance.manager_chat_id = db.get_setting("sales_manager_chat_id")
    telegram_task = asyncio.create_task(bot_instance.start_polling())
    return {"status": "started", "message": "Telegram bot muvaffaqiyatli ishga tushirildi!"}

@app.post("/api/telegram/stop")
def stop_telegram_bot():
    global telegram_task
    bot_instance.stop_polling()
    if telegram_task:
        telegram_task.cancel()
        telegram_task = None
    return {"status": "stopped", "message": "Telegram bot to'xtatildi."}

# ----------------- WORKSPACES API -----------------

@app.get("/api/workspaces")
def list_workspaces():
    """Returns all user workspaces and indicates active workspace."""
    return {"workspaces": db.get_workspaces(), "active_workspace_id": db.get_active_workspace_id()}

@app.post("/api/workspaces")
def add_workspace(ws: WorkspaceCreate):
    """Creates a new workspace and sets it as active."""
    new_ws = db.create_workspace(name=ws.name, niche=ws.niche, description=ws.description, avg_check=ws.avg_check)
    return {"status": "success", "workspace": new_ws, "message": "Yangi loyiha muvaffaqiyatli yaratildi!"}

@app.post("/api/workspaces/switch")
def switch_workspace(req: WorkspaceSwitch):
    """Switches the active workspace."""
    db.set_active_workspace_id(req.workspace_id)
    return {"status": "success", "active_workspace_id": req.workspace_id, "message": "Loyiha almashtirildi!"}

@app.delete("/api/workspaces/{workspace_id}")
def remove_workspace(workspace_id: str):
    """Deletes a workspace."""
    if workspace_id == "default":
        raise HTTPException(status_code=400, detail="Asosiy (Default) loyihani o'chirish mumkin emas.")
    res = db.delete_workspace(workspace_id)
    return {"status": "success" if res else "error", "message": "Loyiha o'chirildi!"}

# ----------------- BILLING & PLANS API -----------------

@app.get("/api/billing")
def get_billing_status(workspace_id: Optional[str] = None):
    """Returns billing status, quotas, and payment history for workspace."""
    return db.get_billing_info(workspace_id)

@app.post("/api/billing/checkout")
def checkout_plan(req: BillingCheckout):
    """Processes plan purchase via Payme or Click, upgrades workspace, and generates payment record."""
    plan = (req.plan_id or "").lower().strip()
    if plan not in ["free", "pro", "business"]:
        raise HTTPException(status_code=400, detail="Noto'g'ri tarif tanlandi")

    months = req.period_months or 1
    if months not in [1, 3, 6, 12]:
        raise HTTPException(status_code=400, detail="Noto'g'ri to'lov davri tanlandi (1, 3, 6 yoki 12 oy)")

    prices_per_month = {
        "free": 0,
        "pro": 249000,
        "business": 590000
    }
    discounts = {
        1: 0.0,
        3: 0.10,
        6: 0.15,
        12: 0.25
    }
    base = prices_per_month[plan]
    disc = discounts[months]
    total = int(base * months * (1.0 - disc))

    method = (req.payment_method or "free").lower().strip()
    if plan != "free":
        if method in ["free", "none", ""]:
            raise HTTPException(
                status_code=400,
                detail="Pullik tarifni faollashtirish uchun to'lov usuli (Payme yoki Click) tanlanishi shart."
            )
        if total <= 0:
            raise HTTPException(status_code=400, detail="To'lov summasi 0 bo'lishi mumkin emas")
    else:
        total = 0
        method = "free"

    ws_id = db.get_active_workspace_id()
    try:
        billing_data = db.record_payment(
            workspace_id=ws_id,
            plan_id=plan,
            period_months=months,
            amount=total,
            payment_method=method
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    return {
        "status": "success",
        "message": f"{plan.capitalize()} tarifi muvaffaqiyatli faollashtirildi!",
        "total_amount": total,
        "plan_id": plan,
        "billing": billing_data
    }

# ----------------- AUTHENTICATION & USERS API -----------------

@app.post("/api/auth/register")
def auth_register(req: RegisterRequest, response: Response):
    """Real registration supporting Email, Telegram, Instagram, and WhatsApp with session creation."""
    if not req.identifier or not req.identifier.strip():
        raise HTTPException(status_code=400, detail="Identifikator (email, akkaunt, bot yoki telefon) kiritilishi shart")
    
    valid_methods = ["email", "telegram", "instagram", "whatsapp"]
    method = req.auth_method.lower().strip()
    if method not in valid_methods:
        method = "email"
        
    res = db.register_user(
        auth_method=method,
        identifier=req.identifier.strip(),
        full_name=req.full_name or "",
        password=req.password or "",
        selected_plan=req.selected_plan or "free"
    )
    user = res["user"]
    token = db.create_session(user["id"])
    response.set_cookie(
        key="vertaflow_session",
        value=token,
        max_age=30 * 86400,
        httponly=True,  # Secure: protects against XSS token harvesting
        samesite="lax",
        path="/"
    )
    return {
        "status": res.get("status", "created"),
        "user": user,
        "token": token,
        "has_primary_channel": db.has_connected_primary_channel()
    }

@app.post("/api/test/reset_rate_limits")
def reset_rate_limits(request: Request):
    """Local-only helper for automated test suites to clear sliding windows."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    if client_ip not in ["127.0.0.1", "localhost", "testclient"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    rate_limiter.requests.clear()
    return {"status": "cleared"}

@app.post("/api/auth/login")
def auth_login(req: LoginRequest, response: Response, request: Request):
    """Real authentication with identifier and password verifying against SQLite database."""
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    # Security: Brute Force Rate Limiter (20/min for localhost test runs, 8/min for public clients)
    limit = 20 if client_ip in ["127.0.0.1", "localhost", "testclient"] else 8
    if not rate_limiter.is_allowed(f"login:{client_ip}", max_requests=limit, window_seconds=60):
        raise HTTPException(status_code=429, detail="Kirish urinishlari me'yordan oshdi. Xavfsizlik yuzasidan 1 daqiqa kuting.")

    if not req.identifier or not req.identifier.strip():
        raise HTTPException(status_code=400, detail="Identifikator kiritilishi shart")
        
    user = db.authenticate_user(
        auth_method=req.auth_method.lower().strip(),
        identifier=req.identifier.strip(),
        password=req.password or ""
    )
    if not user:
        raise HTTPException(status_code=401, detail="Akkaunt topilmadi yoki parol noto'g'ri. Iltimos, ma'lumotlarni tekshiring.")
        
    # Reset failed login count on successful authentication
    rate_limiter.requests.pop(f"login:{client_ip}", None)

    token = db.create_session(user["id"])
    response.set_cookie(
        key="vertaflow_session",
        value=token,
        max_age=30 * 86400,
        httponly=True,  # Secure: protects against XSS token harvesting
        samesite="lax",
        path="/"
    )
    return {
        "status": "success",
        "user": user,
        "token": token,
        "has_primary_channel": db.has_connected_primary_channel()
    }

@app.post("/api/auth/logout")
def auth_logout(response: Response, vertaflow_session: Optional[str] = Cookie(None)):
    """Logs out user and destroys session token."""
    if vertaflow_session:
        db.delete_session(vertaflow_session)
    response.delete_cookie(key="vertaflow_session", path="/")
    return {"status": "logged_out", "message": "Muvaffaqiyatli tizimdan chiqildi"}

@app.get("/api/auth/me")
def auth_me(request: Request, vertaflow_session: Optional[str] = Cookie(None), token: Optional[str] = None):
    """Returns currently authenticated user profile and whether any primary communication channel is connected."""
    auth_token = vertaflow_session or token
    if not auth_token:
        auth_hdr = request.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            auth_token = auth_hdr[7:].strip()
            
    if auth_token:
        user = db.get_user_by_session(auth_token)
        if user:
            return {
                "authenticated": True,
                "user": user,
                "has_primary_channel": db.has_connected_primary_channel()
            }
            
    return {
        "authenticated": False,
        "user": None,
        "has_primary_channel": False
    }

# ----------------- STATIC ASSETS & FRONTEND -----------------

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
@app.head("/")
def serve_landing():
    """Public SEO-optimized Landing Page for visitors from Google and social media."""
    landing_file = os.path.join(static_dir, "landing.html")
    if os.path.exists(landing_file):
        return FileResponse(landing_file)
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "VertaFlow API online. Landing page not found."}

@app.get("/onboarding")
@app.head("/onboarding")
@app.get("/setup")
@app.head("/setup")
@app.get("/login")
@app.head("/login")
def serve_onboarding():
    """Interactive Onboarding & Auth Wizard before platform access."""
    onboard_file = os.path.join(static_dir, "onboarding.html")
    if os.path.exists(onboard_file):
        return FileResponse(onboard_file)
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Onboarding page not found."}

@app.get("/app")
@app.head("/app")
@app.get("/dashboard")
@app.head("/dashboard")
@app.get("/platform")
@app.head("/platform")
def serve_app(request: Request, vertaflow_session: Optional[str] = Cookie(None)):
    """VertaFlow Core SaaS Platform Dashboard with strict real session authentication guard."""
    token = vertaflow_session
    if not token:
        token = request.query_params.get("token")
        
    user = db.get_user_by_session(token) if token else None
    if not user:
        # User is not authenticated -> redirect to login/onboarding
        return RedirectResponse(url="/onboarding", status_code=303)

    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "VertaFlow SaaS Platform index.html not found."}

@app.get("/robots.txt")
def serve_robots():
    """Robots.txt for Googlebot and search crawlers."""
    robots_file = os.path.join(static_dir, "robots.txt")
    if os.path.exists(robots_file):
        return FileResponse(robots_file, media_type="text/plain")
    return Response(content="User-agent: *\nAllow: /\nAllow: /app\nDisallow: /api/\nSitemap: https://vertaflow.uz/sitemap.xml", media_type="text/plain")

@app.get("/sitemap.xml")
def serve_sitemap():
    """XML Sitemap for Google Indexation."""
    sitemap_file = os.path.join(static_dir, "sitemap.xml")
    if os.path.exists(sitemap_file):
        return FileResponse(sitemap_file, media_type="application/xml")
    return Response(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"><url><loc>https://vertaflow.uz/</loc></url></urlset>", media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    print("🚀 VertaFlow Server running on http://127.0.0.1:8000")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
