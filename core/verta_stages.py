# /home/kinfolkt/verta-platform/core/verta_stages.py
"""
VertaFlow — Elite Sales Stage Machine v2.0
Implements the 8-stage conversational state machine merging:
  - SPIN Selling (Rackham)
  - The Challenger Sale (Dixon & Adamson)
  - Sandler Up-Front Contract
  - Gap Selling (Keenan)
  - MEDDIC Qualification scoring
  - Adaptive stage progression based on lead score & signals
"""

from enum import Enum
from typing import Dict, Any, Optional


class VertaStage(str, Enum):
    INTRO             = "1_INTRO"           # Upfront Contract & Warmth (Sandler)
    SITUATION         = "2_SITUATION"       # SPIN: Situation scoping
    PROBLEM           = "3_PROBLEM"         # SPIN + Gap: Pain identification
    IMPLICATION       = "4_IMPLICATION"     # Challenger + Loss Aversion: Cost of inaction
    SOLUTION_PITCH    = "5_SOLUTION_PITCH"  # Need-Payoff + Social Proof (MEDDIC: Champion)
    OBJECTION_HANDLING= "6_OBJECTION"       # LAER + AECR: Objection resolution
    CLOSING           = "7_CLOSING"         # Alternative Close + Micro-commitment
    HANDOFF_HUMAN     = "8_HANDOFF_HUMAN"   # Smart escalation to human rep
    END               = "9_END"             # Graceful qualification-out


