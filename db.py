# /home/kinfolkt/verta-platform/db.py
"""
VertaFlow — SQLite Database & Persistence Layer
Stores businesses, conversations, messages, qualified leads, battlecards, and settings.
Zero external database dependencies, persistent across server restarts.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "vertaflow.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite schema and seeds default data if tables are empty."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Businesses Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS businesses (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        avg_check TEXT,
        faq_list TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Conversations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        session_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        channel TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        script_preference TEXT DEFAULT 'latin',
        autopilot_enabled INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Messages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        sender TEXT NOT NULL, -- 'user', 'agent', 'operator'
        text TEXT NOT NULL,
        stage TEXT,
        script TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES conversations(session_id)
    );
    """)

    # 4. Leads Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        session_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        channel TEXT NOT NULL,
        phone TEXT,
        pain TEXT,
        volume TEXT,
        timeline TEXT,
        score INTEGER DEFAULT 0,
        tier TEXT DEFAULT 'COLD ❄️',
        stage TEXT DEFAULT '1_INTRO',
        script TEXT DEFAULT 'latin',
        score_reasons TEXT, -- JSON array
        dossier TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Battlecards Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battlecards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        keywords TEXT NOT NULL, -- JSON array
        their_strength TEXT,
        their_weakness TEXT,
        reframe_talk_track TEXT,
        landmine_question TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    conn.commit()

    # Seed default business if not exists
    cursor.execute("SELECT COUNT(*) FROM businesses;")
    if cursor.fetchone()[0] == 0:
        default_faqs = [
            {"question": "Narxi qancha?", "answer": "Metri 2.5 mln so'mdan boshlanadi, o'lchamga qarab hisoblanadi."},
            {"question": "Yetkazib berasizmi?", "answer": "Ha, butun Toshkent bo'ylab bepul yetkazib o'rnatamiz."},
            {"question": "Kafolat bormi?", "answer": "5 yil rasmiy kafolat beramiz."}
        ]
        cursor.execute("""
            INSERT INTO businesses (id, name, description, avg_check, faq_list)
            VALUES (?, ?, ?, ?, ?);
        """, ("default", "Mebel Fabrikasi", "Oshxona va uy mebellari ishlab chiqarish", "5 000 000 so'm", json.dumps(default_faqs, ensure_ascii=False)))

    # Seed default battlecards if not exists
    cursor.execute("SELECT COUNT(*) FROM battlecards;")
    if cursor.fetchone()[0] == 0:
        default_cards = [
            (
                "Arzon Tugmali Botlar",
                json.dumps(["arzon bot", "oddiy bot", "boshqa joyda arzon", "800 ming", "500 ming", "telegram bot"], ensure_ascii=False),
                "Boshlang'ich narxi pastligi",
                "E'tirozlarni yopa olmasligi, odamlarni sovitib mijoz yo'qotishi",
                "To'g'ri, ular boshida arzon ko'rinishi mumkin. Lekin oddiy tugmali bot mijoz savollariga javob berolmay, har kuni 2-3 ta xaridorni yo'qotsa — bu oyiga $1,000 dan ko'p zarar degani.",
                "Sizga shunchaki tugmali menyu kerakmi yoki buyurtmalarni o'zi yopadigan sotuvchi agentmi?"
            ),
            (
                "Katta Murakkab Tizimlar (Global CRM)",
                json.dumps(["bitrix", "amocrm", "katta tizim", "murakkab dastur"], ensure_ascii=False),
                "Global brend va keng funksional",
                "O'rnatish 2-3 oy vaqt olishi, xodimlar o'rgana olmasligi",
                "Ular katta va nufuzli tizimlar. Biroq ularni sozlash uchun oylab vaqt va alohida mutaxassis kerak bo'ladi.",
                "Sizga 2 oy kutiladigan murakkab tizim kerakmi yoki 24 soatda ishga tushib 1-kundan sotuv keltiradigan yechimmi?"
            )
        ]
        cursor.executemany("""
            INSERT INTO battlecards (name, keywords, their_strength, their_weakness, reframe_talk_track, landmine_question)
            VALUES (?, ?, ?, ?, ?, ?);
        """, default_cards)

    # Seed sample conversations and leads if empty
    cursor.execute("SELECT COUNT(*) FROM conversations;")
    if cursor.fetchone()[0] == 0:
        seed_sample_data(cursor)

    conn.commit()
    conn.close()

