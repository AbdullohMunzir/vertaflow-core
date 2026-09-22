# /home/kinfolkt/verta-platform/core/verta_gemini.py
"""
VertaFlow — Native Google Gemini 2.5 Flash Engine
Direct high-performance integration with Google's Gemini 2.5 Flash model.
Configured for sub-second responses, low latency, and native Uzbek conversational fluency.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("VertaGemini")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
DEFAULT_GEMINI_KEY = "your_gemini_api_key_here"

class VertaGeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            try:
                import db
                self.api_key = db.get_setting("gemini_api_key")
            except Exception:
                pass
        if not self.api_key:
            self.api_key = DEFAULT_GEMINI_KEY
        self.last_usage = None

    def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        recent_history: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: int = 8
    ) -> Optional[str]:
        """
        Sends structured conversation to Google Gemini 2.5 Flash.
        Returns generated text or None if error occurred (triggering fallback).
        """
        if not self.api_key or not self.api_key.strip():
            return None

        url = f"{GEMINI_API_URL}?key={self.api_key.strip()}"

        # Construct contents with history
        contents = []

        if recent_history:
            for h in recent_history[-4:]:
                role = "user" if h.get("sender") == "user" or h.get("role") == "user" else "model"
                text = h.get("text") or h.get("content") or ""
                if text:
                    contents.append({
                        "role": role,
                        "parts": [{"text": text}]
                    })

        # Append current user prompt
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000,
                "topP": 0.9,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usageMetadata", {})
                self.last_usage = {
                    "model": "gemini-2.5-flash",
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0)
                }
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        reply = parts[0]["text"].strip()
                        return reply
                logger.warning(f"Gemini empty candidates: {data}")
                return None
            elif resp.status_code == 429:
                logger.warning("Gemini API rate limit exceeded (429). Executing rule fallback.")
                return None
            else:
                logger.warning(f"Gemini API error {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.warning(f"Gemini connection failed: {e}. Executing rule fallback.")
            return None

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg",
        timeout_seconds: int = 15
    ) -> Optional[str]:
        """
        Transcribes voice audio note (e.g. Telegram .oga/.ogg) to text in natural Uzbek
        using Gemini 2.5 Flash multimodal capabilities.
        """
        if not self.api_key or not self.api_key.strip():
            return None

        import base64
        encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
        url = f"{GEMINI_API_URL}?key={self.api_key.strip()}"

        payload = {
            "systemInstruction": {
                "parts": [{
                    "text": (
                        "Siz o'zbek tilidagi audio xabarlarni juda aniq transkripsiya qiluvchi sun'iy intellektsiz. "
                        "Ushbu audio yozuvni diqqat bilan eshiting va unda aytilgan har bir so'zni tabiiy o'zbek tilida (Lotin yoki Kirill, so'zlovchining talaffuziga mos ravishda) matnga o'giring. "
                        "Faqat eshitilgan so'zlarning o'zini yozing. Hech qanday boshqa tushuntirish, izoh yoki sarlavha qo'shmang."
                    )
                }]
            },
            "contents": [{
                "role": "user",
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": encoded_audio
                        }
                    },
                    {
                        "text": "Ushbu ovozli xabarni matnga o'giring (transcribe this audio to text):"
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 500
            }
        }

        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        transcribed = parts[0]["text"].strip()
                        return transcribed
                return None
            elif resp.status_code == 429:
                logger.warning("Gemini API rate limit exceeded during audio transcription (429).")
                return None
            else:
                logger.warning(f"Gemini transcription error {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.warning(f"Gemini transcription request failed: {e}")
            return None
