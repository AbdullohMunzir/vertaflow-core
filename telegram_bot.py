# /home/kinfolkt/verta-platform/telegram_bot.py
"""
VertaFlow — Telegram Omnichannel Connector
Synchronized with SQLite database (db.py).
Handles real-time Telegram incoming messages, routes them through VertaFlowEngine,
checks Autopilot status (Human Takeover), and dispatches instant Hot Lead Dossiers.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Optional, Any
import aiohttp

# Add core and root to path
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "core"))

import db
from verta_engine import VertaFlowEngine
from verta_llm import VertaLLMClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VertaTelegramBot")

BASE_TELEGRAM_URL = "https://api.telegram.org/bot"

class VertaTelegramBot:
    def __init__(self, token: Optional[str] = None, manager_chat_id: Optional[str] = None):
        self.token = token or db.get_setting("telegram_bot_token", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.manager_chat_id = manager_chat_id or db.get_setting("sales_manager_chat_id", "") or os.getenv("SALES_MANAGER_CHAT_ID", "")
        self.sessions: Dict[int, VertaFlowEngine] = {}
        self.is_running = False
        self.last_update_id = 0
        self.alerted_sessions = set()
        self._polling_task: Optional[asyncio.Task] = None

    def get_or_create_engine(self, chat_id: int) -> VertaFlowEngine:
        if chat_id not in self.sessions:
            biz_profile = db.get_business_profile()
            api_key = db.get_setting("llm_api_key")
            provider = db.get_setting("llm_provider", "openai")
            model = db.get_setting("llm_model")
            llm_client = VertaLLMClient(api_key=api_key, provider=provider, model=model)

            engine = VertaFlowEngine(
                session_id=f"tg_{chat_id}",
                channel="telegram",
                business_profile=biz_profile,
                llm_client=llm_client
            )
            self.sessions[chat_id] = engine
        return self.sessions[chat_id]

    async def send_message(self, session: aiohttp.ClientSession, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
        """Sends a text message to a specific Telegram chat."""
        if not self.token:
            logger.warning(f"[Mock Send] To: {chat_id} | Text: {text}")
            return True

        url = f"{BASE_TELEGRAM_URL}{self.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return True
                else:
                    err_body = await resp.text()
                    logger.error(f"Telegram send error {resp.status}: {err_body}")
                    return False
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return False

    async def notify_sales_manager(self, session: aiohttp.ClientSession, chat_id: int, engine: VertaFlowEngine):
        """Dispatches high-priority Lead Dossier to sales manager."""
        if chat_id in self.alerted_sessions:
            return

        self.alerted_sessions.add(chat_id)
        attrs = engine.state.collected_attributes
        score = engine.state.lead_score
        tier = engine.state.lead_tier

        manager_text = (
            f"🔥 <b>YANGI ISSIQ LID (HOT LEAD)!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Mijoz ID:</b> <code>tg_{chat_id}</code>\n"
            f"📞 <b>Telefon:</b> {attrs.get('phone') or 'Ko\'rsatilmagan'}\n"
            f"🎯 <b>Og'riq / Soha:</b> {attrs.get('identified_pain') or 'Aniqlanmoqda'}\n"
            f"📊 <b>Ball (Score):</b> <b>{score}/100 ({tier})</b>\n"
            f"⏱ <b>Xarid muddati:</b> {attrs.get('timeline') or 'Tez orada'}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <b>AI Tavsiyasi:</b> Xaridor tayyor! Operator chatga kirishi tavsiya etiladi."
        )

        target_manager = self.manager_chat_id or db.get_setting("sales_manager_chat_id")
        if target_manager:
            try:
                await self.send_message(session, int(target_manager), manager_text)
            except Exception as e:
                logger.error(f"Failed to notify sales manager: {e}")

    async def handle_update(self, session: aiohttp.ClientSession, update: Dict[str, Any]):
        """Processes a single Telegram update message (Text or Voice/Audio)."""
        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        user_name = message.get("from", {}).get("first_name", "Telegram Mijoz")
        session_id = f"tg_{chat_id}"

        text = ""
        # Check for voice note or audio message
        if "voice" in message or "audio" in message:
            audio_obj = message.get("voice") or message.get("audio")
            file_id = audio_obj.get("file_id") if audio_obj else None
            if file_id and self.token:
                try:
                    # 1. Get file path from Telegram API
                    get_file_url = f"{BASE_TELEGRAM_URL}{self.token}/getFile?file_id={file_id}"
                    async with session.get(get_file_url, timeout=aiohttp.ClientTimeout(total=10)) as gf_resp:
                        if gf_resp.status == 200:
                            gf_data = await gf_resp.json()
                            file_path = gf_data.get("result", {}).get("file_path")
                            if file_path:
                                # 2. Download audio file bytes
                                dl_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                                async with session.get(dl_url, timeout=aiohttp.ClientTimeout(total=15)) as dl_resp:
                                    if dl_resp.status == 200:
                                        audio_bytes = await dl_resp.read()
                                        # 3. Transcribe via Gemini Multimodal STT
                                        from verta_gemini import VertaGeminiClient
                                        gemini_client = VertaGeminiClient()
                                        mime = audio_obj.get("mime_type", "audio/ogg")
                                        transcribed = gemini_client.transcribe_audio(audio_bytes, mime_type=mime)
                                        if transcribed:
                                            text = transcribed
                                            logger.info(f"[Voice STT tg_{chat_id}]: {text}")
                except Exception as e:
                    logger.error(f"Error downloading/transcribing voice note: {e}")

            if not text:
                text = "Assalomu alaykum! Ovozli xabaringiz qabul qilindi, qanday mahsulotimiz haqida ma'lumot kerak edi?"
        elif "text" in message:
            text = message["text"].strip()
        else:
            return

        if not text:
            return

        # 1. Check or create conversation in SQLite database
        conv = db.get_conversation(session_id)
        if not conv:
            db.create_or_update_conversation(session_id, user_name, channel="telegram")
            conv = db.get_conversation(session_id)

        # 2. Record incoming message to DB
        db.add_message(session_id, sender="user", text=text)

        # Command handling
        if text.startswith("/start"):
            welcome_msg = (
                f"Assalomu alaykum, {user_name}! VertaFlow savdo tizimiga xush kelibsiz.\n"
                f"Sizga biznesingiz uchun eng ma'qul yechimni hisoblab berishimiz mumkin.\n"
                f"Hozirda korxonangizda qaysi mahsulot yoki xizmat sotuvini rivojlantirmoqchisiz?"
            )
            db.add_message(session_id, sender="agent", text=welcome_msg, stage="1_INTRO")
            await self.send_message(session, chat_id, welcome_msg)
            return

        if text.startswith("/reset"):
            if chat_id in self.sessions:
                del self.sessions[chat_id]
            self.alerted_sessions.discard(chat_id)
            msg = "✅ Muloqot va sessiya tozalandi. Yangidan boshlaymiz!"
            db.add_message(session_id, sender="agent", text=msg)
            await self.send_message(session, chat_id, msg)
            return

        # 3. Check Autopilot Status (Human Takeover)
        if conv and conv.get("autopilot_enabled") == 0:
            logger.info(f"Operator takeover active for tg_{chat_id}. AI response skipped.")
            return

        # 4. Process message through VertaFlow Sales Engine
        engine = self.get_or_create_engine(chat_id)
        result = engine.process_message(text)
        reply = result["reply"]

        # 5. Persist agent reply and lead state to DB
        db.add_message(session_id, sender="agent", text=reply, stage=result["stage"], script=result["script"])
        db.save_lead(
            session_id=session_id,
            name=user_name,
            channel="telegram",
            phone=engine.state.collected_attributes.get("phone"),
            pain=engine.state.collected_attributes.get("identified_pain"),
            volume=engine.state.collected_attributes.get("volume_or_size"),
            timeline=engine.state.collected_attributes.get("timeline"),
            score=result["lead_score"],
            tier=result["lead_tier"],
            stage=result["stage"],
            script=result["script"],
            score_reasons=result["score_reasons"],
            dossier=result.get("dossier")
        )

        # 6. Send 2-3 line response to Telegram user
        await self.send_message(session, chat_id, reply)

        # 7. Check if lead is HOT -> Send alert to manager
        if result["lead_score"] >= 70 or result.get("dossier"):
            await self.notify_sales_manager(session, chat_id, engine)

    async def start_polling(self):
        """Starts asynchronous polling loop."""
        if not self.token:
            logger.info("Telegram Bot Token kiritilmagan. Sozlamalardan token kiriting.")
            return

        self.is_running = True
        logger.info("🚀 VertaFlow Telegram Bot ishga tushdi...")

        async with aiohttp.ClientSession() as http_session:
            while self.is_running:
                try:
                    url = f"{BASE_TELEGRAM_URL}{self.token}/getUpdates"
                    params = {"offset": self.last_update_id + 1, "timeout": 20}
                    async with http_session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            updates = data.get("result", [])
                            for update in updates:
                                self.last_update_id = update["update_id"]
                                await self.handle_update(http_session, update)
                        else:
                            await asyncio.sleep(5)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Telegram polling loop error: {e}")
                    await asyncio.sleep(3)

    def stop_polling(self):
        self.is_running = False

bot_instance = VertaTelegramBot()
