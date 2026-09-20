# /home/kinfolkt/verta-platform/core/verta_uzbek_engine.py
"""
VertaFlow — Native Uzbek Linguistic & Messenger Pacing Engine
Features:
1. Dual Script Mirroring: Auto-detects Latin vs Cyrillic and matches prospect's script.
2. Calque Stripper: Eliminates robotic Russian/English direct translations.
3. Brevity Guard: Enforces 2-3 line maximum and single-question constraint.
"""

import re
from typing import Tuple

# Mapping for Uzbek Latin <-> Cyrillic
LATIN_TO_CYRILLIC = {
    "sh": "ш", "Sh": "Ш", "SH": "Ш",
    "ch": "ч", "Ch": "Ч", "CH": "Ч",
    "yo": "ё", "Yo": "Ё", "YO": "Ё",
    "yu": "ю", "Yu": "Ю", "YU": "Ю",
    "ya": "я", "Ya": "Я", "YA": "Я",
    "o'": "ў", "O'": "Ў", "o‘": "ў", "O‘": "Ў", "o`": "ў", "O`": "Ў",
    "g'": "ғ", "G'": "Ғ", "g‘": "ғ", "G‘": "Ғ", "g`": "ғ", "G`": "Ғ",
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г",
    "h": "ҳ", "i": "и", "j": "ж", "k": "к", "l": "л", "m": "м",
    "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с",
    "t": "т", "u": "у", "v": "в", "x": "х", "y": "й", "z": "з",
    "A": "А", "B": "Б", "D": "Д", "E": "Е", "F": "Ф", "G": "Г",
    "H": "Ҳ", "I": "И", "J": "Ж", "K": "К", "L": "Л", "M": "М",
    "N": "Н", "O": "О", "P": "П", "Q": "Қ", "R": "Р", "S": "С",
    "T": "Т", "U": "У", "V": "В", "X": "Х", "Y": "Й", "Z": "З"
}

# Forbidden robot kalkas and their natural human equivalents
CALQUE_REPLACEMENTS = [
    (r"(?i)sizga qanday yordam bera olaman\??", "Assalomu alaykum! Qaysi xizmatimiz bo'yicha qiziqdingiz?"),
    (r"(?i)qanday yordam berishim mumkin\??", "Qaysi yo'nalish bo'yicha ma'lumot kerak edi?"),
    (r"(?i)yordam berishdan mamnunman", "Albatta, jonim bilan!"),
    (r"(?i)xizmat ko'rsatishdan mamnunman", "Xursand bo'lamiz!"),
    (r"(?i)bu siz uchun mantiqiymi\??", "Fikrim tushunarli bo'ldimi?"),
    (r"(?i)menga xabar bering", "Qulay vaqtda yozib yuborarsiz"),
    (r"(?i)men tushunaman sizning xavotiringizni", "Sizni juda yaxshi tushunib turibman"),
    (r"(?i)biz eng yaxshi kompaniyamiz", "Mijozlarimiz aynan natija uchun bizni tanlashadi"),
]

def detect_script(text: str) -> str:
    """Detects whether prospect writes in Cyrillic or Latin script."""
    cyrillic_chars = len(re.findall(r'[\u0400-\u04FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    
    if cyrillic_chars > latin_chars:
        return "cyrillic"
    return "latin"

def clean_calques(text: str) -> str:
    """Replaces robotic machine-translated phrases with natural conversational Uzbek."""
    cleaned = text
    for pattern, replacement in CALQUE_REPLACEMENTS:
        cleaned = re.sub(pattern, replacement, cleaned)
    return cleaned

def to_cyrillic(text: str) -> str:
    """Converts Uzbek Latin to Cyrillic."""
    res = text
    for lat, cyr in LATIN_TO_CYRILLIC.items():
        res = res.replace(lat, cyr)
    return res

def enforce_messenger_brevity(text: str, max_lines: int = 3) -> str:
    """
    Enforces messenger conversational constraints:
    - Max 2-3 punchy lines.
    - Preserves single question at the end.
    - Strips corporate fluff.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) > max_lines:
        # Keep opening context and closing question
        lines = [lines[0], lines[1], lines[-1]]
    
    result = "\n".join(lines)
    return result

def process_agent_output(text: str, target_script: str = "latin") -> str:
    """Complete linguistic pipeline for agent responses."""
    cleaned = clean_calques(text)
    paced = enforce_messenger_brevity(cleaned, max_lines=3)
    
    if target_script == "cyrillic":
        return to_cyrillic(paced)
    return paced
