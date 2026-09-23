# /home/kinfolkt/verta-platform/core/verta_battlecards.py
"""
VertaFlow — Elite Competitive Intelligence & Objection Engine v2.0
Handles competitor mentions, price objections, and stall tactics
using AECR + Challenger Reframe + Landmine Questions.
"""

from typing import Dict, List, Optional, Tuple


class Battlecard:
    def __init__(
        self,
        name: str,
        keywords: List[str],
        their_strength: str = "Past narx yoki tanish brend",
        their_weakness: str = "Sotuvni yopolmasligi",
        reframe_talk_track: str = "",
        landmine_question: str = ""
    ):
        self.name = name
        self.keywords = [k.lower() for k in keywords]
        self.their_strength = their_strength
        self.their_weakness = their_weakness
        self.reframe_talk_track = reframe_talk_track
        self.landmine_question = landmine_question


# ─────────────────────────────────────────────
# DEFAULT BATTLECARDS — Keng qamrovli raqobat intellekti
# ─────────────────────────────────────────────
DEFAULT_BATTLECARDS = [
    # 1. Arzon tugmali botlar
    Battlecard(
        name="Arzon Tugmali Botlar",
        keywords=[
            "arzon bot", "oddiy bot", "boshqa joyda arzon", "800 ming", "500 ming",
            "telegram bot", "oddiy chatbot", "button bot", "shablon bot"
        ],
        their_strength="Boshlang'ich narxi pastligi va soddaligi",
        their_weakness=(
            "E'tirozlarni yopa olmasligi, faqat tugma bosishga javob beradi, "
            "real savol kelsa 'operator' ga yo'naltiradi — mijoz sovib ketadi."
        ),
        reframe_talk_track=(
            "To'g'ri, ular boshida arzon ko'rinadi. "
            "Lekin oddiy tugmali bot mijozning 'qimmatmi?' savoliga javob berolmaydi — "
            "va u ketadi. Har kuni 2-3 ta mijoz yo'qotsangiz, oyiga 150 ta — "
            "bu o'rtacha chekka ko'paytirsangiz, qancha daromad?"
        ),
        landmine_question=(
            "Sizga shunchaki tugmali menyu kerakmi yoki "
            "e'tirozlarni o'zi yopib buyurtmani o'zi yopuvchi sotuv agentimi?"
        )
    ),

    # 2. Global CRM tizimlar
    Battlecard(
        name="Katta Global CRM (Bitrix / amoCRM)",
        keywords=[
            "bitrix", "bitrix24", "amocrm", "amo crm", "katta tizim",
            "murakkab dastur", "crm bor", "srm", "salesforce"
        ],
        their_strength="Global brend, keng funksionallik va ko'p integratsiyalar",
        their_weakness=(
            "O'rnatish 2-3 oy, sozlash uchun alohida mutaxassis kerak, "
            "oylik narxi katta, O'zbekiston bozori uchun mahalliy sozlama yo'q."
        ),
        reframe_talk_track=(
            "Ular juda kuchli tizimlar — global standart. "
            "Biroq to'liq sozlash uchun 2-3 oy va alohida developer kerak. "
            "Shu vaqt ichida ham sotuv bot kerak bo'ladi."
        ),
        landmine_question=(
            "Sizga 2-3 oy keyin tayyor bo'ladigan murakkab tizim kerakmi yoki "
            "bugun 24 soatda ishga tushib ertaga sotuv keltiradigan yechimmi?"
        )
    ),

    # 3. Freelancer / individual dasturchilar
    Battlecard(
        name="Freelancer / Shaxsiy Dasturchi",
        keywords=[
            "dasturchi bor", "o'zimiz yozamiz", "freelancer", "frilancer",
            "o'zimiz qilamiz", "tanishim dasturchi", "o'zi yozadi"
        ],
        their_strength="Moslashtirilgan yechim va past dastlabki narx",
        their_weakness=(
            "Doimiy qo'llab-quvvatlash yo'q, dasturchi ketsa tizim ishlamaydi, "
            "AI/ML integratsiyasi uchun maxsus bilim kerak, "
            "AI modellar yangilanishi bilan mos sozlash qiyin."
        ),
        reframe_talk_track=(
            "Zo'r — shaxsiy dasturchi moslashuvchanlik beradi. "
            "Lekin bitta savol: u AI modellarini yangilab turishi va "
            "24/7 qo'llab-quvvatlashni kafolatlayaptimi?"
        ),
        landmine_question=(
            "Agar dasturchi tizimdan ketsa yoki boshqa loyihaga o'tsa, "
            "siz qancha vaqt va pul sarflab qayta qurish kerak bo'ladi?"
        )
    ),

    # 4. Boshqa mahalliy AI botlar
    Battlecard(
        name="Boshqa Mahalliy AI Botlar",
        keywords=[
            "boshqa bot", "o'zbekiston bot", "mahalliy bot", "local bot",
            "o'zbek bot", "boshqa ai", "raqobatchi tizim"
        ],
        their_strength="Mahalliy bozorni bilishi va narx afzalligi",
        their_weakness=(
            "Hybrid RAG yo'q, o'zbek tilidagi NLP zaif, "
            "SPIN/Challenger savdo metodologiyasi yo'q, "
            "faqat FAQ bot darajasida ishlashi mumkin."
        ),
        reframe_talk_track=(
            "Mahalliy yechimlar yaxshi alternativ. "
            "Faqat bitta savol: u tizim mijoz 'qimmat' deganda e'tirozni professional yopib, "
            "xaridga yo'naltira oladimi?"
        ),
        landmine_question=(
            "Shu tizim SPIN savdo bosqichlarini o'zi boshqarib, "
            "har bir mijozning 'og'riq nuqtasi'ni aniqlab, buyurtmani o'zi yopa oladimi?"
        )
    ),

    # 5. WhatsApp/Telegram oddiy guruh boshqaruvi
    Battlecard(
        name="Oddiy Guruh / Manual Boshqaruv",
        keywords=[
            "guruh boshqaramiz", "o'zimiz javob beramiz", "operator bor",
            "menejer bor", "xodim bor", "qo'lda bajaramiz", "manually"
        ],
        their_strength="Insoniy muloqot va moslashuvchanlik",
        their_weakness=(
            "24/7 ishlolmaydi, tunda yoki dam olish kunlari javob kechikadi, "
            "bir vaqtda faqat bir suhbat, xodim charchashi va xatolari."
        ),
        reframe_talk_track=(
            "Insoniy muloqot juda muhim — bu siz uchun ustunlik. "
            "Lekin statistikaga ko'ra, tunda yoki kechqurun kelgan so'rovlar — "
            "ertasi kuni javob olsa, 70% allaqachon raqobatchiga buyurtma bergan bo'ladi."
        ),
        landmine_question=(
            "Sizning menejeringiz tunda soat 2:00 da kelgan 'narxi qancha?' "
            "savoliga darhol javob bera oladimi?"
        )
    ),
]


class BattlecardEngine:
    def __init__(self, battlecards: Optional[List[Battlecard]] = None):
        self.battlecards = battlecards or DEFAULT_BATTLECARDS

    def detect_competitor(self, user_message: str) -> Optional[Battlecard]:
        """Detects if user message contains reference to a known competitor category."""
        msg = user_message.lower()
        for card in self.battlecards:
            for kw in card.keywords:
                if kw in msg:
                    return card
        return None

    def generate_counter_response(self, card: Battlecard) -> str:
        """
        Constructs a full AECR + Landmine response:
        Acknowledge → Reframe → Landmine Question
        """
        return (
            f"{card.reframe_talk_track}\n\n"
            f"{card.landmine_question}"
        )

    def add_battlecard(self, battlecard: Battlecard):
        """Dynamically adds a new battlecard (from DB or admin panel)."""
        self.battlecards.append(battlecard)
