# /home/kinfolkt/verta-platform/core/verta_llm.py
"""
VertaFlow — Hybrid LLM Integration Layer
Connects to OpenAI, Groq, OpenRouter, or any OpenAI-compatible endpoint.
Features sub-second timeout, error resilience, and automatic fallback to rule engine.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("VertaLLM")

PROVIDER_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions"
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "meta-llama/llama-3.3-70b-instruct"
}

class VertaLLMClient:
    def __init__(self, api_key: Optional[str] = None, provider: str = "openai", model: Optional[str] = None):
        self.provider = provider.lower() if provider else "openai"
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        self.model = model or DEFAULT_MODELS.get(self.provider, "gpt-4o-mini")
        self.endpoint = PROVIDER_ENDPOINTS.get(self.provider, PROVIDER_ENDPOINTS["openai"])
        self.last_usage = None

    def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        recent_history: Optional[List[Dict[str, str]]] = None,
        timeout_seconds: int = 6
    ) -> Optional[str]:
        """
        Sends conversational completion request to selected LLM.
        Returns generated text or None if fallback should take over.
        """
        if not self.api_key or not self.api_key.strip():
            # No API key provided -> use rule fallback
            return None

        messages = [{"role": "system", "content": system_prompt}]

        if recent_history:
            for h in recent_history[-4:]:
                role = "user" if h.get("sender") == "user" or h.get("role") == "user" else "assistant"
                content = h.get("text") or h.get("content") or ""
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 160
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usage", {})
                self.last_usage = {
                    "model": self.model,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                }
                reply = data["choices"][0]["message"]["content"].strip()
                return reply
            else:
                logger.warning(f"LLM API returned {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.warning(f"LLM request error: {e}. Falling back to deterministic engine.")
            return None