def seed_sample_data(cursor):
    """Populates realistic initial leads to verify UI on first launch."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Lead 1: Jamshid aka (Kirill, Hot)
    cursor.execute("""
        INSERT INTO conversations (session_id, name, channel, script_preference, autopilot_enabled, updated_at)
        VALUES ('sess_jamshid', 'Jamshid aka (Mebel Fabrikasi)', 'telegram', 'cyrillic', 1, ?);
    """, (now,))
    cursor.execute("""
        INSERT INTO leads (session_id, name, channel, phone, pain, volume, timeline, score, tier, stage, script, score_reasons, dossier, updated_at)
        VALUES ('sess_jamshid', 'Jamshid aka (Mebel Fabrikasi)', 'telegram', '+998901234567', 
        '30-40 ta buyurtmada menejerlar kechikmoqda', '30-40 ta buyurtma', 'Shu hafta ichida', 100, 'HOT 🔥', '7_CLOSING', 'cyrillic',
        ?, ?, ?);
    """, (
        json.dumps(["+20 ball: Hajm va ko'lam ma'lumoti", "+25 ball: Asosiy og'riq aniqlandi", "+30 ball: Telefon raqami qoldirildi", "+15 ball: Xarid muddati aniq"]),
        "📋 VERTA LEAD DOSSIER (HOT 🔥 • 100/100):\n👤 Mijoz: Jamshid aka (+998901234567)\n🎯 Asosiy og'riq: 30-40 ta buyurtmada menejerlar kechikmoqda\n⏳ Muddat: Shu hafta ichida • Standart tarif\n⚠️ E'tiroz: Yo'q",
        now
    ))
    cursor.executemany("""
        INSERT INTO messages (session_id, sender, text, stage, script, timestamp)
        VALUES (?, ?, ?, ?, ?, ?);
    """, [
        ('sess_jamshid', 'user', 'Салом, мебел фабрикамиз учун crm тизими нархи қанча?', '1_INTRO', 'cyrillic', now),
        ('sess_jamshid', 'agent', 'Ассалому алайкум! Тизимимиз 1.5 млн сўмдан бошланади.\nСизга энг маъқулини ҳисоблашимиз учун: ҳозир кунига нечта буюртма қабул қиляпсиз?', '2_SITUATION', 'cyrillic', now),
        ('sess_jamshid', 'user', 'Кунига 30-40 та буюртма тушади, лекин сотувчиларимиз улгурмай мижозларни совитиб қўйяпти.', '3_PROBLEM', 'cyrillic', now),
        ('sess_jamshid', 'agent', 'Тушунарли. Айнан шу ҳажмда кўп корхоналарда менежерлар кечикиши кузатилади.\nҲозирда савдо бўлимингизда энг кўп вақт ва мижоз йўқотилаётган жойи қаерда?', '3_PROBLEM', 'cyrillic', now),
        ('sess_jamshid', 'user', 'Шу ҳафта ўрнатмоқчимиз. Мана рақамим: +998901234567', '7_CLOSING', 'cyrillic', now),
        ('sess_jamshid', 'agent', 'Келинг, 10 дақиқалик қисқа консультацияда сизнинг корхонангиз учун ҳисоблаб берамиз.\nҚайси вақт маъқул: бугун 16:00 ми ёки эртага 11:00?', '7_CLOSING', 'cyrillic', now)
    ])

    # Lead 2: Farhod Aliyev (Lotin, Hot)
    cursor.execute("""
        INSERT INTO conversations (session_id, name, channel, script_preference, autopilot_enabled, updated_at)
        VALUES ('sess_farhod', 'Farhod Aliyev', 'web_widget', 'latin', 1, ?);
    """, (now,))
    cursor.execute("""
        INSERT INTO leads (session_id, name, channel, phone, pain, volume, timeline, score, tier, stage, script, score_reasons, dossier, updated_at)
        VALUES ('sess_farhod', 'Farhod Aliyev', 'web_widget', '998977654321', 
        'Hozir 5 ta operatorimiz bor, mijozlarga kech javob berib ulgurmayapti', '5 ta operator', 'Tezroq joriy qilish kerak', 85, 'HOT 🔥', '7_CLOSING', 'latin',
        ?, ?, ?);
    """, (
        json.dumps(["+20 ball: Operatorlar soni", "+25 ball: Kechikish muammosi", "+30 ball: Telefon raqami"]),
        "📋 VERTA LEAD DOSSIER (HOT 🔥 • 85/100):\n👤 Mijoz: Farhod Aliyev (998977654321)\n🎯 Asosiy og'riq: 5 ta operator ulgurmayapti\n⏳ Muddat: Tezroq joriy qilish kerak",
        now
    ))
    cursor.executemany("""
        INSERT INTO messages (session_id, sender, text, stage, script, timestamp)
        VALUES (?, ?, ?, ?, ?, ?);
    """, [
        ('sess_farhod', 'user', 'Assalomu alaykum, ulgurji savdo do\'konimizga tizim joriy qilmoqchimiz.', '1_INTRO', 'latin', now),
        ('sess_farhod', 'agent', 'Assalomu alaykum! Tizimimiz 1.5 mln so\'mdan boshlanadi.\nSizga eng ma\'qulini hisoblashimiz uchun: hozir kuniga nechta buyurtma qabul qilyapsiz?', '2_SITUATION', 'latin', now),
        ('sess_farhod', 'user', 'Hozir 5 ta operatorimiz bor, mijozlarga kech javob berib ulgurmayapti. Telefonim 998977654321, tezroq joriy qilish kerak.', '7_CLOSING', 'latin', now),
        ('sess_farhod', 'agent', 'Keling, 10 daqiqalik qisqa konsultatsiyada sizning korxonangiz uchun hisoblab beramiz.\nQaysi vaqt ma\'qul: bugun 16:00 mi yoki ertaga 11:00?', '7_CLOSING', 'latin', now)
    ])

# Database Helper Functions

def get_business_profile(biz_id: str = "default") -> Dict[str, Any]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM businesses WHERE id = ?;", (biz_id,)).fetchone()
    conn.close()
    if not row:
        return {
            "business_name": "Mebel Fabrikasi",
            "business_desc": "Oshxona va uy mebellari ishlab chiqarish",
            "avg_check": "5 000 000 so'm",
            "faq_list": []
        }
    return {
        "business_name": row["name"],
        "business_desc": row["description"],
        "avg_check": row["avg_check"],
        "faq_list": json.loads(row["faq_list"] or "[]")
    }

def update_business_profile(name: str, desc: str, avg_check: str, faq_list: Optional[List[Dict[str, str]]] = None, biz_id: str = "default"):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    faqs_json = json.dumps(faq_list or [], ensure_ascii=False)
    conn.execute("""
        UPDATE businesses
        SET name = ?, description = ?, avg_check = ?, faq_list = ?, updated_at = ?
        WHERE id = ?;
    """, (name, desc, avg_check, faqs_json, now, biz_id))
    conn.commit()
    conn.close()

def list_conversations() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*, l.score, l.tier, l.phone,
               (SELECT text FROM messages WHERE session_id = c.session_id ORDER BY id DESC LIMIT 1) as last_message,
               (SELECT timestamp FROM messages WHERE session_id = c.session_id ORDER BY id DESC LIMIT 1) as last_time
        FROM conversations c
        LEFT JOIN leads l ON c.session_id = l.session_id
        ORDER BY c.updated_at DESC;
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_conversation(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM conversations WHERE session_id = ?;", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_or_update_conversation(session_id: str, name: str, channel: str = "telegram", script: str = "latin", autopilot: int = 1):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO conversations (session_id, name, channel, script_preference, autopilot_enabled, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            name = excluded.name,
            script_preference = excluded.script_preference,
            updated_at = excluded.updated_at;
    """, (session_id, name, channel, script, autopilot, now))
    conn.commit()
    conn.close()

