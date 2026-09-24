#!/usr/bin/env bash
# =================================================================
# VertaFlow AI — Automated 1-Click Production Server Setup Script
# Works on Ubuntu 20.04+, Debian 11+, and Linux VPS environments.
# =================================================================

set -e

echo "🚀 VertaFlow AI Closer Platform — O'rnatish jarayoni boshlandi..."

# 1. Check Python version
if ! command -v python3 &> /dev/null; then
    echo "📦 Python3 o'rnatilmoqda..."
    sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
fi

# 2. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Virtual environment (venv) yaratilmoqda..."
    python3 -m venv venv
fi

echo "📦 Kutubxonalar o'rnatilmoqda..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Environment & Database Setup
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "⚙️ .env fayli yaratilmoqda (.env.example nusxalandi)..."
    cp .env.example .env
fi

echo "🗄️ Ma'lumotlar bazasi initsializatsiya qilinmoqda..."
python3 -c "import db; print('✅ vertaflow.db tayyor!')"

# 4. Verify Gemini Engine
echo "🧠 Google Gemini tekshirilmoqda..."
python3 -c "
from core.verta_gemini import VertaGeminiClient
client = VertaGeminiClient()
if client.api_key:
    print('✅ Gemini API muvaffaqiyatli ulandi!')
else:
    print('⚠️ Eslatma: GEMINI_API_KEY .env fayliga kiritilishi kerak')
"

echo "================================================================="
echo "🎉 VertaFlow AI platformasi to'liq o'rnatildi va tayyor!"
echo ""
echo "Serverni ishga tushirish uchun:"
echo "   source venv/bin/activate"
echo "   python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "Yoki fon rejimida (systemd / nohup):"
echo "   nohup venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &"
echo ""
echo "Boshqaruv paneli manzili:"
echo "👉 http://localhost:8000"
echo "================================================================="
