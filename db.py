# /home/kinfolkt/verta-platform/db.py
"""
VertaFlow — SQLite Database & Persistence Layer
Stores businesses, conversations, messages, qualified leads, battlecards, and settings.
Zero external database dependencies, persistent across server restarts.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "vertaflow.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception:
        pass
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

    # Schema migration for workspaces & billing
    for col_sql in [
        "ALTER TABLE businesses ADD COLUMN plan_id TEXT DEFAULT 'free';",
        "ALTER TABLE businesses ADD COLUMN plan_expires_at TIMESTAMP;",
        "ALTER TABLE businesses ADD COLUMN billing_period INTEGER DEFAULT 1;",
        "ALTER TABLE businesses ADD COLUMN niche TEXT DEFAULT 'general';"
    ]:
        try:
            cursor.execute(col_sql)
        except Exception:
            pass

    # Payments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id TEXT NOT NULL,
        plan_id TEXT NOT NULL,
        period_months INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        payment_method TEXT NOT NULL,
        status TEXT DEFAULT 'paid',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Users Table (Email, Telegram, Instagram, WhatsApp registration)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        auth_method TEXT NOT NULL,
        identifier TEXT NOT NULL,
        full_name TEXT,
        password_hash TEXT,
        selected_plan TEXT DEFAULT 'free',
        active_workspace_id TEXT DEFAULT 'default',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Real User Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    );
    """)

    # Server-Authoritative Token Usage & Audit Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS token_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id TEXT NOT NULL,
        session_id TEXT,
        model TEXT,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_ws_time ON token_usage(workspace_id, created_at DESC);")

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
        workspace_id TEXT DEFAULT 'default',
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

    # 6b. Follow-ups Table (Smart Re-engagement)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS follow_ups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        name TEXT,
        follow_up_step INTEGER DEFAULT 1,
        status TEXT DEFAULT 'pending',
        scheduled_at TIMESTAMP,
        sent_at TIMESTAMP,
        follow_up_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES conversations(session_id)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_ups_status ON follow_ups(status, scheduled_at);")

    # 7. Knowledge Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        item_type TEXT NOT NULL, -- 'file', 'url', 'faq', 'text'
        content TEXT NOT NULL,
        metadata TEXT, -- JSON
        workspace_id TEXT DEFAULT 'default',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 8. Channels Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        channel_id TEXT PRIMARY KEY, -- 'instagram', 'telegram', 'whatsapp', 'web_widget'
        channel_name TEXT NOT NULL,
        is_connected INTEGER DEFAULT 0,
        config TEXT, -- JSON
        last_sync TIMESTAMP
    );
    """)

    # 9. Knowledge Chunks Table (Production RAG with Embeddings)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding TEXT, -- JSON array of floats (gemini-embedding-001)
        metadata TEXT,  -- JSON
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES knowledge_items(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_parent ON knowledge_chunks(parent_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_time ON messages(session_id, timestamp ASC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_items(item_type);")

    # 10. Analytics Events Table (Native privacy-first telemetry)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analytics_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        page TEXT NOT NULL,
        metadata TEXT,
        client_ip_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(event_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_time ON analytics_events(created_at DESC);")

    # Migrations for existing DBs
    try:
        cursor.execute("ALTER TABLE knowledge_items ADD COLUMN workspace_id TEXT DEFAULT 'default';")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE battlecards ADD COLUMN workspace_id TEXT DEFAULT 'default';")
    except Exception:
        pass
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_ws ON knowledge_items(workspace_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battlecards_ws ON battlecards(workspace_id);")

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
        """, ("default", "Mening Korxonam", "AI sotuv agenti bilan jihozlangan korxona", "1 000 000 so'm", json.dumps(default_faqs, ensure_ascii=False)))

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

    # Seed default knowledge items if not exists
    cursor.execute("SELECT COUNT(*) FROM knowledge_items;")
    if cursor.fetchone()[0] == 0:
        default_knowledge = [
            (
                "Mebel Mahsulotlari va Narxlari 2026.pdf",
                "file",
                "Oshxona mebellari: 1 pogon metri 2 500 000 so'mdan 6 000 000 so'mgacha (MDF, Akril, Shpon va bo'yalgan emal). Yotoqxona to'plamlari (krovat, shkaf, tumba, tryumo): 8 000 000 so'mdan 25 000 000 so'mgacha. Shkaf-kupe: 1 metri 1 800 000 so'mdan boshlanadi. Buyurtma asosida 7-10 ish kunida tayyorlanadi. Bepul o'lchov olish (zamer) xizmati mavjud.",
                json.dumps({"file_size": "245 KB", "category": "Katalog va Narxlar"}, ensure_ascii=False)
            ),
            (
                "Yetkazib berish va o'rnatish shartlari qanday?",
                "faq",
                "Toshkent shahri bo'ylab bepul yetkazib va professional ustalarimiz tomonidan o'rnatib beriladi. Viloyatlarga masofaga qarab kelishilgan hamyonbop narxda yetkaziladi.",
                json.dumps({"category": "Yetkazib berish"}, ensure_ascii=False)
            ),
            (
                "To'lov usullari va bo'lib to'lash (muddatli to'lov) bormi?",
                "faq",
                "Naqd pul, Payme, Click va bank hisob raqamiga o'tkazma (perechislenie) qabul qilinadi. Shuningdek, 3 oydan 12 oygacha ortiqcha foizsiz muddatli to'lov (rassrochka) imkoniyati mavjud.",
                json.dumps({"category": "To'lov"}, ensure_ascii=False)
            ),
            (
                "Mahsulotlarga kafolat bormi va materiallar qayerdan?",
                "faq",
                "Barcha mebellarimizga 5 yillik rasmiy kafolat beramiz. Furnituralar Turkiya va Avstriya (Blum, Samet), laminat va MDF plitalar Rossiya va Yevropaning sertifikatlangan zavodlaridan keltiriladi.",
                json.dumps({"category": "Kafolat va Sifat"}, ensure_ascii=False)
            ),
            (
                "Rasmiy Sayt: mebelfabrika.uz",
                "url",
                "Mebel Fabrikasi — Toshkent shahridagi zamonaviy korxona. Biz 2018-yildan buyon 10,000 dan ortiq xonadon va ofislarga mebel yetkazib berdik. Manzil: Toshkent sh., Chilonzor 9-mavze, 12-uy. Ish vaqti: Har kuni 09:00 dan 20:00 gacha. Telefon: +998 (71) 200-00-00.",
                json.dumps({"url": "https://mebelfabrika.uz", "status": "Faol"}, ensure_ascii=False)
            )
        ]
        cursor.executemany("""
            INSERT INTO knowledge_items (title, item_type, content, metadata)
            VALUES (?, ?, ?, ?);
        """, default_knowledge)

    # Seed default channels if not exists
    cursor.execute("SELECT COUNT(*) FROM channels;")
    if cursor.fetchone()[0] == 0:
        default_channels = [
            (
                "instagram",
                "Instagram Direct",
                0,
                json.dumps({
                    "account_name": "@mebel_premium_uz",
                    "page_id": "",
                    "access_token": "",
                    "verify_token": "verta_ig_token_99",
                    "auto_reply_comments": True,
                    "auto_reply_direct": True,
                    "webhook_url": "http://127.0.0.1:8000/api/webhooks/instagram"
                }, ensure_ascii=False)
            ),
            (
                "telegram",
                "Telegram Bot",
                0,
                json.dumps({
                    "bot_token": "",
                    "bot_username": "@vertaflow_bot",
                    "manager_chat_id": ""
                }, ensure_ascii=False)
            ),
            (
                "whatsapp",
                "WhatsApp Business",
                0,
                json.dumps({
                    "phone_number": "+998 90 123 45 67",
                    "status": "disconnected",
                    "qr_code": "verta_wa_qr_sim",
                    "webhook_url": "http://127.0.0.1:8000/api/webhooks/whatsapp"
                }, ensure_ascii=False)
            ),
            (
                "web_widget",
                "Web Chat Vidjet",
                1,
                json.dumps({
                    "theme_color": "#B5F87B",
                    "title": "Mebel Fabrikasi",
                    "subtitle": "24/7 AI Maslahatchi",
                    "widget_url": "http://127.0.0.1:8000/static/widget.js",
                    "position": "right"
                }, ensure_ascii=False)
            )
        ]
        cursor.executemany("""
            INSERT INTO channels (channel_id, channel_name, is_connected, config)
            VALUES (?, ?, ?, ?);
        """, default_channels)

    # Sample data seeding is disabled to prevent dummy data pollution on new accounts.
    # seed_sample_data(cursor) can be invoked explicitly in isolated test suites if needed.

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