def toggle_conversation_autopilot(session_id: str, enabled: bool):
    conn = get_connection()
    conn.execute("UPDATE conversations SET autopilot_enabled = ? WHERE session_id = ?;", (1 if enabled else 0, session_id))
    conn.commit()
    conn.close()

def add_message(session_id: str, sender: str, text: str, stage: Optional[str] = None, script: Optional[str] = None) -> int:
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (session_id, sender, text, stage, script, timestamp)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (session_id, sender, text, stage, script, now))
    msg_id = cursor.lastrowid
    conn.execute("UPDATE conversations SET updated_at = ? WHERE session_id = ?;", (now, session_id))
    conn.commit()
    conn.close()
    return msg_id

def get_messages(session_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC;
    """, (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_lead(session_id: str, name: str, channel: str, phone: Optional[str], pain: Optional[str],
              volume: Optional[str], timeline: Optional[str], score: int, tier: str, stage: str,
              script: str, score_reasons: List[str], dossier: Optional[str]):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reasons_json = json.dumps(score_reasons, ensure_ascii=False)
    conn.execute("""
        INSERT INTO leads (session_id, name, channel, phone, pain, volume, timeline, score, tier, stage, script, score_reasons, dossier, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            phone = COALESCE(excluded.phone, leads.phone),
            pain = COALESCE(excluded.pain, leads.pain),
            volume = COALESCE(excluded.volume, leads.volume),
            timeline = COALESCE(excluded.timeline, leads.timeline),
            score = excluded.score,
            tier = excluded.tier,
            stage = excluded.stage,
            script = excluded.script,
            score_reasons = excluded.score_reasons,
            dossier = COALESCE(excluded.dossier, leads.dossier),
            updated_at = excluded.updated_at;
    """, (session_id, name, channel, phone, pain, volume, timeline, score, tier, stage, script, reasons_json, dossier, now))
    conn.commit()
    conn.close()

def get_leads() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM leads ORDER BY score DESC;").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["score_reasons"] = json.loads(d["score_reasons"] or "[]")
        result.append(d)
    return result

def get_battlecards() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM battlecards ORDER BY id ASC;").fetchall()
    conn.close()
    cards = []
    for r in rows:
        cards.append({
            "id": r["id"],
            "name": r["name"],
            "keywords": json.loads(r["keywords"] or "[]"),
            "strength": r["their_strength"],
            "weakness": r["their_weakness"],
            "reframe": r["reframe_talk_track"],
            "landmine": r["landmine_question"]
        })
    return cards

def add_battlecard(name: str, keywords: List[str], weakness: str, reframe: str, landmine: str, strength: str = "Past narx"):
    conn = get_connection()
    conn.execute("""
        INSERT INTO battlecards (name, keywords, their_strength, their_weakness, reframe_talk_track, landmine_question)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (name, json.dumps(keywords, ensure_ascii=False), strength, weakness, reframe, landmine))
    conn.commit()
    conn.close()

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?;", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value;
    """, (key, value))
    conn.commit()
    conn.close()

def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings;").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

# Initialize database on module import
init_db()
