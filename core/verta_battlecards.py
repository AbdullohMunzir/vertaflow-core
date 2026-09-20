# /home/kinfolkt/verta-platform/core/verta_battlecards.py
"""
VertaFlow — Competitive Battlecards & Strategic Objection Engine
Transforms competitor mentions into non-aggressive reframes and strategic landmine questions.
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


# Preloaded battlecards for market alternatives
DEFAULT_BATTLECARDS = [
    Battlecard(
        name="Arzon Tugmali Botlar",
        keywords=["arzon bot", "oddiy bot", "boshqa joyda arzon", "800 ming", "500 ming", "telegram bot"],
        their_strength="Boshlang'ich narxi pastligi",
        their_weakness="E'tirozlarni yopa olmasligi, odamlarni sovitib mijoz yo'qotishi",
        reframe_talk_track="To'g'ri, ular boshida arzon ko'rinishi mumkin. Lekin oddiy tugmali bot mijoz savollariga javob berolmay, har kuni 2-3 ta xaridorni yo'qotsa — bu oyiga $1,000 dan ko'p zarar degani.",
        landmine_question="Sizga shunchaki tugmali menyu kerakmi yoki buyurtmalarni o'zi yopadigan sotuvchi agentmi?"
    ),
    Battlecard(
        name="Katta Murakkab Tizimlar (Global CRM)",
        keywords=["bitrix", "amocrm", "katta tizim", "murakkab dastur"],
        their_strength="Global brend va keng funksional",
        their_weakness="O'rnatish 2-3 oy vaqt olishi, xodimlar o'rgana olmasligi",
        reframe_talk_track="Ular katta va nufuzli tizimlar. Biroq ularni sozlash uchun oylab vaqt va alohida mutaxassis kerak bo'ladi.",
        landmine_question="Sizga 2 oy kutiladigan murakkab tizim kerakmi yoki 24 soatda ishga tushib 1-kundan sotuv keltiradigan yechimmi?"
    )
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
        """Constructs an AECR reframe response with landmine question."""
        return (
            f"{card.reframe_talk_track}\n\n"
            f"{card.landmine_question}"
        )
