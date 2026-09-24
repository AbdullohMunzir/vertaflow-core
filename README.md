# VertaFlow AI | Autonomous AI Sales Closer Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%20WAL-003B57.svg)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-SPIN%20%2B%20Challenger-FF6F00.svg)]()

**VertaFlow AI** is a production-grade autonomous conversational commerce engine and AI closer platform. Unlike generic FAQ chatbots that merely answer questions, VertaFlow actively guides prospects through a proven sales methodology, resolves stubborn objections in real time, scores purchase intent, and drives conversations to closed deals.

Built specifically for high-velocity messenger commerce across **Telegram**, **Instagram Direct**, **WhatsApp Business**, and **Web Chat Widgets**.

---

## Key Capabilities

### 1. 8-Stage Conversational State Machine
VertaFlow runs on a structured, multi-stage sales progression model adapting principles from **SPIN Selling**, **The Challenger Sale**, **Sandler Selling System**, and **LAER Framework**:
- `01 // INTRO`: Sandler upfront contract establishing permission to ask questions.
- `02 // SITUATION`: Discovery of current workflow and volume parameters.
- `03 // PROBLEM`: Identification of core business pain points and bottlenecks.
- `04 // IMPLICATION`: Challenger calculation of recurring daily financial losses.
- `05 // SOLUTION PITCH`: Social proof, quantifiable outcomes, and tailored value proposition.
- `06 // OBJECTION DEFUSER`: LAER active listening and reframing (Price, Trust, Timing, Competition).
- `07 // CLOSING`: Micro-commitments, trial offers, and payment links (Click, Payme).
- `08 // HANDOFF`: Automated 3-line sales dossier dispatched to sales representatives.

### 2. Brevity Guard & Engagement Rules
- Eliminates lengthy corporate blocks of text: responses are constrained to 2-3 readable lines.
- Every outgoing message ends with **exactly one closing question** to sustain conversational momentum.

### 3. Dual-Script Language Engine (Latin & Cyrillic)
- Automatically detects the prospect's script (Latin or Cyrillic Uzbek) and mirrors back identically.
- Filters out unnatural machine-translation artifacts, preserving authentic commercial terminology.

### 4. Deterministic Intent Scoring (0-100)
- Real-time lead scoring based on explicit signals:
  - Phone number captured: `+30 points`
  - Pain point quantified: `+25 points`
  - Order volume specified: `+20 points`
  - Urgency / timeframe confirmed: `+15 points`
- Categorization: `HOT 🔥` (70-100), `WARM ⚡` (40-69), `COLD ❄️` (0-39).

### 5. Automated Sales Dossier
- Generates an executive 3-line summary for human sales reps when a lead becomes hot:
  - Prospect Name & Channel origin
  - Specific product interest & calculated budget
  - Recommended closing tactic and telephone contact

### 6. Competitive Battlecards & Challenger Reframing
- Counter-strategies against competitor mentions using non-disparaging "landmine" questions.
- Reframes price objections into daily cost-of-inaction calculations.

### 7. Self-Improving Nightly Evaluator
- Analyzes daily conversation logs to detect drop-off reasons.
- Delivers actionable prompt tuning and knowledge base expansion suggestions directly to the admin dashboard.

### 8. Hybrid Retrieval-Augmented Generation (RAG)
- Hybrid BM25 keyword matching and vector semantic retrieval.
- Grounded strictly in validated knowledge base documents (PDF, DOCX, TXT, FAQ) to eliminate hallucinations.

---

## Architecture Overview

```
                      [ Incoming Prospect Message ]
                                    |
      +-----------------------------+-----------------------------+
      |                             |                             |
[ Telegram Bot ]           [ Instagram / WhatsApp ]       [ Web Chat Widget ]
      |                             |                             |
      +-----------------------------+-----------------------------+
                                    |
                                    v
                     [ FastAPI Central Hub (api.py) ]
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
            v                       v                       v
    [ Brevity Guard ]     [ Dual-Script Mirror ]   [ Rate Limiter & Auth ]
            |                       |                       |
            +-----------------------+-----------------------+
                                    |
                                    v
                      [ VertaFlow Sales Engine ]
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
            v                       v                       v
     [ State Machine ]      [ RAG Knowledge ]     [ Battlecard Matrix ]
   (SPIN / Challenger)     (BM25 + Semantic)       (Objection Handling)
            |                       |                       |
            +-----------------------+-----------------------+
                                    |
                                    v
                     [ Intent Scorer (0-100) ]
                                    |
                  +-----------------+-----------------+
                  |                                   |
                  v                                   v
          Score >= 70 (HOT)                   Score < 70 (NURTURE)
                  |                                   |
                  v                                   v
      [ Instant Telegram Alert ]              [ Guided Follow-up ]
```

