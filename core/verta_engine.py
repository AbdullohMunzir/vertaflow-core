# /home/kinfolkt/verta-platform/core/verta_engine.py
"""
VertaFlow — Unified Master Core Engine
Orchestrates:
- VertaStage state machine (SPIN + Challenger)
- VertaLeadState (Attribute tracking & Lead Scoring)
- Native Google Gemini 2.5 Flash Engine with OpenAI/Groq and deterministic fallback
- Uzbek Linguistic & Script Mirroring
- Battlecard Landmine Injection
"""

import re
from typing import Dict, Any, Optional, List

from verta_stages import VertaStage, VERTA_STAGES_CONFIG, determine_next_stage
from verta_state import VertaLeadState
from verta_uzbek_engine import detect_script, process_agent_output, to_cyrillic
from verta_battlecards import BattlecardEngine, Battlecard
from verta_prompt import build_sales_closer_prompt
from verta_gemini import VertaGeminiClient
from verta_llm import VertaLLMClient

try:
    from verta_rag import get_rag_engine
except ImportError:
    from core.verta_rag import get_rag_engine

class VertaFlowEngine:
    def __init__(
        self,
        session_id: str,
        channel: str = "telegram",
        business_profile: Optional[Dict[str, Any]] = None,
        gemini_client: Optional[VertaGeminiClient] = None,
        llm_client: Optional[VertaLLMClient] = None,
        knowledge_text: str = "",
        persona: Optional[Dict[str, Any]] = None
    ):
        self.state = VertaLeadState(session_id=session_id, channel=channel)
        self.battlecards = BattlecardEngine()
        self.business_profile = business_profile or {
            "business_name": "Mebel Fabrikasi",
            "business_desc": "Oshxona va uy mebellari ishlab chiqarish",
            "avg_check": "5 000 000 so'm",
            "faq_list": []
        }
        self.gemini_client = gemini_client or VertaGeminiClient()
        self.llm_client = llm_client or VertaLLMClient()
        self.knowledge_text = knowledge_text or ""
        self.persona = persona or {}

    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Main pipeline processing prospect's incoming message and returning conversational closer response.
        """
        raw_msg = user_message.strip()
        self.state.add_message("user", raw_msg)

        # 1. Linguistic & Script Detection
        detected_script = detect_script(raw_msg)
        self.state.script_preference = detected_script

        # 2. Competitor / Battlecard Detection
        battlecard = self.battlecards.detect_competitor(raw_msg)
        has_competitor = battlecard is not None

        # 3. Objection & Intent Extraction
        is_objection = False
        lower_msg = raw_msg.lower()
        if any(w in lower_msg for w in ["qimmat", "қиммат", "arzon", "арзон", "o'ylab", "ўйлаб", "shoshilmay"]):
            is_objection = True
            self.state.collected_attributes["current_objection"] = raw_msg

        # 4. Attribute Extraction & Dynamic Scoring
        self._extract_lead_attributes(raw_msg)

        # 5. State Machine Transition (Adaptive — telefon + og'riq aniqlansa tezroq yopadi)
        has_phone = bool(self.state.collected_attributes.get("phone"))
        has_pain = bool(self.state.collected_attributes.get("identified_pain"))
        next_stage = determine_next_stage(
            current_stage=self.state.current_stage,
            user_intent="normal",
            lead_score=self.state.lead_score,
            has_unresolved_objection=is_objection or has_competitor,
            is_ready_for_close=self.state.is_lead_ready(),
            has_phone=has_phone,
            has_pain=has_pain
        )
        self.state.current_stage = next_stage
        self.state.questions_asked += 1

        # 6. Response Construction:
        # Step A: Targeted RAG Context Retrieval (Dense + Sparse + RRF)
        rag_context = ""
        try:
            rag_engine = get_rag_engine()
            rag_context = rag_engine.assemble_context(raw_msg, top_k=3)
        except Exception:
            rag_context = ""

        effective_knowledge = rag_context if rag_context else (self.knowledge_text if len(self.knowledge_text) < 1200 else "")

        response_text = None
        prompt = build_sales_closer_prompt(
            business_profile=self.business_profile,
            stage_name=next_stage.value,
            collected_attributes=self.state.collected_attributes,
            detected_script=detected_script,
            battlecard=battlecard,
            knowledge_text=effective_knowledge,
            persona=self.persona
        )

        # Step A: Check for prompt injection / jailbreak attacks
        lower_msg = raw_msg.lower()
        injection_patterns = [
            "ignore previous instructions", "ignore all previous", "system prompt",
            "disregard instructions", "print your prompt", "tell me your api key",
            "give me the secret", "acting as a dan", "sudo mode", "developer mode"
        ]
        is_injection = any(p in lower_msg for p in injection_patterns)

        safe_user_msg = f"<prospect_message>\n{raw_msg}\n</prospect_message>"

        if self.gemini_client:
            response_text = self.gemini_client.generate_response(
                system_prompt=prompt,
                user_message=safe_user_msg,
                recent_history=self.state.history
            )

        # Step B: Try Alternative LLM (OpenAI/Groq) if Gemini is not available
        if not response_text and self.llm_client:
            response_text = self.llm_client.generate_response(
                system_prompt=prompt,
                user_message=safe_user_msg,
                recent_history=self.state.history
            )

        # Step C: Deterministic Rule Fallback if external APIs fail or injection detected
        if is_injection and not response_text:
            response_text = "Korxonamiz rasmiy savdo bo'limi sizga mahsulotlar va xizmatlar bo'yicha yordam beradi. Mahsulotimiz narxlari bo'yicha qanday savolingiz bor?"
        elif not response_text:
            response_text = self._generate_stage_response(next_stage, battlecard, raw_msg)

        # 7. Post-Processing: Uzbek Calque Filter, Brevity Guard, Script Mirroring
        final_text = process_agent_output(response_text, target_script=detected_script)
        self.state.add_message("agent", final_text)

        # 8. Token Accounting Calculation (Server-Authoritative)
        token_usage = None
        if self.gemini_client and getattr(self.gemini_client, 'last_usage', None):
            token_usage = self.gemini_client.last_usage
        elif self.llm_client and getattr(self.llm_client, 'last_usage', None):
            token_usage = self.llm_client.last_usage

        if not token_usage:
            p_tok = int(len(prompt) // 3.5 + len(raw_msg) // 3.5)
            c_tok = int(len(final_text) // 3.5)
            token_usage = {
                "model": "verta-deterministic",
                "prompt_tokens": p_tok,
                "completion_tokens": c_tok,
                "total_tokens": p_tok + c_tok
            }

        # 9. Check Lead Status & Dossier
        dossier = None
        if self.state.is_lead_ready() or self.state.lead_score >= 70:
            dossier = self.state.generate_lead_dossier()

        return {
            "reply": final_text,
            "stage": self.state.current_stage.value,
            "lead_score": self.state.lead_score,
            "lead_tier": self.state.lead_tier,
            "script": self.state.script_preference,
            "dossier": dossier,
            "score_reasons": self.state.score_reasons,
            "token_usage": token_usage
        }

    def _extract_lead_attributes(self, msg: str):
        """Extracts key attributes and scores lead mathematically."""
        lower = msg.lower()
        
        # Phone number detection
        phone_match = re.search(r'(\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\b\d{9}\b)', msg)
        if phone_match and not self.state.collected_attributes["phone"]:
            self.state.update_attribute("phone", phone_match.group(0), 30, "Telefon raqami qoldirildi")

        # Order volume / team size
        if any(c.isdigit() for c in msg) and any(w in lower for w in ["ta", "дона", "buyurtma", "буюртма", "mijoz", "мижоз"]):
            if not self.state.collected_attributes["volume_or_size"]:
                self.state.update_attribute("volume_or_size", msg, 20, "Hajm va ko'lam ma'lumoti berildi")

        # Pain point / problem
        if any(w in lower for w in ["ulgurmay", "улгурмай", "kech", "кеч", "muammo", "муаммо", "yo'qot", "йўқот", "charchat"]):
            if not self.state.collected_attributes["identified_pain"]:
                self.state.update_attribute("identified_pain", msg, 25, "Asosiy biznes og'rig'i aniqlandi")

        # Timeline / Urgency
        if any(w in lower for w in ["shu hafta", "шу ҳафта", "tezroq", "тезроқ", "bugun", "бугун", "shu oy", "шу ой"]):
            if not self.state.collected_attributes["timeline"]:
                self.state.update_attribute("timeline", msg, 15, "Xarid qilish muddati aniq")

    def _generate_stage_response(self, stage: VertaStage, battlecard: Optional[Any], user_msg: str) -> str:
        """Stage-specific tailored message generation (Deterministic Fallback)."""
        if battlecard:
            return self.battlecards.generate_counter_response(battlecard)

        biz_name = self.business_profile.get("business_name", "Korxonamiz")

        if stage == VertaStage.INTRO or stage == VertaStage.SITUATION:
            return (
                f"Assalomu alaykum! {biz_name} xizmatlari 1.5 mln so'mdan boshlanadi.\n"
                f"Sizga eng ma'qulini hisoblashimiz uchun: hozir kuniga nechta buyurtma qabul qilyapsiz?"
            )
        elif stage == VertaStage.PROBLEM:
            return (
                "Tushunarli. Aynan shu hajmda ko'p korxonalarda menejerlar kechikishi kuzatiladi.\n"
                "Hozirda savdo bo'limingizda eng ko'p vaqt va mijoz yo'qotilayotgan joyi qayerda?"
            )
        elif stage == VertaStage.IMPLICATION:
            return (
                "Agar kuniga atigi 2 ta mijoz javob kutib sovib ketsa — bu oyiga $1,500 yo'qotilgan daromad degani.\n"
                "Sizda hozir menejerlar mijozga necha daqiqada javob berishyapti?"
            )
        elif stage == VertaStage.SOLUTION_PITCH:
            return (
                "VertaFlow har bir murojaatga 3 soniyada professional javob berib, buyurtmani o'zi yopadi.\n"
                "Xuddi sizning sohangizdagi 12 ta korxona o'tgan oy buyurtma yo'qotishni 0 ga tushirdi."
            )
        elif stage == VertaStage.OBJECTION_HANDLING:
            return (
                "To'g'ri, bir qarashda shunday tuyulishi mumkin.\n"
                "Faqat aytingchi, asosiy ikkilanish narxdami yoki tizim natija berishidami?"
            )
        elif stage == VertaStage.CLOSING:
            return (
                "Keling, 10 daqiqalik qisqa konsultatsiyada sizning korxonangiz uchun hisoblab beramiz.\n"
                "Qaysi vaqt ma'qul: bugun 16:00 mi yoki ertaga 11:00?"
            )
        elif stage == VertaStage.HANDOFF_HUMAN:
            return (
                "Ajoyib! Mutaxassisimiz barcha ma'lumotlarni oldi va 10 daqiqada siz bilan bog'lanadi.\n"
                "Xaridingiz barakali bo'lsin!"
            )
        return "Sizga qanday yordam bera olaman?"