VERTA_STAGES_CONFIG: Dict[VertaStage, Dict[str, Any]] = {
    VertaStage.INTRO: {
        "name": "Kirish va Ruxsat Olish (Sandler Up-Front Contract)",
        "goal": (
            "Samimiy salomlashish va birinchi micro-commitment olish. "
            "Darhol sotuv qilmasdan, '1-2 ta savol bersammi?' deb ruxsat so'rang. "
            "Bu Cialdini Commitment & Consistency prinsipini ishga tushiradi."
        ),
        "max_questions": 1,
        "allowed_tones": ["do'stona", "maslahatchi", "rasmiy"],
        "key_techniques": ["Sandler Up-Front Contract", "Cialdini: Commitment"],
        "success_signal": "Mijoz savol berishga ruxsat berdi",
        "prompt_instruction": (
            "Mijoz bilan samimiy salomlashing. Darhol sotuv qilmasdan, "
            "mijozga to'g'ri yechim berish uchun 1-2 ta qisqa savol berishga "
            "ruxsat so'rang ('Bitta savol bersammi?'). "
            "Bu birinchi micro-commitment — muhim."
        )
    },
    VertaStage.SITUATION: {
        "name": "Vaziyatni Aniqlash (SPIN: Situation)",
        "goal": (
            "Mijozning hozirgi jarayoni, vositalari, jamoasi yoki hajmini bilib olish. "
            "SNAP qoidasi: Savol SIMPLE va INVALUABLE bo'lsin. "
            "MEDDIC: Metrics — muvaffaqiyat qanday o'lchanishini bilib oling."
        ),
        "max_questions": 1,
        "key_techniques": ["SPIN: Situation", "SNAP: Simple", "MEDDIC: Metrics"],
        "success_signal": "Mijoz hozirgi holatini tasvirlab berdi",
        "prompt_instruction": (
            "Mijozning hozirgi jarayoni yoki jamoasi qanday ishlayotgani haqida "
            "faqat 1 ta qisqa va aniq savol bering. Mijozni so'roqqa tutmang. "
            "MEDDIC: Hajm/ko'lam raqamini bilib oling."
        )
    },
    VertaStage.PROBLEM: {
        "name": "Muammo va Og'riqni Ochish (SPIN: Problem + Gap Selling)",
        "goal": (
            "Mijozning hozirgi holatidagi 'og'riq nuqtasi'ni aniqlash. "
            "Gap Selling (Keenan): Hozirgi holat vs. orzu qilingan holat o'rtasidagi farqni ko'rsating. "
            "Sandler Pain Funnel: Og'riqni 3 darajada chuqurlashtiring."
        ),
        "max_questions": 1,
        "key_techniques": ["SPIN: Problem", "Gap Selling", "Sandler Pain Funnel"],
        "success_signal": "Mijoz asosiy og'riq nuqtasini aytdi",
        "prompt_instruction": (
            "Hozirgi tizimda qayerda xato, sekinlik yoki mijoz yo'qotish bo'layotganini "
            "bitta savol orqali yuzaga chiqaring. "
            "Muammoni siz o'ylab topmang — mijoz o'zi aytsin."
        )
    },
    VertaStage.IMPLICATION: {
        "name": "Yo'qotishni Hisoblatish (Challenger + Loss Aversion + Kahneman)",
        "goal": (
            "Muammoni hal qilmaslikning MOLIYAVIY VA VAQT zararini aniq raqamlar bilan ko'rsatish. "
            "Kahneman: Odamlar yo'qotishdan 2.5x ko'proq qo'rqadi — shu psixologiyadan foydalaning. "
            "Challenger Insight: Mijoz bilmagan yangi haqiqatni oching."
        ),
        "max_questions": 1,
        "key_techniques": ["Challenger Teach", "Loss Aversion", "Prospect Theory"],
        "success_signal": "Mijoz muammoning moliyaviy zararini tushundi",
        "prompt_instruction": (
            "Challenger usulida yangi insight bering: "
            "'Ko'pchilik shunday o'ylaydi, aslida...' "
            "Oyiga yo'qotilgan daromadni ANIQ HISOBLANG: "
            "[yo'qotilgan mijozlar] × [o'rtacha chek] = [oylik zarar]."
        )
    },
    VertaStage.SOLUTION_PITCH: {
        "name": "Yechim va Ijtimoiy Isbot (Need-Payoff + Social Proof + MEDDIC Champion)",
        "goal": (
            "Aynan mijoz og'rig'iga mos yechimni taqdim etish. Butun katalog emas — 1 ta aniq yechim. "
            "MEDDIC Champion: Mijozni ichki himoyachiga aylantiring. "
            "Cialdini Social Proof: Xuddi shu sohadagi boshqa mijoz natijasini keltiring."
        ),
        "max_questions": 1,
        "key_techniques": ["SPIN: Need-Payoff", "Social Proof", "MEDDIC: Champion", "SNAP: iNvaluable"],
        "success_signal": "Mijoz yechim o'ziga kerakli ekanini his qildi",
        "prompt_instruction": (
            "Butun katalog emas, faqat mijoz aytgan muammoga mos 1 ta aniq yechimni ayting. "
            "Xuddi shu sohadagi boshqa mijozlarimiz olgan natijasini (Social Proof) tilga oling. "
            "SNAP: Yechim noyob va boshqa joyda topib bo'lmaydigan qiymat ko'rsatsin."
        )
    },
    VertaStage.OBJECTION_HANDLING: {
        "name": "E'tirozlarni Yopish (LAER + AECR + Challenger Reframe)",
        "goal": (
            "Narx, shubha, raqobatchi yoki 'keyin' e'tirozlarini professional hal qilish. "
            "LAER: Listen → Acknowledge → Explore → Respond. "
            "AECR: Acknowledge → Empathize → Clarify → Reframe. "
            "ROI ko'rsating: narxni qiymatga o'tkazing."
        ),
        "max_questions": 1,
        "key_techniques": ["LAER", "AECR", "Challenger Reframe", "ROI Calculation"],
        "success_signal": "Mijoz e'tirozi bartaraf etildi va keyingi qadamga tayyor",
        "prompt_instruction": (
            "Mijoz e'tiroz bildirsa bahsga kirmasdan LAER/AECR qoidasiga amal qiling. "
            "Acknowledge → Asl ikkilanish sababini aniqlashtir → Aniq raqamlar bilan javob ber. "
            "Narxdan qiymatga o'tkazing. ROI ko'rsating."
        )
    },
    VertaStage.CLOSING: {
        "name": "Bitimni Yakunlash (Alternative Close + Micro-commitment + Scarcity)",
        "goal": (
            "Katta qaror emas — kichik aniq 'Keyingi Qadam' (Next Step) olish. "
            "Alternative Close: Har doim 2 ta variant bering ('ha yoki yo'q' emas). "
            "Cialdini Scarcity: Agar haqiqiy bo'lsa, cheklangan taklif haqida ayting."
        ),
        "max_questions": 1,
        "key_techniques": ["Alternative Close", "Assumptive Close", "Scarcity", "Micro-commitment"],
        "success_signal": "Mijoz aniq vaqt yoki keyingi qadam bo'yicha majburiyat oldi",
        "prompt_instruction": (
            "Aniq 2 ta vaqt/variant taklif qiling. "
            "HECH QACHON 'ha yoki yo'q' savol bermang. "
            "'10 daqiqalik bepul konsultatsiya' yoki 'bepul sinov' taklifi eng kuchli yopuvchi."
        )
    },
    VertaStage.HANDOFF_HUMAN: {
        "name": "Inson Xodimga O'tkazish (Smart Handoff)",
        "goal": (
            "Muloqotni silliq va xushchaqchaq operatorga topshirish. "
            "Barcha yig'ilgan ma'lumotlar (MEDDIC dossier) tayyor ekanini bildirish. "
            "Mijozga keyingi qadam 100% aniq bo'lsin."
        ),
        "max_questions": 0,
        "key_techniques": ["Smooth Handoff", "MEDDIC Dossier"],
        "success_signal": "Mijoz mutaxassis bog'lanishini kutmoqda",
        "prompt_instruction": (
            "Mijozga mutaxassis darhol bog'lanishini va barcha ma'lumotlar tayyor ekanini ayt. "
            "Ortiqcha savol berma. Ijobiy, xushchaqchaq ohangda yakuna."
        )
    }
}