def get_business_profile(biz_id: Optional[str] = None) -> Dict[str, Any]:
    if not biz_id:
        biz_id = get_active_workspace_id()
    conn = get_connection()
    row = conn.execute("SELECT * FROM businesses WHERE id = ?;", (biz_id,)).fetchone()
    conn.close()
    if not row:
        return {
            "business_name": "Mening Korxonam",
            "business_desc": "AI sotuv agenti bilan jihozlangan korxona",
            "avg_check": "1 000 000 so'm",
            "faq_list": []
        }
    return {
        "business_name": row["name"],
        "business_desc": row["description"],
        "avg_check": row["avg_check"],
        "faq_list": json.loads(row["faq_list"] or "[]")
    }

def update_business_profile(name: str, desc: str, avg_check: str, faq_list: Optional[List[Dict[str, str]]] = None, biz_id: Optional[str] = None):
    if not biz_id:
        biz_id = get_active_workspace_id()
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

def get_battlecards(workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    conn = get_connection()
    rows = conn.execute("SELECT * FROM battlecards WHERE workspace_id = ? ORDER BY id ASC;", (workspace_id,)).fetchall()
    if not rows and workspace_id != "default":
        rows = conn.execute("SELECT * FROM battlecards WHERE workspace_id = 'default' ORDER BY id ASC;").fetchall()
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

def add_battlecard(name: str, keywords: List[str], weakness: str, reframe: str, landmine: str, strength: str = "Past narx", workspace_id: Optional[str] = None):
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    conn = get_connection()
    conn.execute("""
        INSERT INTO battlecards (name, keywords, their_strength, their_weakness, reframe_talk_track, landmine_question, workspace_id)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (name, json.dumps(keywords, ensure_ascii=False), strength, weakness, reframe, landmine, workspace_id))
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

# ----------------- KNOWLEDGE BASE HELPERS -----------------

def list_knowledge_items(workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    conn = get_connection()
    rows = conn.execute("SELECT * FROM knowledge_items WHERE workspace_id = ? ORDER BY id DESC;", (workspace_id,)).fetchall()
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        d["metadata"] = json.loads(d["metadata"] or "{}")
        items.append(d)
    return items

def add_knowledge_item(title: str, item_type: str, content: str, metadata: Optional[Dict[str, Any]] = None, workspace_id: Optional[str] = None) -> int:
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    conn = get_connection()
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO knowledge_items (title, item_type, content, metadata, workspace_id)
        VALUES (?, ?, ?, ?, ?);
    """, (title, item_type, content, meta_json, workspace_id))
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id

def delete_knowledge_item(item_id: int, workspace_id: Optional[str] = None):
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    conn = get_connection()
    conn.execute("DELETE FROM knowledge_chunks WHERE parent_id IN (SELECT id FROM knowledge_items WHERE id = ? AND workspace_id = ?);", (item_id, workspace_id))
    conn.execute("DELETE FROM knowledge_items WHERE id = ? AND workspace_id = ?;", (item_id, workspace_id))
    conn.commit()
    conn.close()

def delete_knowledge_items_batch(item_ids: List[int], workspace_id: Optional[str] = None) -> int:
    if not item_ids:
        return 0
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    conn = get_connection()
    placeholders = ",".join("?" for _ in item_ids)
    params = list(item_ids) + [workspace_id]
    conn.execute(f"DELETE FROM knowledge_chunks WHERE parent_id IN (SELECT id FROM knowledge_items WHERE id IN ({placeholders}) AND workspace_id = ?);", params)
    cur = conn.execute(f"DELETE FROM knowledge_items WHERE id IN ({placeholders}) AND workspace_id = ?;", params)
    deleted_count = cur.rowcount
    conn.commit()
    conn.close()
    return deleted_count

# ----------------- KNOWLEDGE CHUNKS (RAG) HELPERS -----------------

def add_chunk(
    parent_id: int,
    chunk_index: int,
    content: str,
    embedding: Optional[List[float]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    emb_json = json.dumps(embedding) if embedding else None
    meta_json = json.dumps(metadata or {})
    cursor.execute("""
        INSERT INTO knowledge_chunks (parent_id, chunk_index, content, embedding, metadata)
        VALUES (?, ?, ?, ?, ?);
    """, (parent_id, chunk_index, content, emb_json, meta_json))
    chunk_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return chunk_id

def add_chunks_batch(chunks: List[Dict[str, Any]]):
    if not chunks:
        return
    conn = get_connection()
    cursor = conn.cursor()
    data = []
    for c in chunks:
        emb_json = json.dumps(c.get("embedding")) if c.get("embedding") else None
        meta_json = json.dumps(c.get("metadata") or {})
        data.append((
            c["parent_id"],
            c["chunk_index"],
            c["content"],
            emb_json,
            meta_json
        ))
    cursor.executemany("""
        INSERT INTO knowledge_chunks (parent_id, chunk_index, content, embedding, metadata)
        VALUES (?, ?, ?, ?, ?);
    """, data)
    conn.commit()
    conn.close()

def delete_chunks_for_item(parent_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM knowledge_chunks WHERE parent_id = ?;", (parent_id,))
    conn.commit()
    conn.close()

def get_all_chunks() -> List[Dict[str, Any]]:
    """Retrieves all indexed chunks with decoded embeddings and metadata for RAG."""
    conn = get_connection()
    rows = conn.execute("SELECT id, parent_id, chunk_index, content, embedding, metadata, created_at FROM knowledge_chunks ORDER BY parent_id, chunk_index;").fetchall()
    conn.close()
    chunks = []
    for r in rows:
        emb_val = None
        if r["embedding"]:
            try:
                emb_val = json.loads(r["embedding"])
            except Exception:
                emb_val = None
        meta_val = {}
        if r["metadata"]:
            try:
                meta_val = json.loads(r["metadata"])
            except Exception:
                meta_val = {}
        chunks.append({
            "id": r["id"],
            "parent_id": r["parent_id"],
            "chunk_index": r["chunk_index"],
            "content": r["content"],
            "embedding": emb_val,
            "metadata": meta_val,
            "created_at": r["created_at"]
        })
    return chunks

def get_chunks_for_item(parent_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT id, parent_id, chunk_index, content, embedding, metadata FROM knowledge_chunks WHERE parent_id = ? ORDER BY chunk_index;", (parent_id,)).fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        d["embedding"] = json.loads(d["embedding"]) if d["embedding"] else None
        d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
        res.append(d)
    return res

def get_chunks_count() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) FROM knowledge_chunks;").fetchone()
    conn.close()
    return row[0] if row else 0

def get_all_knowledge_text() -> str:
    """Concatenates all knowledge items into structured text for LLM injection."""
    items = list_knowledge_items()
    if not items:
        return ""
    blocks = ["### KORXONA RASMIY BILIMLAR BAZASI (FAQ, NARXLAR, KATALOG):"]
    for item in items:
        blocks.append(f"📌 [{item['item_type'].upper()}] {item['title']}:\n{item['content']}")
    return "\n\n".join(blocks)

# ----------------- CHANNELS HELPERS -----------------

def list_channels() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM channels ORDER BY channel_id ASC;").fetchall()
    conn.close()
    chans = []
    for r in rows:
        d = dict(r)
        d["config"] = json.loads(d["config"] or "{}")
        chans.append(d)
    return chans

def get_channel(channel_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM channels WHERE channel_id = ?;", (channel_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["config"] = json.loads(d["config"] or "{}")
    return d

def update_channel(channel_id: str, is_connected: Optional[int] = None, config: Optional[Dict[str, Any]] = None):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current = get_channel(channel_id)
    if not current:
        conn.close()
        return
    new_conn = is_connected if is_connected is not None else current["is_connected"]
    new_conf = current["config"]
    if config is not None:
        new_conf.update(config)
    
    conn.execute("""
        UPDATE channels
        SET is_connected = ?, config = ?, last_sync = ?
        WHERE channel_id = ?;
    """, (new_conn, json.dumps(new_conf, ensure_ascii=False), now, channel_id))
    conn.commit()
    conn.close()

# ----------------- AGENT PERSONA HELPERS -----------------

def get_agent_persona(workspace_id: Optional[str] = None) -> Dict[str, Any]:
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    raw = get_setting(f"agent_persona_{workspace_id}")
    if not raw and workspace_id == "default":
        raw = get_setting("agent_persona")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    ws = get_workspace(workspace_id)
    ws_name = ws.get("name", "Mening Korxonam") if ws else "Mening Korxonam"
    return {
        "name": "Madina",
        "role": "Sotuv bo'yicha bosh maslahatchi",
        "avatar": "female_consultant",
        "tone": "friendly_closer",
        "tone_label": "Samimiy & Savdo yopuvchi",
        "greeting": f"Assalomu alaykum! {ws_name}ga xush kelibsiz. Sizga qanday yordam bera olaman?",
        "max_discount": "10%",
        "rules": {
            "on_operator_request": True,
            "on_complaint": True,
            "on_payment_receipt": True
        }
    }

def update_agent_persona(persona: Dict[str, Any], workspace_id: Optional[str] = None):
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    set_setting(f"agent_persona_{workspace_id}", json.dumps(persona, ensure_ascii=False))
    if workspace_id == "default":
        set_setting("agent_persona", json.dumps(persona, ensure_ascii=False))

# ----------------- DASHBOARD STATS HELPERS -----------------

def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_connection()
    total_convs = conn.execute("SELECT COUNT(*) FROM conversations;").fetchone()[0]
    total_leads = conn.execute("SELECT COUNT(*) FROM leads;").fetchone()[0]
    hot_leads = conn.execute("SELECT COUNT(*) FROM leads WHERE score >= 70;").fetchone()[0]
    total_msgs = conn.execute("SELECT COUNT(*) FROM messages;").fetchone()[0]
    active_chans = conn.execute("SELECT COUNT(*) FROM channels WHERE is_connected = 1 AND channel_id != 'web_widget';").fetchone()[0]
    conn.close()
    return {
        "total_conversations": total_convs,
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "total_messages": total_msgs,
        "active_channels": active_chans,
        "avg_response_time": "1.1s" if total_convs > 0 else "0.0s",
        "conversion_rate": f"{round((hot_leads / max(total_convs, 1)) * 100, 1)}%" if total_convs > 0 else "0.0%"
    }

# ----------------- WORKSPACE & BILLING HELPERS -----------------

def get_active_workspace_id() -> str:
    active = get_setting("active_workspace_id")
    if not active:
        active = "default"
        set_setting("active_workspace_id", "default")
    return active

def set_active_workspace_id(workspace_id: str):
    set_setting("active_workspace_id", workspace_id)

def get_workspaces() -> List[Dict[str, Any]]:
    conn = get_connection()
    active_id = get_active_workspace_id()
    rows = conn.execute("SELECT * FROM businesses ORDER BY updated_at ASC;").fetchall()
    res = []
    for r in rows:
        d = dict(r)
        d["is_active"] = (d["id"] == active_id)
        d["plan_id"] = d.get("plan_id") or "free"
        res.append(d)
    conn.close()
    return res

def get_workspace(workspace_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM businesses WHERE id = ?;", (workspace_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["plan_id"] = d.get("plan_id") or "free"
        return d
    return None

def create_workspace(name: str, niche: str = "Chakana savdo", description: str = "", avg_check: str = "1 000 000 so'm") -> Dict[str, Any]:
    import uuid
    ws_id = "ws_" + uuid.uuid4().hex[:8]
    conn = get_connection()
    conn.execute("""
        INSERT INTO businesses (id, name, niche, description, avg_check, plan_id, billing_period)
        VALUES (?, ?, ?, ?, ?, 'free', 1);
    """, (ws_id, name, niche, description or f"{name} savdo boti", avg_check))
    conn.commit()
    conn.close()
    set_active_workspace_id(ws_id)
    return get_workspace(ws_id)

def delete_workspace(workspace_id: str) -> bool:
    if workspace_id == "default":
        return False
    conn = get_connection()
    conn.execute("DELETE FROM knowledge_chunks WHERE parent_id IN (SELECT id FROM knowledge_items WHERE workspace_id = ?);", (workspace_id,))
    conn.execute("DELETE FROM knowledge_items WHERE workspace_id = ?;", (workspace_id,))
    conn.execute("DELETE FROM battlecards WHERE workspace_id = ?;", (workspace_id,))
    conn.execute("DELETE FROM businesses WHERE id = ?;", (workspace_id,))
    conn.commit()
    conn.close()
    if get_active_workspace_id() == workspace_id:
        set_active_workspace_id("default")
    return True

def get_billing_info(workspace_id: Optional[str] = None) -> Dict[str, Any]:
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    ws = get_workspace(workspace_id)
    if not ws:
        ws = {"id": "default", "name": "Mebel Fabrikasi", "plan_id": "free", "billing_period": 1}
    
    plan_id = ws.get("plan_id") or "free"
    billing_period = ws.get("billing_period") or 1
    expires_at = ws.get("plan_expires_at")

    conn = get_connection()
    knowledge_count = conn.execute("SELECT COUNT(*) FROM knowledge_items WHERE workspace_id = ?;", (workspace_id,)).fetchone()[0]
    catalog_count = min(knowledge_count * 2, 8)
    ig_chan = conn.execute("SELECT is_connected FROM channels WHERE channel_id = 'instagram';").fetchone()
    tg_chan = conn.execute("SELECT is_connected FROM channels WHERE channel_id = 'telegram';").fetchone()
    ig_connected = 1 if ig_chan and ig_chan[0] == 1 else 0
    tg_connected = 1 if tg_chan and tg_chan[0] == 1 else 0

    pay_rows = conn.execute("""
        SELECT * FROM payments 
        WHERE workspace_id = ? 
        ORDER BY created_at DESC LIMIT 10;
    """, (workspace_id,)).fetchall()
    payments = [dict(p) for p in pay_rows]
    conn.close()

    plan_names = {
        "free": "Bepul",
        "pro": "Pro",
        "business": "Biznes"
    }

    cur_limit = PLAN_LIMITS.get(plan_id, PLAN_LIMITS["free"])
    token_stats = get_token_usage_stats(workspace_id)

    return {
        "workspace_id": workspace_id,
        "workspace_name": ws.get("name", "VertaFlow Loyiha"),
        "plan_id": plan_id,
        "plan_name": plan_names.get(plan_id, "Bepul"),
        "billing_period": billing_period,
        "expires_at": expires_at or "Cheksiz",
        "usage": {
            "knowledge": {"current": knowledge_count, "max": cur_limit["knowledge_max"]},
            "catalog": {"current": catalog_count, "max": cur_limit["catalog_max"]},
            "instagram": {"current": ig_connected, "max": cur_limit["instagram_max"]},
            "telegram": {"current": tg_connected, "max": cur_limit["telegram_max"]},
            "tokens": {"current": token_stats["total_tokens"], "max": cur_limit["tokens_max"]},
            "ai_responses": {"current": token_stats["requests_count"], "max": cur_limit["ai_responses_max"]},
            "reels_active": cur_limit["reels_ai"],
            "smart_model": cur_limit["smart_model"]
        },
        "payments": payments
    }

PLAN_LIMITS = {
    "free": {
        "knowledge_max": 3,
        "catalog_max": 10,
        "ai_responses_max": 100,
        "tokens_max": 25000,
        "broadcast_max": 0,
        "instagram_max": 1,
        "telegram_max": 1,
        "channels_max": 1,
        "reels_ai": False,
        "smart_model": False
    },
    "pro": {
        "knowledge_max": 25,
        "catalog_max": 50,
        "ai_responses_max": 1000,
        "tokens_max": 500000,
        "broadcast_max": 200,
        "instagram_max": 1,
        "telegram_max": 1,
        "channels_max": 3,
        "reels_ai": True,
        "smart_model": False
    },
    "business": {
        "knowledge_max": 9999,
        "catalog_max": 300,
        "ai_responses_max": 3000,
        "tokens_max": 2000000,
        "broadcast_max": 1000,
        "instagram_max": 3,
        "telegram_max": 3,
        "channels_max": 99,
        "reels_ai": True,
        "smart_model": True
    }
}

def record_token_usage(
    workspace_id: str,
    session_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int
) -> int:
    """Authoritative server-side recording of tokens used by AI responses into an audit ledger."""
    p_tok = max(0, int(prompt_tokens or 0))
    c_tok = max(0, int(completion_tokens or 0))
    t_tok = p_tok + c_tok
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO token_usage (workspace_id, session_id, model, prompt_tokens, completion_tokens, total_tokens)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (workspace_id, session_id, model, p_tok, c_tok, t_tok))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def get_token_usage_stats(workspace_id: Optional[str] = None) -> Dict[str, Any]:
    """Returns current month token usage statistics for workspace."""
    if not workspace_id:
        workspace_id = get_active_workspace_id()
    conn = get_connection()
    cursor = conn.cursor()
    row = cursor.execute("""
        SELECT 
            COALESCE(SUM(prompt_tokens), 0),
            COALESCE(SUM(completion_tokens), 0),
            COALESCE(SUM(total_tokens), 0),
            COUNT(*)
        FROM token_usage
        WHERE workspace_id = ?
          AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now');
    """, (workspace_id,)).fetchone()
    conn.close()
    return {
        "workspace_id": workspace_id,
        "prompt_tokens": row[0] if row else 0,
        "completion_tokens": row[1] if row else 0,
        "total_tokens": row[2] if row else 0,
        "requests_count": row[3] if row else 0
    }

def check_quota(workspace_id: str, action_type: str) -> Tuple[bool, str]:
    """
    Enforces business logic quotas across plans.
    Guards against free overuse of tokens, knowledge base, channels, and AI responses.
    """
    ws = get_workspace(workspace_id)
    plan_id = (ws.get("plan_id") if ws else "free") or "free"
    limits = PLAN_LIMITS.get(plan_id, PLAN_LIMITS["free"])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if action_type == "ai_chat":
        token_stats = get_token_usage_stats(workspace_id)
        msg_count = cursor.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE sender = 'agent' 
              AND strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now');
        """).fetchone()[0]
        conn.close()
        
        if msg_count >= limits["ai_responses_max"]:
            return False, f"Tarif bo'yicha oylik AI javoblar limiti tugadi ({plan_id.capitalize()} tarifi: {limits['ai_responses_max']} ta). Iltimos, tarifingizni yangilang."
        if token_stats["total_tokens"] >= limits["tokens_max"]:
            return False, f"Tarif bo'yicha oylik tokenlar limiti tugadi ({limits['tokens_max']:,} token). Iltimos, tarifingizni oshiring."
        return True, "OK"
        
    elif action_type == "add_knowledge":
        k_count = cursor.execute("SELECT COUNT(*) FROM knowledge_items WHERE workspace_id = ?;", (workspace_id,)).fetchone()[0]
        conn.close()
        if k_count >= limits["knowledge_max"]:
            return False, f"Tarif bo'yicha bilimlar bazasi limiti tugadi ({plan_id.capitalize()} tarifi: {limits['knowledge_max']} ta). Yangi bilim qo'shish uchun tarifni oshiring."
        return True, "OK"
        
    elif action_type == "connect_channel":
        c_count = cursor.execute("SELECT COUNT(*) FROM channels WHERE is_connected = 1 AND channel_id != 'web_widget';").fetchone()[0]
        conn.close()
        if c_count >= limits["channels_max"]:
            return False, f"Tarif bo'yicha ulangan kanallar limiti tugadi ({plan_id.capitalize()} tarifi: {limits['channels_max']} ta). Boshqa kanal ulash uchun tarifni oshiring."
        return True, "OK"
        
    conn.close()
    return True, "OK"

def record_payment(workspace_id: str, plan_id: str, period_months: int, amount: int, payment_method: str) -> Dict[str, Any]:
    plan_id = (plan_id or "").lower().strip()
    if plan_id not in ["free", "pro", "business"]:
        raise ValueError(f"Noto'g'ri tarif tanlandi: {plan_id}")
    if period_months not in [1, 3, 6, 12]:
        raise ValueError(f"Noto'g'ri to'lov davri: {period_months}")
        
    prices = {"free": 0, "pro": 249000, "business": 590000}
    discounts = {1: 0.0, 3: 0.10, 6: 0.15, 12: 0.25}
    expected_base = prices[plan_id]
    expected_disc = discounts[period_months]
    expected_total = int(expected_base * period_months * (1.0 - expected_disc))
    
    # Security: If paid plan, strictly verify payment method and amount
    if plan_id != "free":
        if not payment_method or payment_method.lower() in ["free", "none", ""]:
            raise ValueError("Pullik tarifni bepul to'lov usuli bilan faollashtirish taqiqlanadi.")
        if amount < expected_total:
            raise ValueError(f"To'lov summasi yetarli emas. Kutilgan summa: {expected_total} so'm, yuborilgan summa: {amount} so'm.")
    else:
        amount = 0
        payment_method = "free"
        
    expires = (datetime.now() + timedelta(days=period_months * 30)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO payments (workspace_id, plan_id, period_months, amount, payment_method, status)
        VALUES (?, ?, ?, ?, ?, 'paid');
    """, (workspace_id, plan_id, period_months, amount, payment_method))
    
    cursor.execute("""
        UPDATE businesses
        SET plan_id = ?, billing_period = ?, plan_expires_at = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
    """, (plan_id, period_months, expires, workspace_id))
    conn.commit()
    conn.close()
    return get_billing_info(workspace_id)

import uuid
import hashlib

def hash_password(password: str) -> str:
    if not password:
        return ""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_user(auth_method: str, identifier: str, full_name: str = "", password: str = "", selected_plan: str = "free") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    clean_id = identifier.strip().lower()
    
    cursor.execute("SELECT * FROM users WHERE auth_method = ? AND identifier = ?", (auth_method, clean_id))
    row = cursor.fetchone()
    if row:
        user = dict(row)
        cursor.execute("UPDATE users SET selected_plan = ? WHERE id = ?", (selected_plan, user["id"]))
        conn.commit()
        conn.close()
        user["selected_plan"] = selected_plan
        return {"status": "exists", "user": user}
    
    user_id = "usr_" + uuid.uuid4().hex[:12]
    pwd_hash = hash_password(password) if password else ""
    display_name = full_name.strip() or clean_id.replace("@", "").split(".")[0].capitalize()
    
    cursor.execute("""
        INSERT INTO users (id, auth_method, identifier, full_name, password_hash, selected_plan, active_workspace_id)
        VALUES (?, ?, ?, ?, ?, ?, 'default');
    """, (user_id, auth_method, clean_id, display_name, pwd_hash, selected_plan))
    
    # Reset active workspace setting to default
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('active_workspace_id', 'default');")

    # Personalize default workspace name to the newly registered user
    biz_name = f"{display_name} Korxonasi" if display_name else "Mening Korxonam"
    cursor.execute("UPDATE businesses SET name = ?, description = 'AI sotuv agenti bilan jihozlangan korxona' WHERE id = 'default';", (biz_name,))
    
    # Remove any extra mock workspaces from previous tests
    cursor.execute("DELETE FROM businesses WHERE id != 'default';")

    # SECURITY HARDENING:
    # A user cannot gain paid 'pro' or 'business' tier for free on the workspace simply by registering!
    # The selected_plan is recorded as user preference, but the active workspace remains 'free'
    # until paid checkout is completed.
    if selected_plan == "free":
        cursor.execute("UPDATE businesses SET plan_id = 'free' WHERE id = 'default'")
    
    # Clean workspace initialization: Wipe old mock conversations and leads so new user gets clean 0-state
    cursor.execute("DELETE FROM messages;")
    cursor.execute("DELETE FROM follow_ups;")
    cursor.execute("DELETE FROM leads;")
    cursor.execute("DELETE FROM conversations;")

    # Channel connection rules:
    # If registered with email/gmail/google, all external channels MUST be disconnected (0)
    # until the user explicitly connects one in the channel gate overlay
    is_email_or_google = auth_method in ('email', 'google') or ('@' in clean_id and not clean_id.startswith('@'))
    if is_email_or_google:
        cursor.execute("UPDATE channels SET is_connected = 0 WHERE channel_id IN ('instagram', 'telegram', 'whatsapp');")
    else:
        if auth_method in ('instagram', 'telegram', 'whatsapp'):
            cursor.execute("UPDATE channels SET is_connected = 1 WHERE channel_id = ?;", (auth_method,))
            cursor.execute("UPDATE channels SET is_connected = 0 WHERE channel_id != ? AND channel_id != 'web_widget';", (auth_method,))

    conn.commit()
    conn.close()
    return {
        "status": "created",
        "user": {
            "id": user_id,
            "auth_method": auth_method,
            "identifier": clean_id,
            "full_name": display_name,
            "selected_plan": selected_plan,
            "active_workspace_id": "default"
        }
    }

def authenticate_user(auth_method: str, identifier: str, password: str = "") -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    clean_id = identifier.strip().lower()
    
    cursor.execute("SELECT * FROM users WHERE auth_method = ? AND identifier = ?", (auth_method, clean_id))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    
    user = dict(row)
    if password and user.get("password_hash"):
        if hash_password(password) != user["password_hash"]:
            return None
    user.pop("password_hash", None)
    return user

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, auth_method, identifier, full_name, selected_plan, active_workspace_id, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_session(user_id: str, days: int = 30) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    token = "sess_" + uuid.uuid4().hex
    expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO sessions (token, user_id, expires_at)
        VALUES (?, ?, ?);
    """, (token, user_id, expires))
    conn.commit()
    conn.close()
    return token

def get_user_by_session(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.auth_method, u.identifier, u.full_name, u.selected_plan, u.active_workspace_id, u.created_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND (s.expires_at IS NULL OR s.expires_at > CURRENT_TIMESTAMP);
    """, (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_session(token: str):
    if not token:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?;", (token,))
    conn.commit()
    conn.close()

def has_connected_primary_channel() -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM channels 
        WHERE channel_id IN ('instagram', 'telegram', 'whatsapp') AND is_connected = 1;
    """)
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# ----------------- FOLLOW-UP / RE-ENGAGEMENT FUNCTIONS -----------------

def schedule_follow_up(session_id: str, channel: str = "telegram", name: str = "Mijoz", delay_minutes: int = 120, step: int = 1) -> Optional[int]:
    """Schedules a smart, non-intrusive re-engagement follow-up for an idle lead."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # 1. Ensure conversation row exists to satisfy foreign key constraint
        conv = cursor.execute("SELECT session_id FROM conversations WHERE session_id = ?;", (session_id,)).fetchone()
        if not conv:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT OR IGNORE INTO conversations (session_id, name, channel, script_preference, autopilot_enabled, updated_at)
                VALUES (?, ?, ?, 'spin', 1, ?);
            """, (session_id, name, channel, now))
            conn.commit()

        # 2. Check if there is already a pending follow up for this session
        existing = cursor.execute("SELECT id FROM follow_ups WHERE session_id = ? AND status = 'pending';", (session_id,)).fetchone()
        if existing:
            return existing["id"]

        scheduled_at = (datetime.now() + timedelta(minutes=delay_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO follow_ups (session_id, channel, name, follow_up_step, status, scheduled_at)
            VALUES (?, ?, ?, ?, 'pending', ?);
        """, (session_id, channel, name, step, scheduled_at))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_due_follow_ups() -> List[Dict[str, Any]]:
    """Fetches follow-ups that are pending and due to be sent."""
    conn = get_connection()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute("""
            SELECT f.*, c.autopilot_enabled, c.status as conv_status
            FROM follow_ups f
            JOIN conversations c ON f.session_id = c.session_id
            WHERE f.status = 'pending' AND f.scheduled_at <= ? AND c.autopilot_enabled = 1
            ORDER BY f.scheduled_at ASC LIMIT 20;
        """, (now_str,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def mark_follow_up_sent(follow_up_id: int, text: str):
    """Marks follow-up as sent and records sent text."""
    conn = get_connection()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            UPDATE follow_ups 
            SET status = 'sent', sent_at = ?, follow_up_text = ?
            WHERE id = ?;
        """, (now_str, text, follow_up_id))
        conn.commit()
    finally:
        conn.close()

def cancel_pending_follow_ups(session_id: str):
    """Cancels pending follow-ups when user responds or interacts."""
    conn = get_connection()
    try:
        conn.execute("UPDATE follow_ups SET status = 'replied' WHERE session_id = ? AND status = 'pending';", (session_id,))
        conn.commit()
    finally:
        conn.close()

def list_follow_up_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns recent follow up events and history."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM follow_ups ORDER BY id DESC LIMIT ?;", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def record_analytics_event(event_type: str, page: str = "/", metadata: Optional[Dict[str, Any]] = None, client_ip_hash: str = "") -> int:
    """Records privacy-compliant telemetry event (pageview, CTA click)."""
    conn = get_connection()
    try:
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        cursor = conn.execute(
            "INSERT INTO analytics_events (event_type, page, metadata, client_ip_hash) VALUES (?, ?, ?, ?);",
            (event_type, page, meta_json, client_ip_hash)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_analytics_summary() -> Dict[str, Any]:
    """Returns analytics aggregate summary for dashboard."""
    conn = get_connection()
    try:
        total_views = conn.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'pageview';").fetchone()[0]
        total_clicks = conn.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'cta_click';").fetchone()[0]
        top_ctas = conn.execute("""
            SELECT metadata, COUNT(*) as cnt 
            FROM analytics_events 
            WHERE event_type = 'cta_click' 
            GROUP BY metadata 
            ORDER BY cnt DESC LIMIT 5;
        """).fetchall()
        return {
            "pageviews": total_views,
            "cta_clicks": total_clicks,
            "top_ctas": [{"name": r[0], "count": r[1]} for r in top_ctas]
        }
    finally:
        conn.close()

# Initialize database on module import
init_db()