---

## Tech Stack

| Component | Technology | Rationale |
|:---|:---|:---|
| **Backend Framework** | FastAPI 0.115+ / Python 3.10+ | High-throughput asynchronous routing and native validation |
| **Database** | SQLite with WAL mode (`db.py`) | Zero-latency embedded database, transactional integrity, automated online backups |
| **LLM Inference** | Google Gemini 2.5 Flash / Hybrid Fallback | Sub-second generation speed, high reasoning benchmark scores, low token footprint |
| **Frontend Dashboard** | Vanilla JS / Tailwind CSS / Plus Jakarta Sans | Single-bundle responsiveness, zero heavy SPA build steps, ultra-fast mobile loading |
| **Compression** | Starlette GZipMiddleware | Reduces network payload by ~78% (72 KB down to 16 KB) |
| **Testing** | Pytest / Playwright E2E | Multi-stage regression suites, automated browser verification, security auditing |

---

## Project Structure

```
vertaflow-core/
├── core/
│   ├── verta_engine.py       # Central sales orchestrator
│   ├── verta_stages.py       # 8-stage SPIN & Challenger state machine
│   ├── verta_state.py        # Lead scoring (0-100) & lead dossier generator
│   ├── verta_uzbek_engine.py # Dual-script mirror & brevity guard filter
│   ├── verta_rag.py          # Hybrid RAG retrieval engine
│   ├── verta_battlecards.py  # Objection defuser and competitive battlecards
│   ├── verta_evaluator.py   # Autonomous nightly conversation evaluator
│   └── verta_gemini.py       # Native Google Gemini 2.5 Flash integration
├── static/
│   ├── index.html            # Obsidian Dark Luxury SaaS admin platform
│   ├── landing.html          # High-converting responsive landing page
│   ├── onboarding.html       # 3-step merchant setup wizard
│   ├── terms.html            # Public terms of service (Ommaviy Oferta)
│   ├── privacy.html          # Public privacy policy
│   ├── widget.js             # 1-line embeddable floating chat widget
│   ├── robots.txt            # Search engine crawler policies
│   └── sitemap.xml           # Structured sitemap
├── tests/                    # Playwright E2E and API test suites
├── api.py                    # Production FastAPI server & REST API
├── backup_db.py              # Atomic SQLite backup rotation service
├── db.py                     # Central SQLite schema, queries, and migrations
├── telegram_bot.py           # Telegram bot integration & manager notification
├── deploy.sh                 # 1-click Linux VPS automated deployment script
├── docker-compose.yml        # Docker orchestration configuration
├── Dockerfile                # Production container build recipe
├── requirements.txt          # Python dependencies
└── .env.example              # Environment configuration template
```

---

## Quickstart Guide

### 1. Clone Repository & Setup Environment
```bash
git clone https://github.com/AbdullohMunzir/vertaflow-core.git
cd vertaflow-core
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and supply your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
# Google Gemini API Key (Required for primary closer brain)
GEMINI_API_KEY=your_gemini_api_key_here

# Telegram Bot Integration (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
SALES_MANAGER_CHAT_ID=your_chat_id_here

# Server Settings
PORT=8000
```

### 3. Launch Development Server
```bash
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to:
- Landing Page: **http://localhost:8000/**
- Admin Dashboard: **http://localhost:8000/app**
- Health Check: **http://localhost:8000/health**

---

## Docker Deployment

To launch the complete platform inside an isolated container:

```bash
# Set your Gemini API key in environment
export GEMINI_API_KEY="your_gemini_api_key_here"

# Build and start container
docker-compose up -d --build
```

---

## Omnichannel Integrations

### Telegram Bot Setup
1. Create a bot using [@BotFather](https://t.me/BotFather) and obtain your token.
2. In the VertaFlow Dashboard under **Channels -> Telegram**, enter the token and the manager chat ID.
3. Start the bot worker:
   ```bash
   python3 telegram_bot.py
   ```

### Web Chat Widget Integration
Embed the responsive floating chat widget into any website before `</body>`:
```html
<script src="https://vertaflow.uz/static/widget.js"></script>
```

---

## Automated Backups & Reliability

The database service utilizes SQLite's online backup API via `backup_db.py`:
- Backs up active transactions without database locks or server restarts.
- Executes automatically at startup and once every 24 hours.
- Maintains rolling retention of the 14 most recent snapshot archives.

---

## License

This project is licensed under the **MIT License**. Free for commercial and non-commercial development.
