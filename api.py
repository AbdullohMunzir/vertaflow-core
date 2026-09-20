# /home/kinfolkt/verta-platform/api.py
"""
VertaFlow — Central FastAPI Server & Omnichannel Hub
Exposes conversational sales engine, live lead scoring, onboarding,
self-improving evaluator, battlecard repository, and web UI.
"""

import sys
import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Add core engine to path
sys.path.append(os.path.join(os.path.dirname(__file__), "core"))
from verta_engine import VertaFlowEngine
from verta_battlecards import Battlecard, BattlecardEngine
from verta_evaluator import VertaEvaluator

app = FastAPI(title="VertaFlow AI Platform API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared Battlecard Engine instance
global_battlecards = BattlecardEngine()

# Telegram Configuration state
telegram_config = {
    "token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "manager_chat_id": os.getenv("SALES_MANAGER_CHAT_ID", ""),
    "is_connected": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
    "channel": "Telegram Bot"
}

# Global Business Onboarding Profile
business_profile = {
    "business_name": "Mebel Fabrikasi",
    "business_desc": "Oshxona va uy mebellari ishlab chiqarish",
    "avg_check": "5 000 000 so'm",
    "faq_list": [
        {"question": "Narxi qancha?", "answer": "Metri 2.5 mln dan boshlanadi, o'lchamga qarab hisoblanadi."},
        {"question": "Yetkazib berasizmi?", "answer": "Ha, butun Toshkent bo'ylab bepul yetkazib o'rnatamiz."},
        {"question": "Kafolat bormi?", "answer": "5 yil rasmiy kafolat beramiz."}
    ]
}

# In-memory session store: session_id -> VertaFlowEngine
sessions: Dict[str, VertaFlowEngine] = {}

def seed_sample_sessions():
    """Seeds realistic lead sessions for immediate dashboard visibility."""
    # 1. Hot lead (Kirill)
    s1 = VertaFlowEngine("sess_jamshid", channel="telegram")
    s1.process_message("Салом, мебел фабрикамиз учун нархи қанча?")
    s1.process_message("Кунига 30-40 та буюртма тушади, лекин сотувчиларимиз улгурмай мижозларни совитиб қўйяпти.")
    s1.process_message("Шу ҳафта ўрнатмоқчимиз. Мана рақамим +998901234567")
    sessions["sess_jamshid"] = s1

    # 2. Warm lead (Lotin)
    s2 = VertaFlowEngine("sess_anvar", channel="instagram")
    s2.process_message("Salom, o'quv markazimiz uchun bot kerak edi.")
    s2.process_message("Kuniga 15 ta o'quvchi yozadi, lekin ko'pi narxni bilib yo'qolib qoladi.")
    sessions["sess_anvar"] = s2

    # 3. Hot lead 2 (Lotin)
    s3 = VertaFlowEngine("sess_farhod", channel="web_widget")
    s3.process_message("Assalomu alaykum, ulgurji savdo do'konimizga tizim joriy qilmoqchimiz.")
    s3.process_message("Hozir 5 ta operatorimiz bor, mijozlarga kech javob berib ulgurmayapti.")
    s3.process_message("Tezroq joriy qilish kerak, telefonim 998977654321")
    sessions["sess_farhod"] = s3

    # 4. Cold lead
    s4 = VertaFlowEngine("sess_nigora", channel="telegram")
    s4.process_message("Salom, qimmat emasmi?")
    sessions["sess_nigora"] = s4

seed_sample_sessions()

def get_or_create_engine(session_id: str) -> VertaFlowEngine:
    if session_id not in sessions:
        engine = VertaFlowEngine(session_id=session_id)
        # Link shared battlecards
        engine.battlecards = global_battlecards
        sessions[session_id] = engine
    return sessions[session_id]

# Request models
class ChatMessage(BaseModel):
    session_id: str
    message: str

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

class RecommendationApply(BaseModel):
    id: str

class TelegramConfigData(BaseModel):
    token: str
    manager_chat_id: Optional[str] = ""

# Endpoints
@app.post("/api/chat")
def process_chat(msg: ChatMessage):
    if not msg.message.strip():
        raise HTTPException(status_code=400, detail="Xabar bo'sh bo'lishi mumkin emas")
    
    engine = get_or_create_engine(msg.session_id)
    response = engine.process_message(msg.message)
    return response

@app.get("/api/session/{session_id}")
def get_session_state(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    engine = sessions[session_id]
    return {
        "state": engine.state.to_dict(),
        "history": engine.state.history,
        "dossier": engine.state.generate_lead_dossier() if engine.state.lead_score >= 50 else None
    }

@app.get("/api/leads")
def list_leads():
    leads = []
    for sid, engine in sessions.items():
        state = engine.state
        name_hint = "Mijoz"
        if "jamshid" in sid:
            name_hint = "Jamshid aka"
        elif "anvar" in sid:
            name_hint = "Anvar Rasulov"
        elif "farhod" in sid:
            name_hint = "Farhod Aliyev"
        elif "nigora" in sid:
            name_hint = "Nigora Karimova"
        else:
            name_hint = f"Mijoz ({sid[-4:]})"

        leads.append({
            "session_id": sid,
            "name": name_hint,
            "channel": state.channel,
            "tier": state.lead_tier,
            "score": state.lead_score,
            "stage": state.current_stage.value,
            "script": state.script_preference,
            "phone": state.collected_attributes.get("phone"),
            "pain": state.collected_attributes.get("identified_pain"),
            "volume": state.collected_attributes.get("volume_or_size"),
            "timeline": state.collected_attributes.get("timeline"),
            "score_reasons": state.score_reasons,
            "dossier": state.generate_lead_dossier() if state.lead_score >= 50 else None
        })
    leads.sort(key=lambda x: x["score"], reverse=True)
    return {"leads": leads, "total_leads": len(leads)}

@app.get("/api/battlecards")
def get_battlecards():
    cards = []
    for bc in global_battlecards.battlecards:
        cards.append({
            "name": bc.name,
            "keywords": bc.keywords,
            "weakness": bc.their_weakness,
            "reframe": bc.reframe_talk_track,
            "landmine": bc.landmine_question
        })
    return {"battlecards": cards}

@app.post("/api/battlecards/add")
def add_battlecard(item: BattlecardItem):
    card = Battlecard(
        name=item.name,
        keywords=item.keywords,
        their_weakness=item.their_weakness,
        reframe_talk_track=item.reframe_talk_track,
        landmine_question=item.landmine_question
    )
    global_battlecards.battlecards.append(card)
    return {"status": "success", "message": f"'{item.name}' battlecardi muvaffaqiyatli qo'shildi!"}

@app.get("/api/evaluator/insights")
def get_evaluator_insights():
    evaluator = VertaEvaluator(sessions)
    report = evaluator.generate_audit_report()
    return report

@app.post("/api/evaluator/apply")
def apply_evaluator_recommendation(req: RecommendationApply):
    evaluator = VertaEvaluator(sessions)
    report = evaluator.generate_audit_report()
    recs = report.get("recommendations", [])
    
    target = None
    for r in recs:
        if r["id"] == req.id:
            target = r
            break
            
    if not target:
        raise HTTPException(status_code=404, detail="Tavsiya topilmadi")

    # Execute recommendation action
    if target["action_type"] == "add_battlecard":
        payload = target["action_payload"]
        bc = Battlecard(
            name=payload["competitor_name"],
            keywords=payload["keywords"],
            their_weakness=payload["weakness"],
            reframe_talk_track=payload["reframe"],
            landmine_question=payload["landmine"]
        )
        global_battlecards.battlecards.append(bc)
        return {"status": "applied", "message": f"'{payload['competitor_name']}' battlecardi qo'shildi!"}
    
    elif target["action_type"] == "add_faq":
        payload = target["action_payload"]
        business_profile["faq_list"].append(payload)
        return {"status": "applied", "message": f"Yangi FAQ bilimi muvaffaqiyatli qo'shildi!"}

    return {"status": "applied", "message": "Tavsiya amaliyotga tatbiq etildi!"}

@app.get("/api/telegram/status")
def get_telegram_status():
    return telegram_config

@app.post("/api/telegram/config")
def update_telegram_config(cfg: TelegramConfigData):
    global telegram_config
    telegram_config["token"] = cfg.token
    if cfg.manager_chat_id:
        telegram_config["manager_chat_id"] = cfg.manager_chat_id
    telegram_config["is_connected"] = bool(cfg.token.strip())
    return {"status": "updated", "config": telegram_config}

@app.post("/api/onboarding")
def save_onboarding(data: OnboardingData):
    global business_profile
    business_profile["business_name"] = data.business_name
    business_profile["business_desc"] = data.business_desc
    if data.avg_check:
        business_profile["avg_check"] = data.avg_check
    if data.faq_list:
        business_profile["faq_list"] = data.faq_list
    return {"status": "success", "profile": business_profile}

@app.get("/api/onboarding")
def get_onboarding():
    return business_profile

# Mount static files and frontend
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