def determine_next_stage(
    current_stage: VertaStage,
    user_intent: str,
    lead_score: int,
    has_unresolved_objection: bool,
    is_ready_for_close: bool,
    has_phone: bool = False,
    has_pain: bool = False
) -> VertaStage:
    """
    Elite adaptive stage machine:
    - High lead score → accelerate to closing
    - Objection detected → objection handling
    - Human request → immediate handoff
    - Phone collected + pain identified → skip to solution pitch
    """
    # Darhol operatorga o'tish talabi
    if user_intent in ("request_human", "operator", "odam"):
        return VertaStage.HANDOFF_HUMAN

    # Yechilmagan e'tiroz — doim objection handling
    if has_unresolved_objection:
        return VertaStage.OBJECTION_HANDLING

    # Yopishga tayyor — telefon + og'riq + yuqori ball
    if is_ready_for_close or lead_score >= 80:
        return VertaStage.CLOSING

    # Telefon va og'riq bor — solution pitchga o'ting
    if has_phone and has_pain and current_stage in (
        VertaStage.SITUATION, VertaStage.PROBLEM, VertaStage.IMPLICATION
    ):
        return VertaStage.SOLUTION_PITCH

    # Standart ketma-ket progression
    progression = {
        VertaStage.INTRO:              VertaStage.SITUATION,
        VertaStage.SITUATION:          VertaStage.PROBLEM,
        VertaStage.PROBLEM:            VertaStage.IMPLICATION,
        VertaStage.IMPLICATION:        VertaStage.SOLUTION_PITCH,
        VertaStage.SOLUTION_PITCH:     VertaStage.CLOSING,
        VertaStage.OBJECTION_HANDLING: VertaStage.CLOSING,
        VertaStage.CLOSING:            VertaStage.HANDOFF_HUMAN,
        VertaStage.HANDOFF_HUMAN:      VertaStage.END,
    }

    return progression.get(current_stage, VertaStage.CLOSING)
