# /home/kinfolkt/verta-platform/core/verta_state.py
"""
VertaFlow — Deterministic State Tracking & Lead Scoring Engine
Combines AI-Lead-Qualifier's strict attribute tracking with LangGraph's dynamic scoring schema.
"""

from typing import Dict, Any, List, Optional
from verta_stages import VertaStage

class VertaLeadState:
    """
    Tracks customer conversational data, mandatory requirements, and live lead score.
    """
    def __init__(self, session_id: str, channel: str = "telegram"):
        self.session_id = session_id
        self.channel = channel
        self.current_stage = VertaStage.INTRO
        self.script_preference = "latin" # 'latin' or 'cyrillic'
        
        # Attribute stores
        self.collected_attributes: Dict[str, Optional[str]] = {
            "name": None,
            "phone": None,
            "business_type": None,
            "volume_or_size": None,
            "identified_pain": None,
            "budget": None,
            "timeline": None,
            "current_objection": None,
            "competitor_mentioned": None
        }

        # Mandatory attributes needed before marking lead as ready/won
        self.mandatory_attributes = ["phone", "identified_pain", "timeline"]

        self.questions_asked = 0
        self.history: List[Dict[str, str]] = []
        self.score_reasons: List[str] = []
        self.lead_score = 10 # Base starting score

    def update_attribute(self, key: str, value: Any, score_points: int = 0, reason: str = ""):
        """Updates an attribute and dynamically recalibrates lead score."""
        if key in self.collected_attributes and value:
            self.collected_attributes[key] = str(value)
            if score_points > 0:
                self.lead_score = min(100, self.lead_score + score_points)
                if reason:
                    self.score_reasons.append(f"+{score_points} ball: {reason}")

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content, "stage": self.current_stage.value})

    def is_mandatory_complete(self) -> bool:
        """Verifies all mandatory attributes have been collected."""
        for attr in self.mandatory_attributes:
            if not self.collected_attributes.get(attr):
                return False
        return True

    def is_lead_ready(self) -> bool:
        """Determines if the lead has met qualification threshold for hard closing or human handoff."""
        return self.is_mandatory_complete() and self.questions_asked >= 2

    @property
    def lead_tier(self) -> str:
        """Classifies lead into actionable sales tier."""
        if self.lead_score >= 75:
            return "HOT 🔥"
        elif self.lead_score >= 40:
            return "WARM ⚡"
        return "COLD ❄️"

    def generate_lead_dossier(self) -> str:
        """
        Generates the concise 3-4 line executive summary for human sales reps (Hot Handoff).
        """
        name = self.collected_attributes.get('name') or "Noma'lum mijoz"
        phone = self.collected_attributes.get('phone') or "Raqam kutilmoqda"
        pain = self.collected_attributes.get('identified_pain') or "Aniq ko'rsatilmagan"
        timeline = self.collected_attributes.get('timeline') or "Aniqlanmagan"
        budget = self.collected_attributes.get('budget') or "Standart tarif"
        objection = self.collected_attributes.get('current_objection') or "Yo'q"

        dossier = (
            f"📋 VERTA LEAD DOSSIER ({self.lead_tier} • {self.lead_score}/100):\n"
            f"👤 Mijoz: {name} ({phone})\n"
            f"🎯 Asosiy og'riq: {pain}\n"
            f"⏳ Muddat & Byudjet: {timeline} • {budget}\n"
            f"⚠️ Hozirgi e'tiroz/to'siq: {objection}"
        )
        return dossier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "stage": self.current_stage.value,
            "script": self.script_preference,
            "score": self.lead_score,
            "tier": self.lead_tier,
            "attributes": self.collected_attributes,
            "mandatory_complete": self.is_mandatory_complete(),
            "questions_asked": self.questions_asked,
            "score_reasons": self.score_reasons
        }
