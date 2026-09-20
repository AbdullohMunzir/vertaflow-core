# 🚀 VertaFlow AI — Autonomous AI Sales Closer Platform

**VertaFlow AI** — O'zbekiston bozori va messenjerlar (Telegram, Instagram DM, Web Widget) uchun maxsus ishlab chiqilgan, shunchaki savol-javob qiluvchi oddiy FAQ bot emas, balki mijoz e'tirozlarini professional darajada yopuvchi va bitim tuzuvchi **avtonom sotuvchi agent (AI Closer)** platformasi.

---

## 🌟 Asosiy Imkoniyatlar (Core Features)

- 🧠 **SPIN Selling & Challenger Sale Metodologiyasi**:
  - `Situation` ➔ `Problem` ➔ `Implication` ➔ `Solution Pitch` ➔ `Objection Handling` ➔ `Closing` ➔ `Handoff Human`
  - Mijozga keraksiz uzun ma'lumot tiqishtirmaydi, aksincha uning biznes og'rig'ini aniqlab, qiymatni hisoblab beradi.
- ⚡ **Messenjer Qisqaligi Nazorati (Brevity Guard)**:
  - Hech qachon 2-3 qatordan ortiq korporativ paragraflar yozmaydi.
  - Har bir xabar doimo **1 ta aniq yopuvchi savol** bilan yakunlanadi.
- 🇺🇿 **O'zbek Tili Ko'zgu Detektori (Dual-Script Engine)**:
  - Mijoz **Kirill** alifbosida yozsa — agent avtomatik Kirillda javob qaytaradi.
  - Mijoz **Lotin** alifbosida yozsa — agent Lotinda javob qaytaradi.
  - Sun'iy ruscha/inglizcha kalka so'zlarni avtomatik tozalaydi.
- 📊 **Dinamik Lead Scoring (0–100 Ball)**:
  - Deterministik atributlar tahlili (Telefon raqami: +30, Og'riq: +25, Hajm: +20, Xarid muddati: +15).
  - Lid holati: `HOT 🔥` (70–100), `WARM ⚡` (40–69), `COLD ❄️` (0–39).
- 📋 **Avtomatlashtirilgan 3 Qatorlik Lead Dossier**:
  - Sotuv bo'limi operatori 50 ta xabarni o'qib o'tirmaydi — agent zudlik bilan 3-4 qatorda tayyor mijoz dosyesini shakllantiradi.
- ⚔️ **Raqobat Battlecards va Challenger Reframe**:
  - Raqobatchilar eslanganda ularni kamsitmasdan, ularning zaif tomonlarini ko'rsatib, "Landmine" (tuzoq) savollari bilan muloqotni bizning foydamizga buradi.
- 📈 **O'z-o'zini Rivojlantiruvchi Tungi Audit (Self-Improving Evaluator)**:
  - Kunlik muloqotlarni tahlil qilib, tushib qolgan mijozlar sababini aniqlaydi va biznes egasiga 3 ta tayyor AI tavsiya taqdim etadi.
- ✈️ **Telegram Bot & Omnichannel Dispatcher**:
  - Telegram orqali muloqot va mijoz issiq holatga kelishi bilan sotuv menejerining shaxsiy Telegramiga darhol xabarnoma yuborish.
- 🌐 **1 Qatorda O'rnatiluvchi Web Vidjet (`widget.js`)**:
  - Har qanday veb-saytga bitta `<script>` orqali ulanuvchi zamonaviy suzuvchi chat.

---

## 🎨 Dizayn Tizimi (Design System)

Platforma boshqaruv paneli **Chatla** andozasida quyidagi ranglar gammasida yaratilgan:
- **Asosiy fon**: Tinch kashmir/off-white (`#F7F9F6`)
- **Kartalar va bloklar**: Toza oq (`#FFFFFF`), nozik chegara (`#E5E7EB`)
- **Asosiy aksent**: Pastel Pistachio Lime (`#B5F87B`)
- **Lead Hot nishoni**: Warm Amber (`#FEF08A` / `#78350F`)

---

## 📂 Loyiha Tuzilishi

```
vertaflow/
├── core/
│   ├── verta_engine.py       # Markaziy boshqaruvchi (Orkestrator)
│   ├── verta_stages.py       # 8 bosqichli SPIN & Challenger holatlar mashinasi
│   ├── verta_state.py        # Lead scoring (0-100), atributlar va Lead Dossier
│   ├── verta_uzbek_engine.py # Kirill/Lotin ko'zgu detektori va 2-3 qator filtri
│   ├── verta_battlecards.py  # Raqobat battlecards va landmine savollari
│   └── verta_evaluator.py   # Tungi audit va avto-tavsiyalar dvigateli
├── static/
│   ├── index.html            # Chatla uslubidagi zamonaviy boshqaruv paneli
│   └── widget.js             # Veb-saytlar uchun embeddable chat vidjeti
├── api.py                    # FastAPI server (Chat, CRM, Battlecards, Telegram)
├── telegram_bot.py           # Telegram bot va xabarnomalar moduli
├── test_verta.py             # CLI sinov skripti
├── requirements.txt          # Kerakli Python kutubxonalari
└── README.md
```

---

## ⚡ Tezkor Ishga Tushirish (Quickstart)

### 1. Repozitoriyni klonlash va virtual muhit yaratish
```bash
git clone git@github.com:AbdullohMunzir/vertaflow.git
cd vertaflow
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. FastAPI Serverni ishga tushirish
```bash
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```
Brauzeringizda oching:
👉 **http://localhost:8000**

### 3. Telegram Botni ulash (Ixtiyoriy)
```bash
export TELEGRAM_BOT_TOKEN="your_botfather_token"
export SALES_MANAGER_CHAT_ID="your_telegram_chat_id"
python3 telegram_bot.py
```

### 4. Saytingizga Vidjetni Joylash
Saytingizning `</body>` tegi oldiga joylang:
```html
<script src="http://localhost:8000/static/widget.js"></script>
```

---

## 🧪 CLI Orqali Sinab Ko'rish

```bash
python3 test_verta.py
```

---

## 📄 Litsenziya
MIT License. Erkin foydalanish va rivojlantirish uchun ochiq.
