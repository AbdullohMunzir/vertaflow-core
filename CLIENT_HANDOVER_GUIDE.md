# 📘 VertaFlow AI — Buyurtmachiga Topshirish va Foydalanish Qo'llanmasi (Client Handover Guide)

Hush kelibsiz! Ushbu qo'llanma **VertaFlow AI Closer Platformasi**ni real biznes korxonasiga (Mebel fabrikasi, O'quv markazi, Klinika, Savdo do'koni va h.k.) topshirish, uni ishga tushirish va undan maksimal savdo natijalariga erishish bo'yicha to'liq qo'llanmadir.

---

## 🌟 1. VertaFlow AI Nima va U Biznesga Qanday Foyda Keltiradi?

Ko'p bizneslarda xaridorlar Instagram, Telegram yoki saytga yozishadi, lekin:
- Sotuvchi menejerlar tushlikda, kechasi yoki mijoz ko'pligidan kechikib (30–60 daqiqada) javob berishadi.
- Bu vaqt ichida mijoz sovib, boshqa korxonaga ketib qoladi.

**VertaFlow AI** — shunchaki oddiy savol-javob qiluvchi bot emas, balki **professional savdo yopuvchi agent (AI Closer)** dir:
1. **3 soniyada javob beradi (24/7 kutishsiz)**;
2. **Qat'iy 2–3 qatorlik qoida**: Mijozni uzun ma'ruzalar bilan zeriktirmaydi;
3. **SPIN Selling metodologiyasi**: Mijozning biznes og'rig'i, ehtiyoji va buyurtma hajmini aniqlaydi;
4. **Challenger Reframe**: Agar mijoz *"qimmat ekan"* yoki *"boshqa joyda arzon bot bor"* desa, uning e'tiborini narxdan yo'qotilayotgan foydaga buradi;
5. **Kirill va Lotin avto-ko'zgusi**: Mijoz kirillda yozsa — kirillda, lotinda yozsa — lotinda javob beradi;
6. **Menejerga 3 Qatorlik Tayyor Dosye**: Mijoz telefon raqamini berishi yoki 70+ ball to'plashi bilanoq, sotuv bo'limi boshlig'ining Telegramiga zudlik bilan qisqa mijoz dosyesi yuboriladi.

---

## ⚡ 2. 1-Bosqich: Serverda Ishga Tushirish

Serveringizda (Ubuntu / Debian VPS) loyihani 1 ta buyruq bilan ishga tushirish mumkin:

```bash
# Repozitoriyni ochish
cd verta-platform

# Avtomatlashtirilgan o'rnatish
./deploy.sh
```

Server ishga tushgach, brauzeringizda quyidagi manzilni oching:
👉 **http://SERVER_IP:8000** (yoki mahaliy kompyuterda `http://127.0.0.1:8000`)

---

## 🏢 3. 2-Bosqich: Biznesni 2 Daqiqada Sozlash (Onboarding)

Platformani yangi biznesga moslashtirish uchun:
1. Ekranning yuqori o'ng burchagidagi **"⚡ Sozlash"** tugmasini bosing;
2. Korxona nomi (masalan: *"Grand Mebel"* yoki *"Everest O'quv Markazi"*), faoliyat sohasi va o'rtacha chekni kiriting;
3. Mijozlar eng ko'p beradigan 3–4 ta savol-javobni (FAQ) yozing (masalan: narxlar, yetkazib berish, kafolat);
4. **"Saqlash"** tugmasini bosing.
   *(AI bir zumda yangi ma'lumotlarni o'rganib oladi va barcha mijozlarga aynan sizning biznesingiz nomidan javob berishni boshlaydi).*

---

## ✈️ 4. 3-Bosqich: Telegram Botni Ulash

1. Telegramda `@BotFather` ga kiring va yangi bot yarating (`/newbot`);
2. BotFather bergan **HTTP API Token**ni nusxalang;
3. VertaFlow boshqaruv panelida chap menyudagi **"✈️ Telegram Bot"** ustiga bosing;
4. Bot Tokenni va issiq lidlar yuborilishi kerak bo'lgan **Menejer Chat ID**sini kiriting;
5. **"Botni Ishga Tushirish ▶"** tugmasini bosing;
6. Endi Telegram botingizga yozgan har bir mijoz bilan VertaFlow suhbatlashadi va u qoldirgan raqamlar darhol panelda va menejer telefonida aks etadi!

---

## 🌐 5. 4-Bosqich: Har Qanday Veb-Saytga Vidjetni Joylashtirish

Agar korxonaning o'z veb-sayti bo'lsa, ushbu kodni saytning `</body>` tegi oldiga qo'yish kifoya:

```html
<script src="http://SIZNING_DOMEN:8000/static/widget.js"></script>
```

Saytning pastki o'ng burchagida zamonaviy yashil rangli **VertaFlow AI Closer** tugmasi paydo bo'ladi.

---

## 👨‍💼 6. 5-Bosqich: Inson-Operator Nazorati (Human Takeover)

Agar sotuvchi xodim suhbatga o'zi aralashmoqchi bo'lsa:
1. Panelda chapdagi Inbox ro'yxatidan kerakli mijozni tanlaydi;
2. O'ng paneldagi **"👨‍💼 Operator Chatga Kirishi"** tugmasini bosadi;
3. AI avtopilot to'xtaydi va operator pastdagi maydondan o'zi xabar yozishi mumkin;
4. Xabar bir zumda mijozning Telegramiga yoki sayt vidjetiga yetkaziladi;
5. Istalgan paytda **"AI Avtopilotni Qaytarish 🤖"** tugmasi orqali suhbatni yana sun'iy intellektga topshirish mumkin.

---

## 📊 7. 6-Bosqich: Lidlar CRM va Excel Eksport

- Barcha saralangan xaridorlar **"👥 Mijozlar (Lead CRM)"** bo'limida saqlanadi;
- Mijoz to'plagan balliga qarab `HOT 🔥` (100–70 ball), `WARM ⚡` (40–69 ball) va `COLD ❄️` (0–39 ball) bo'lib turadi;
- Ekranning yuqorisidagi **"📥 Excel / CSV Yuklab Olish"** tugmasini bosish orqali barcha lidlar telefon raqamlari, og'riqlari va xarid muddatlari bilan birga to'g'ridan-to'g'ri Excel formatida yuklab olinadi.

---

## 📈 8. 7-Bosqich: O'z-o'zini Rivojlantiruvchi Tungi Audit (Evaluator)

- Har kecha VertaFlow barcha suhbatlarni tahlil qiladi;
- Qaysi savolda mijoz javobsiz qolganini yoki nima sababdan sotuv yopilmaganini aniqlaydi;
- Boshqaruv panelining **"📈 Tungi Audit"** bo'limida biznes egasiga **3 ta tayyor AI tavsiya** beriladi;
- Biznes egasi **"Qabul qilish" (Apply)** tugmasini bossa, yangi bilim darhol agent xotirasiga qo'shiladi.

---

## 🔒 9. Texnik Xavfsizlik va Ma'lumotlar Doimiyligi

- **Ma'lumotlar bazasi**: Barcha yozishmalar va lidlar `vertaflow.db` (SQLite) faylida saqlanadi. Hech qanday ma'lumot yo'qolmaydi;
- **AI Miya**: Tizim Google kompaniyasining eng so'nggi va tejamkor **Gemini 2.5 Flash** modeli asosida ishlaydi;
- **Oflayn Zaxira**: Agar internetda uzilish yuz bersa ham, tizim to'xtab qolmasdan, o'zining avtonom sotuv andozasida xizmat ko'rsatishda davom etadi.
