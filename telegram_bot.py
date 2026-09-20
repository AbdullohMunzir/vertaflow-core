# /home/kinfolkt/verta-platform/telegram_bot.py
"""
VertaFlow — Telegram Omnichannel Connector
Handles real-time Telegram incoming messages, routes them through VertaFlowEngine,
mirrors user's script (Latin/Cyrillic), enforces 2-3 line brevity,
and dispatches instant Hot Lead Dossiers to the Sales Manager's chat!
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Optional, Any
import aiohttp

# Add core engine to path
sys.path.append(os.path.join(os.path.dirname(__file__), "core"))
from verta_engine import VertaFlowEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VertaTelegramBot")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SALES_MANAGER_CHAT_ID = os.getenv("SALES_MANAGER_CHAT_ID", "")
BASE_TELEGRAM_URL = "https://api.telegram.org/bot"

class VertaTelegramBot:
    def __init__(self, token: Optional[str] = None, manager_chat_id: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.manager_chat_id = manager_chat_id or SALES_MANAGER_CHAT_ID
        self.sessions: Dict[int, VertaFlowEngine] = {}
        self.is_running = False
        self.last_update_id = 0
        self.alerted_sessions = set()  # To avoid spamming dossier for same lead repeatedly

    def get_or_create_session(self, chat_id: int) -> VertaFlowEngine:
        if chat_id not in self.sessions:
            self.sessions[chat_id] = VertaFlowEngine(session_id=f"tg_{chat_id}", channel="telegram")
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
            return  # Already alerted for this lead

        self.alerted_sessions.add(chat_id)
        dossier = engine.state.generate_lead_dossier()
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

        target_manager = self.manager_chat_id or str(chat_id)
        logger.info(f"🚨 Dispatching Lead Dossier for tg_{chat_id} to Manager: {target_manager}")
        if self.manager_chat_id:
            try:
                await self.send_message(session, int(self.manager_chat_id), manager_text)
            except Exception as e:
                logger.error(f"Failed to notify sales manager: {e}")

    async def handle_update(self, session: aiohttp.ClientSession, update: Dict[str, Any]):
        """Processes a single Telegram update message."""
        message = update.get("message")
        if not message or "text" not in message:
            return

        chat_id = message["chat"]["id"]
        text = message["text"].strip()
        user_name = message.get("from", {}).get("first_name", "Mijoz")

        # Command handling
        if text.startswith("/start"):
            welcome_msg = (
                f"Assalomu alaykum, {user_name}! VertaFlow savdo tizimiga xush kelibsiz.\n"
                f"Sizga biznesingiz uchun eng ma'qul yechimni hisoblab berishimiz mumkin.\n"
                f"Hozirda korxonangizda qaysi mahsulot yoki xizmat sotuvini rivojlantirmoqchisiz?"
            )
            await self.send_message(session, chat_id, welcome_msg)
            return

        if text.startswith("/reset"):
            if chat_id in self.sessions:
                del self.sessions[chat_id]
            self.alerted_sessions.discard(chat_id)
            await self.send_message(session, chat_id, "✅ Muloqot va sessiya tozalandi. Yangidan boshlaymiz!")
            return

        # Process through VertaFlow Sales Engine
        engine = self.get_or_create_session(chat_id)
        result = engine.process_message(text)
        reply = result["reply"]

        # Send 2-3 line response to user
        await self.send_message(session, chat_id, reply)

        # Check if lead is HOT -> Send alert to manager
        if result["lead_score"] >= 70 or result.get("dossier"):
            await self.notify_sales_manager(session, chat_id, engine)

    async def start_polling(self):
        """Starts asynchronous polling loop."""
        if not self.token:
            logger.info("ℹ️ Telegram Bot Token o'rnatilmagan. Bot simulyatsiya rejimida kutmoqda.")
            return

        self.is_running = True
        logger.info("🚀 VertaFlow Telegram Bot ishga tushdi...")

        async with aiohttp.ClientSession() as http_session:
            while self.is_running:
                try:
                    url = f"{BASE_TELEGRAM_URL}{self.token}/getUpdates"
                    params = {"offset": self.last_update_id + 1, "timeout": 30}
                    async with http_session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=35)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            updates = data.get("result", [])
                            for update in updates:
                                self.last_update_id = update["update_id"]
                                await self.handle_update(http_session, update)
                        else:
                            logger.error(f"Polling HTTP {resp.status}")
                            await asyncio.sleep(5)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Telegram polling loop error: {e}")
                    await asyncio.sleep(3)

    def stop_polling(self):
        self.is_running = False

if __name__ == "__main__":
    print("VertaFlow Telegram Bot module ready.")
    bot = VertaTelegramBot()
    # If token exists, run polling
    if bot.token:
        asyncio.run(bot.start_polling())
    else:
        print("Telegram Bot Token kiritilmagan. Test o'tkazish uchun env TELEGRAM_BOT_TOKEN belgilang.")
