# /home/kinfolkt/verta-platform/core/verta_stages.py
"""
VertaFlow — Sales Stages & Methodology Definitions
Implements the 8-stage conversational state machine merging SalesGPT's stage controller 
with SPIN Selling, Gap Selling, and Challenger Sale commercial teaching frameworks.
"""

from enum import Enum
from typing import Dict, Any, Optional

class VertaStage(str, Enum):
    INTRO = "1_INTRO"                         # Upfront Contract & Welcoming
    SITUATION = "2_SITUATION"                 # SPIN: 1-2 situational scoping questions
    PROBLEM = "3_PROBLEM"                     # SPIN: Identifying core friction/pain
    IMPLICATION = "4_IMPLICATION"             # SPIN + Challenger: Cost of inaction & Reframe
    SOLUTION_PITCH = "5_SOLUTION_PITCH"       # Need-Payoff: Tailored benefit & Social Proof
    OBJECTION_HANDLING = "6_OBJECTION"        # AECR: Acknowledge, Empathize, Clarify, Reframe
    CLOSING = "7_CLOSING"                     # The Close: Direct next step commitment
    HANDOFF_HUMAN = "8_HANDOFF_HUMAN"         # Escalation / Hot lead transfer to human sales rep
    END = "9_END"                             # Graceful finish / Qualified out


VERTA_STAGES_CONFIG: Dict[VertaStage, Dict[str, Any]] = {
    VertaStage.INTRO: {
        "name": "Kirish va Muloqot Sharti (Intro & Upfront Contract)",
        "goal": "Samimiy salomlashish, mijozga bosim qilmaslik va muloqot maqsadi bo'yicha ruxsat olish.",
        "max_questions": 1,
        "allowed_tones": ["do'stona", "maslahatchi", "rasmiy"],
        "prompt_instruction": (
            "Mijoz bilan samimiy salomlashing. Darhol sotuv qilmasdan, "
            "mijozga to'g'ri yechim berish uchun 1-2 ta qisqa savol berishga ruxsat so'rang."
        )
    },
    VertaStage.SITUATION: {
        "name": "Vaziyatni Aniqlash (SPIN: Situation)",
        "goal": "Mijozning hozirgi holatini o'rganish. Maksimal 1-2 ta qisqa savol.",
        "max_questions": 1,
        "prompt_instruction": (
            "Mijozning hozirgi jarayoni yoki jamoasi qanday ishlayotgani haqida "
            "faqat 1 ta qisqa va aniq savol bering. Mijozni so'roqqa tutmang."
        )
    },
    VertaStage.PROBLEM: {
        "name": "Muammo va Og'riqni Ochish (SPIN: Problem)",
        "goal": "Mijoz duch kelayotgan noqulaylik yoki kechikishlarni yuzaga chiqarish.",
        "max_questions": 1,
        "prompt_instruction": (
            "Hozirgi tizimda qayerida xato, sekinlik yoki mijoz yo'qotish bo'layotganini "
            "bitta savol orqali yuzaga chiqaring."
        )
    },
    VertaStage.IMPLICATION: {
        "name": "Oqibat va Fikrni Yangilash (Challenger + Implication)",
        "goal": "Mijozga muammoning haqiqiy moliyaviy yoki vaqt zararini ko'rsatish va reframe qilish.",
        "max_questions": 1,
        "prompt_instruction": (
            "Challenger usulida yangi tushuncha (insight) bering: agar muammo hal bo'lmasa, "
            "oyiga qancha pul yoki mijoz yo'qotilishini hisoblab ko'rsating. Loss Aversion qo'llang."
        )
    },
    VertaStage.SOLUTION_PITCH: {
        "name": "Yechim va Ijtimoiy Isbot (Need-Payoff & Social Proof)",
        "goal": "Aynan mijoz aytgan og'riqqa davo bo'ladigan yechimni taqdim etish va 120+ mijoz keysini keltirish.",
        "max_questions": 1,
        "prompt_instruction": (
            "Butun katalog emas, faqat mijoz aytgan muammoga mos 1 ta aniq yechimni ayting. "
            "Xuddi shu sohadagi boshqa mijozlarimiz olgan natijasini (Social Proof) tilga oling."
        )
    },
    VertaStage.OBJECTION_HANDLING: {
        "name": "E'tirozlarni Yopish (AECR Framework)",
        "goal": "Narx, shubha yoki raqobatchi bilan solishtirish e'tirozlarini professional hal qilish.",
        "max_questions": 1,
        "prompt_instruction": (
            "Mijoz e'tiroz bildirsa bahslashmang. "
            "AECR (Acknowledge -> Empathize -> Clarify -> Reframe) qoidasiga amal qiling. "
            "Asl ikkilanish sababini aniqlashtiring."
        )
    },
    VertaStage.CLOSING: {
        "name": "Bitimni Yakunlash (The Hard Close)",
        "goal": "Mijozdan aniq keyingi qadam bo'yicha majburiyat (commitment) olish.",
        "max_questions": 1,
        "prompt_instruction": (
            "Aniq 2 ta vaqt variantini taklif qiling: "
            "'Bugun 16:00 mi yoki ertaga 11:00 da 10 daqiqalik konsultatsiya qilsak ma'qulmi?'"
        )
    },
    VertaStage.HANDOFF_HUMAN: {
        "name": "Inson Xodimga O'tkazish (Smart Handoff)",
        "goal": "Muloqotni silliq operatorga topshirish va qisqa xulosa chiqarish.",
        "max_questions": 0,
        "prompt_instruction": (
            "Mijozga mutaxassis darhol bog'lanishini xabar qiling. Ortiqcha savol bermang."
        )
    }
}

def determine_next_stage(
    current_stage: VertaStage, 
    user_intent: str, 
    lead_score: int, 
    has_unresolved_objection: bool,
    is_ready_for_close: bool
) -> VertaStage:
    if user_intent == "request_human":
        return VertaStage.HANDOFF_HUMAN

    if has_unresolved_objection:
        return VertaStage.OBJECTION_HANDLING

    if is_ready_for_close or lead_score >= 80:
        return VertaStage.CLOSING

    progression = {
        VertaStage.INTRO: VertaStage.SITUATION,
        VertaStage.SITUATION: VertaStage.PROBLEM,
        VertaStage.PROBLEM: VertaStage.IMPLICATION,
        VertaStage.IMPLICATION: VertaStage.SOLUTION_PITCH,
        VertaStage.SOLUTION_PITCH: VertaStage.CLOSING,
        VertaStage.OBJECTION_HANDLING: VertaStage.CLOSING,
        VertaStage.CLOSING: VertaStage.HANDOFF_HUMAN,
    }

    return progression.get(current_stage, VertaStage.CLOSING)
