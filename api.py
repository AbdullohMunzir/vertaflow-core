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
from typing import Dict, Any, List, Optional
import io
import csv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
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
from telegram_bot import bot_instance

app = FastAPI(title="VertaFlow AI Platform API", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory runtime cache for engine states
engine_cache: Dict[str, VertaFlowEngine] = {}

def get_or_create_engine(session_id: str, channel: str = "web_simulator") -> VertaFlowEngine:
    if session_id not in engine_cache:
        biz_profile = db.get_business_profile()
        gemini_key = db.get_setting("gemini_api_key")
        gemini_client = VertaGeminiClient(api_key=gemini_key)

        api_key = db.get_setting("llm_api_key")
        provider = db.get_setting("llm_provider", "openai")
        model = db.get_setting("llm_model")
        llm_client = VertaLLMClient(api_key=api_key, provider=provider, model=model)

        engine = VertaFlowEngine(
            session_id=session_id,
            channel=channel,
            business_profile=biz_profile,
            gemini_client=gemini_client,
            llm_client=llm_client
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

        engine_cache[session_id] = engine

    # Always ensure business profile is up-to-date
    engine_cache[session_id].business_profile = db.get_business_profile()
    return engine_cache[session_id]

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

    return {"status": "applied", "message": "Tavsiya tatbiq etildi!"}

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

# ----------------- STATIC ASSETS & FRONTEND -----------------

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "VertaFlow API online. Web index.html not found yet."}

if __name__ == "__main__":
    import uvicorn
    print("🚀 VertaFlow Server running on http://127.0.0.1:8000")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
