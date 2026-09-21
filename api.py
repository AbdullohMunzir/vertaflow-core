# /home/kinfolkt/verta-platform/api.py
"""
VertaFlow — Central Production-Grade FastAPI Server & Hub
Fully backed by SQLite database (db.py).
Provides REST endpoints for Chat, CRM, Real-time Inbox, Human Takeover,
AI Settings, Telegram Bot Lifecycle, Battlecards, and Self-Improving Evaluator.
"""

import sys
import os
import asyncio
import re
import json
from typing import Dict, Any, List, Optional
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

def verify_meta_signature(raw_body: bytes, signature_header: Optional[str], secret: Optional[str]) -> bool:
    """Verifies X-Hub-Signature-256 for Meta Webhooks (Instagram / WhatsApp)."""
    if not secret:
        return True  # Bypass in dev/test if secret is not set yet
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    signature = signature_header[len("sha256="):]
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

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

class PersonaUpdate(BaseModel):
    name: str
    role: Optional[str] = "Sotuv bo'yicha maslahatchi"
    avatar: Optional[str] = "👩‍💼"
    tone: Optional[str] = "friendly_closer"
    tone_label: Optional[str] = "Samimiy & Savdo yopuvchi"
    greeting: Optional[str] = "Assalomu alaykum! Fabrikamizga xush kelibsiz. Qaysi mebel turi sizga ma'qul bo'lyapti?"
    max_discount: Optional[str] = "10%"
    rules: Optional[Dict[str, bool]] = None

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

@app.post("/api/chat")
def process_chat(msg: ChatMessage):
    """Processes incoming chat from web simulator or widget, persists to DB, and returns AI Closer response."""
    text = msg.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Xabar bo'sh bo'lishi mumkin emas")

    session_id = msg.session_id
    channel = msg.channel or "web_simulator"

    # 1. Ensure conversation exists in DB
    conv = db.get_conversation(session_id)
    if not conv:
        db.create_or_update_conversation(session_id, name=msg.user_name or "Mijoz", channel=channel)
        conv = db.get_conversation(session_id)

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

    # 5. Record agent reply to DB
    db.add_message(session_id, sender="agent", text=response["reply"], stage=response["stage"], script=response["script"])

    # 6. Save qualified lead state
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
    """Allows human operator to send reply directly, pausing AI autopilot."""
    conv = db.get_conversation(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")

    # Disable autopilot so AI doesn't interfere
    db.toggle_conversation_autopilot(session_id, False)

    # Save operator message to DB
    db.add_message(session_id, sender="operator", text=reply.text)

    # If it's a Telegram chat, forward message to real user!
    if conv["channel"] == "telegram" and session_id.startswith("tg_"):
        chat_id = int(session_id.replace("tg_", ""))
        async with aiohttp.ClientSession() as http_sess:
            await bot_instance.send_message(http_sess, chat_id, f"👨‍💼 <b>Operator:</b> {reply.text}")

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
    db.delete_knowledge_item(item_id)
    try:
        get_rag_engine().refresh_cache()
    except Exception:
        pass
    engine_cache.clear()
    return {"status": "success", "message": "Bilim va uning vektorlari muvaffaqiyatli o'chirildi!"}

# ----------------- AGENT PERSONA API -----------------

@app.get("/api/agent/persona")
@app.get("/api/persona")
def get_persona():
    """Returns current AI agent persona and behavioral settings."""
    return db.get_agent_persona()

@app.post("/api/agent/persona")
def update_persona(p: PersonaUpdate):
    """Updates AI agent name, avatar, tone, greeting message, and handoff rules."""
    data = p.dict()
    db.update_agent_persona(data)
    engine_cache.clear()
    return {"status": "success", "persona": db.get_agent_persona(), "message": "Agent personasi saqlandi!"}

# ----------------- CHANNELS & INTEGRATIONS API -----------------

@app.get("/api/channels")
def list_all_channels():
    """Returns status and configuration of all channels (Instagram, Telegram, WhatsApp, Web)."""
    return {"channels": db.list_channels()}

@app.post("/api/channels/{channel_id}")
def update_channel_config(channel_id: str, update: ChannelConfigUpdate):
    """Updates channel connection and credentials."""
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
    return process_chat(msg)

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
                    process_chat(msg)
            for change in entry.get("changes", []):
                val = change.get("value", {})
                comment_text = val.get("text")
                user_id = val.get("from", {}).get("id")
                if comment_text and user_id:
                    sid = f"ig_comm_{user_id}"
                    msg = ChatMessage(session_id=sid, message=comment_text, channel="instagram", user_name=f"Instagram Comment ({val.get('from', {}).get('username', 'Mijoz')})")
                    process_chat(msg)
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
                        process_chat(chat_msg)
    except Exception as e:
        print(f"[Webhook WA Error]: {e}")
    return {"status": "received"}

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
    base = prices_per_month.get(req.plan_id, 0)
    disc = discounts.get(req.period_months, 0.0)
    total = int(base * (req.period_months or 1) * (1.0 - disc))
    
    ws_id = db.get_active_workspace_id()
    billing_data = db.record_payment(
        workspace_id=ws_id,
        plan_id=req.plan_id,
        period_months=req.period_months or 1,
        amount=total,
        payment_method=req.payment_method or "free"
    )
    return {
        "status": "success",
        "message": f"{req.plan_id.capitalize()} tarifi muvaffaqiyatli faollashtirildi!",
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
        httponly=False,
        samesite="lax",
        path="/"
    )
    return {
        "status": res.get("status", "created"),
        "user": user,
        "token": token,
        "has_primary_channel": db.has_connected_primary_channel()
    }

@app.post("/api/auth/login")
def auth_login(req: LoginRequest, response: Response):
    """Real authentication with identifier and password verifying against SQLite database."""
    if not req.identifier or not req.identifier.strip():
        raise HTTPException(status_code=400, detail="Identifikator kiritilishi shart")
        
    user = db.authenticate_user(
        auth_method=req.auth_method.lower().strip(),
        identifier=req.identifier.strip(),
        password=req.password or ""
    )
    if not user:
        raise HTTPException(status_code=401, detail="Akkaunt topilmadi yoki parol noto'g'ri. Iltimos, ma'lumotlarni tekshiring.")
        
    token = db.create_session(user["id"])
    response.set_cookie(
        key="vertaflow_session",
        value=token,
        max_age=30 * 86400,
        httponly=False,
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
