#!/usr/bin/env python3
"""
VertaFlow — Sales Training Knowledge Seeder
==========================================
SPIN Selling (Rackham) va The Challenger Sale (Dixon & Adamson) kitoblarining
asosiy bilimlarini barcha mavjud workspacelarga yuklab, RAG orqali indekslaydi.

Muhim: Bu materiallar agent o'rganishi uchun — mijozlarga ko'rinmaydi.
Foydalanish: python3 seed_training_books.py [--workspace ALL | --workspace ws_id]
"""

import sys
import os
import json
import argparse
import sqlite3

# Path sozlash
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

# ─────────────────────────────────────────────────────────────
# KITOB 1: SPIN SELLING — Neil Rackham
# 35,000 dan ortiq sotuv suhbati tahlilidan yaratilgan
# ─────────────────────────────────────────────────────────────
SPIN_SELLING_BOOK = """
SPIN SELLING — Neil Rackham
(Dunyo bo'yicha 3 million nusxada sotilgan)
Published: 1988 | Huthwaite Research Group — 35,000 ta sotuv suhbatini tahlil qilgan

════════════════════════════════════════════════
ASOSIY G'OYA
════════════════════════════════════════════════
Kichik sotuvlar uchun an'anaviy texnikalar (ochiq savol, e'tirozga javob, yopish) yaxshi ishlaydi.
Lekin KATTA sotuvlarda bu texnikalar 50% kam natija beradi.
Rackham 35,000 ta real sotuv suhbatini tahlil qildi va yuqori darajali sotuvchilar
4 turdagi savollar ketma-ketligini qo'llashini aniqladi.

════════════════════════════════════════════════
SPIN = 4 SAVOL TURI
════════════════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
S — SITUATION (Vaziyat) Savollar
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Maqsad: Mijozning hozirgi holatini tushunish.
Xato: Ko'p situation savol berish mijozni charchatadi.
Qoida: Faqat keyingi savol uchun kerakli ma'lumotni yig'ing.

Samarali Situation savollari:
- "Hozirda kuniga taxminan qancha buyurtma qabul qilasiz?"
- "Savdo jarayoningizda qanday vositalardan foydalanasiz?"
- "Jamoangizda necha nafar menejer savdo bilan shug'ullanadi?"
- "Mijozlarga qanday kanal orqali javob berasiz — telefon, WhatsApp yoki boshqa?"
- "O'rtacha bitta savdoni yopish uchun qancha vaqt ketadi?"

Noto'g'ri qo'llash misoli (juda ko'p situation):
Agent: "Shtatda necha odam bor? Biznes qachon ochildi? Asosiy mahsulotingiz nima?
Yillik aylanmangiz qancha? CRM ishlatadizmi?"
→ BU NOTO'G'RI — mijoz so'roqqa tortilgandek his qiladi.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P — PROBLEM (Muammo) Savollar
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Maqsad: Mijozning noqulayliklarini, qiyinchiliklarini yuzaga chiqarish.
Muhim: Yuqori darajali sotuvchilar kichik sotuvchilarga nisbatan 2x ko'proq Problem savol beradi.

Samarali Problem savollar:
- "Menejerlar bir vaqtda ko'p so'rov kelganda ulgurolmay qoladimi?"
- "Tunda yoki bayram kunlari savdoni kim boshqaradi?"
- "Mijozlar javob kutib sovib ketgan holatlar bo'ladimi?"
- "CRM ma'lumotlarini to'ldirish qancha vaqt oladi?"
- "Yangi menejer o'rgatish qancha vaqt va pul sarflaydi?"
- "Ba'zan buyurtmalar tushib qolishi yoki unutilishi bo'ladimi?"
- "Mijozdan qayta aloqa olish uchun qancha kuch sarflaysiz?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I — IMPLICATION (Oqibat) Savollar
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Maqsad: Muammoning katta ekanini — uning oqibatlarini ko'rsatish.
Bu eng KUCHLI savol turi. Katta sotuvlarda hal qiluvchi rol o'ynaydi.
Maqsad: Mijoz muammoni o'zi "katta" deb his qilsin.

Samarali Implication savollar:
- "Agar har kuni 3 ta mijoz javobsiz ketsa, bu oyiga qancha buyurtma demak?"
- "Yilda yo'qotilgan shu buyurtmalar biznesdagi o'sishingizga qanday ta'sir qiladi?"
- "Menejer har bir savdo bo'yicha 30 daqiqa ma'lumot kiritsa — bu jamoada umumiy necha soat isrof?"
- "Agar mijoz 5 daqiqa ichida javob olmasdan ketsa, u raqibingizga boradimi?"
- "Bu muammo hal bo'lmasa, kelgusi yil aylanmangizga qanday ta'sir qiladi?"
- "Agar menejer kasal bo'lib qolsa yoki ketsa — savdo qancha vaqt to'xtab qoladi?"

Implication savol formulasi:
[Muammo] + "bu qanday ta'sir qiladi?" = Implication savol

Misol hisob-kitob (eng kuchli Implication texnikasi):
"Kuniga 3 ta mijoz × 30 kun = oyiga 90 ta yo'qolgan mijoz.
O'rtacha chek 500,000 so'm × 90 = 45 MILLION so'm yo'qotilgan daromad.
Bu siz uchun muhimmi?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
N — NEED-PAYOFF (Ehtiyoj-Foyda) Savollar
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Maqsad: Mijozni yechimning qiymatini o'zi ayttirish.
Muhim: Mijoz o'zi aytgan yechim 5x ishontiruvchi bo'ladi.

Samarali Need-Payoff savollar:
- "Agar har bir so'rov 3 daqiqada avtomatik javob olsa, bu sizga qancha qo'shimcha buyurtma beradi?"
- "Menejerlar hujjat to'ldirish o'rniga faqat bitim yopishga qarasalar — nima o'zgaradi?"
- "Agar tizim tunda ham ishlasa, erta tonggi so'rovlar yo'qolmaydimi?"
- "Bu yechim o'rnatilgandan keyin biznesdagi eng katta foyda nima bo'ladi deb o'ylaysiz?"
- "Agar aylanmangiz 20% oshsa, bu sizning biznesdagi keyingi qadamlaringizga qanday ta'sir qiladi?"

════════════════════════════════════════════════
SPIN TEXNIKASINI QO'LLASH TARTIBINI
════════════════════════════════════════════════

1. BOSQICH — Situation (1-2 savol): Hozirgi holat
2. BOSQICH — Problem (2-3 savol): Og'riq nuqtasi
3. BOSQICH — Implication (2-4 savol): Oqibat kattaligi
4. BOSQICH — Need-Payoff (1-2 savol): Mijoz yechimni o'zi istasin

MUHIM QOIDALAR:
✓ Har suhbatda Situation savollarni minimal saqlang
✓ Problem va Implication savollar eng ko'p vaqtni olsin
✓ Need-Payoff savollar bilan yopishga o'ting
✓ Hech qachon bir vaqtda 2 ta savol bermang

════════════════════════════════════════════════
KLASSIK XATOLAR
════════════════════════════════════════════════

XATO 1: Yopish texnikasini juda erta qo'llash
"Hozir sotib olasizmi?" → Mijoz hali tayyor emas

XATO 2: Faqat mahsulot xususiyatlarini gapirish
"Bizda 50 funksiya bor!" → Mijozga foyda muhim, xususiyat emas

XATO 3: Mijoz e'tiroziga darhol javob berish
Implication bosqichi to'liq bo'lmasa e'tiroz qoladi

XATO 4: Ko'p Situation savol
Mijoz so'roqqa tortilgandek his qiladi

XATO 5: Need-Payoff savolsiz yechim taqdim etish
Mijoz o'zi istamasdan yechim taqdim qilsangiz — rad etish ehtimoli yuqori

════════════════════════════════════════════════
REAL SUHBAT NAMUNASI
════════════════════════════════════════════════

Sotuvchi: Assalomu alaykum! Korxonangizda savdo bo'limi qanday ishlaydi? (Situation)
Mijoz: 3 ta menejerimiz bor, Instagram va Telegram orqali javob berishadi.

Sotuvchi: Tunda yoki dam olish kunlari menejerlar bo'lmasa, so'rovlar kutib qoladimi? (Problem)
Mijoz: Ha, ba'zan ertalab 5-10 ta javobsiz xabar bo'ladi.

Sotuvchi: Agar shu 10 ta xabardan yarmi sovib ketgan bo'lsa — bu oyiga qancha buyurtma? (Implication)
Mijoz: (hisoblaydi) ... oyiga 150 ta desa bo'ladi.

Sotuvchi: 150 ta buyurtma, o'rtacha chek 300,000 so'mdan — bu oyiga 45 mln so'm. Bu raqam siz uchun muhimmi? (Implication kuchaytirish)
Mijoz: Ha, juda katta raqam!

Sotuvchi: Agar tizim tunda ham javob berib, har bir so'rovni o'zi yopsa — bu biznesdagi nima o'zgartirar edi? (Need-Payoff)
Mijoz: Kamida 30-40% ko'proq buyurtma olardik!

Sotuvchi: Demak, tizim oyiga 45 mlnning 30-40%ini qaytarsa — bu 13-18 mln so'm. Boshlasak?
"""

# ─────────────────────────────────────────────────────────────
# KITOB 2: THE CHALLENGER SALE — Matthew Dixon & Brent Adamson
# CEB (Corporate Executive Board) — 6,000 dan ortiq sotuvchi tadqiqoti
# ─────────────────────────────────────────────────────────────
CHALLENGER_SALE_BOOK = """
THE CHALLENGER SALE — Matthew Dixon & Brent Adamson
(Harvard Business Review Press, 2011)
CEB tadqiqoti — 6,000+ sotuvchi, 100+ kompaniya

════════════════════════════════════════════════
ASOSIY KASHFIYOT
════════════════════════════════════════════════
Tadqiqotda 5 ta sotuvchi profili aniqlandi:
1. Hard Worker (Mehnatsevar) — ko'p ishlaydi, berishmasligi uchun qo'shimcha sa'y
2. Relationship Builder (Munosabat quruvchi) — mijoz bilan yaxshi munosabat
3. Lone Wolf (Yolg'iz bo'ri) — o'z usulida ishlaydi
4. Reactive Problem Solver (Reaktiv yechimchi) — muammo kelganda hal qiladi
5. CHALLENGER (Meydon qo'yuvchi) — YUTUVCHI!

Muhim: Murakkab sotuvlarda Challengerlar boshqalarga nisbatan 3x ko'proq natija beradi.
Oddiy sotuvlarda Relationship Builderlar ham yaxshi ishlaydi — lekin murakkab sotuvda ular oxirgi o'rinda.

════════════════════════════════════════════════
CHALLENGER PROFILI — KIM BU?
════════════════════════════════════════════════
Challenger sotuvchilar 3 ta noyob qobiliyatga ega:

1. TEACH (O'rgatish): Mijoz bilmagan muhim narsani o'rgatadi
2. TAILOR (Moslashtirish): Har bir mijoz uchun xabarni moslashtiradi
3. TAKE CONTROL (Jarayonni boshqarish): Sotuvni boshqaradi, bosim o'tkazadi

════════════════════════════════════════════════
TEACH — TIJORIY O'RGATISH
════════════════════════════════════════════════
Challenger sotuvchi mijozga YANGI VA FOYDALI TUSHUNCHA beradi.
Bu tushuncha:
- Mijoz bilmagan, lekin uning biznesi uchun MUHIM bo'lishi kerak
- Sotuvchining mahsuloti/xizmati bilan bog'liq bo'lishi kerak
- Mijozni "Voh, bu haqda o'ylamagan edim!" deydigan qilishi kerak

CHALLENGER TEACHING PITCH TUZILMASI:
1. WARMER (Isitish): Mijoz tan oladigan umumiy muammodan boshlang
2. REFRAME (Qayta ko'rsatish): Muammoga yangi nuqtai nazar bering
3. RATIONAL DROWNING (Mantiqiy botirilish): Raqamlar bilan muammoning kattaligini ko'rsating
4. EMOTIONAL IMPACT (Hissiy ta'sir): Shaxsiy ta'sirni ko'rsating
5. VALUE PROPOSITION (Qiymat taklifi): Yechimni taqdim eting
6. SOLUTION (Yechim): Mahsulot/xizmatni ulang

MISOL CHALLENGER TEACH:
"Ko'pchilik (Warmer) mijoz xizmatiga ko'proq pul sarflash kerak deb o'ylaydi.
Aslida (Reframe) tadqiqotimiz ko'rsatishicha, asosiy muammo — javob tezligida.
Raqamlar (Rational Drowning): Mijoz savol bergandan keyin 5 daqiqa ichida javob olmasalar, 78% raqobatchiga ketadi.
Sizda (Emotional Impact) bu oyiga qancha mijoz demak? Hisoblaylik...
Yechim (Value): 3 daqiqa ichida javob beradigan AI agent bu raqamni 0 ga tushiradi."

════════════════════════════════════════════════
TAILOR — XABARNI MOSLASHTIRISH
════════════════════════════════════════════════
Challenger sotuvchi har bir STAKEHOLDER uchun xabarni moslashtiradi.

CEO uchun: Biznes ta'siri va ROI
CFO uchun: Xarajat va tejash
Operations Manager uchun: Samaradorlik va vaqt tejash
Marketing Manager uchun: Mijoz tajribasi va konversiya

STAKEHOLDER MOSLASH TEXNIKASI:
"Siz Operations tomonda bo'lsangiz, bu tizim har kuni menejerlardan 2 soat tejaydi.
Agar moliyaviy tomoni muhim bo'lsa — oyiga tejilgan 10M so'm + 30% ko'proq daromad."

════════════════════════════════════════════════
TAKE CONTROL — JARAYONNI BOSHQARISH
════════════════════════════════════════════════
Challenger sotuvchi SOTUVNI BOSHQARADI — mijoz emas.

"Comfortable tension" yaratish:
Challenger mijozni noqulay his qildiradi — lekin bu yaxshi noqulaylik.
U mijozga yangi, qo'rqinchli haqiqatni ko'rsatadi.

TAKE CONTROL texnikasi — Bosim o'tkazish:
- Aniq muddat belgilash: "Ertaga soat 15:00 gacha javob kutaman"
- Keyingi qadam taklif qilish: "10 daqiqalik call qo'yaman — bugunmi ertami?"
- Price conversation boshqarish: "Narxdan oldin maqsadingizni tushunib olaylik"

IKKILANUVCHI MIJOZ BILAN TAKE CONTROL:
Mijoz: "O'ylab ko'raman..."
Challenger: "Tushunarli. Odatda odamlar 3 sababdan o'ylashadi:
1) Narx — byudjet yo'q
2) Vaqt — hozir to'g'ri emas
3) Ishonch — yechim ishlaydi degan kafolat yo'q
Sizda qaysi biri?"
(Bu LAER boshlanishi — aniq sababni chiqarish)

════════════════════════════════════════════════
MUNOSABAT QURUVCHI (RELATIONSHIP BUILDER) NIMA UCHUN YO'QOLADI?
════════════════════════════════════════════════
Muhim: Bu ko'pchilikni hayron qoldiradi.

Relationship Builderlar:
✓ Mijoz bilan yaxshi munosabat quradi
✓ Mijoz xohlaganda hamma narsaga "ha" deydi
✗ Murakkab sotuvlarda ENG KAM natija beradi (tadqiqot)

Nima uchun? Chunki:
- Ular mijozni noqulay his qildirmaydi
- Ular yangi tushuncha bermaydi
- Ular munosabatni saqlash uchun bosim o'tkazishdan qo'rqadi
- Ular mijoz rad etsa ham, munosabatni saqlab qolishga intiladi

Challenger esa: "Agar siz uchun to'g'ri yechim bo'lmasa — vaqtingizni olmayman. Lekin bu muammoningizni hal qiladi deb ishonaman."

════════════════════════════════════════════════
COMMERCIAL INSIGHT — TIJORIY TUSHUNCHA
════════════════════════════════════════════════
Challenger sotuvchining eng kuchli quroli: YANGI TUSHUNCHA berish.

YAXSHI Tijoriy Tushuncha:
✓ Mijoz bilmaydi yoki o'ylamagan
✓ Ularning biznesi uchun muhim
✓ Sotuvchining mahsuloti hal qiladi
✓ Raqobatchilar ayta olmaydi (yoki aytmaydi)

MISOL Tijoriy Tushuncha (sotuv agenti uchun):
"Ko'pchilik bizneslar xodim xarajatini yo'qotish uchun AI qo'llaydi.
Aslida eng katta yutuq — javob tezligida.
Tadqiqotlar: Birinchi 5 daqiqa savdoning 70% ini belgilaydi.
Siz erta tonggi soat 2:00 da kelgan so'rovga qachon javob berasiz?"

MISOL 2 Tijoriy Tushuncha (ko'chmas mulk uchun):
"Xaridorlar narx bo'yicha solishtiradi deb o'ylaysiz.
Aslida 68% xaridor birinchi javob bergan agentdan sotib oladi.
Sizning agentingiz har kuni birinchi bo'lib javob berayaptimi?"

════════════════════════════════════════════════
E'TIROZLARNI CHALLENGER USLUBIDA YO'NALTIRISH
════════════════════════════════════════════════

E'TIROZ: "Qimmat"
Relationship Builder: "Mayli, chegirma qilaman" (NOTO'G'RI)
Challenger: "Qimmat deganingizni tushunaman. Keling hisoblaylik:
Bu tizim oyiga [X] mijoz keltirsa, har bir mijoz [Y] so'm bo'lsa — ROI qancha?
Narxi ko'p ko'rinsa ham, 1.5 oyda o'zi qaytib keladi.
Assosiy savol: Oyiga [Z] so'm sarmoyangiz [Z*3] so'm qaytishi siz uchun yaxshi biznesmi?"

E'TIROZ: "Hozir vaqt emas"
Challenger: "Qachon vaqt to'g'ri bo'ladi? (Aniq javob eshitish)
Agar 3 oydan keyin bo'lsa, bu 3 oy davomida oyiga [X] so'm yo'qolishida davom etadi.
Bu yo'qolishni to'xtatish uchun to'g'ri vaqt — aynan hozir emas deysizmi?"

E'TIROZ: "O'ylab ko'raman"
Challenger: "Albatta! Odatda 3 narsa kutiladi — narx, vaqt, yoki ishonch.
Siz uchun qaysi biri muhimroq?
(Javobga qarab) Keling, aynan o'sha masalani hal qilaylik — 5 daqiqa vaqtingiz bormi?"

════════════════════════════════════════════════
CHALLENGERS BO'YICHA STATISTIKA
════════════════════════════════════════════════
- Murakkab sotuvlarda top 20% sotuvchilarning 40% i Challengerdir
- Murakkab sotuvda Challenger Relationship Builderdan 3.4x ko'proq natija beradi
- Iqtisodiy inqiroz davrida Challenger yutuvchilar 3.7x ko'proq yutadi
- Relationship Builderlar murakkab sotuvda eng oxirgi o'rinda turadi

════════════════════════════════════════════════
CHALLENGER SUHBAT TUZILMASI — AMALIY QOIDA
════════════════════════════════════════════════

1. Umumiy muammodan boshlang (mijoz tan oladi)
2. Yangi nuqtai nazar bering ("Aslida...")
3. Raqamlar bilan muammoni kattalashing
4. Shaxsiy ta'sirni ko'rsating ("Sizda bu...")
5. Yechimni taqdim eting
6. Keyingi qadamni aniq belgilang (Alternative Close)

QOIDA: Challengers don't ask for the business — they TAKE it.
(Challengers biznes so'ramaydi — ular uni olib ketishadi)
"""

# ─────────────────────────────────────────────────────────────
# KITOB 3: QO'SHIMCHA — E'TIROZ YO'NALTIRISH ENSIKLOPEDIYASI
# ─────────────────────────────────────────────────────────────
OBJECTION_HANDLING_BIBLE = """
E'TIROZ YO'NALTIRISH ENSIKLOPEDIYASI
Sotuv agentig uchun to'liq qo'llanma

════════════════════════════════════════════════
LAER FRAMEWORK — TO'LIQ TUSHUNTIRISH
════════════════════════════════════════════════
L — LISTEN (Tinglash)
A — ACKNOWLEDGE (Tan olish)
E — EXPLORE (O'rganish)
R — RESPOND (Javob berish)

════════════════════════════════════════════════
25 TA ENG KO'P UCHRAYDIGAN E'TIROZ VA PROFESSIONAL JAVOBLAR
════════════════════════════════════════════════

─────────────────────────────────────────────
NARX E'TIROZLARI
─────────────────────────────────────────────
E'TIROZ 1: "Juda qimmat"
Javob: "To'g'ri, narx muhim. Asosiy savol: Bu tizim oyiga qancha daromad keltiradi?
Agar [narx]ni [qaytish muddati] da qaytarsa — bu qanday ko'rinadi siz uchun?"

E'TIROZ 2: "Byudjet yo'q"
Javob: "Tushunarli. Ko'pchilik shunday boshlaydi.
Keling, teskari hisob qilaylik: Tizim oyiga qancha tejaydi yoki keltiradi?
Agar u o'zini 45 kunda to'lasa — byudjet muammomi yoki investitsiya qarorimi?"

E'TIROZ 3: "Boshqa joyda arzonroq"
Javob: "Yaxshi, alternativlarni ko'rib chiqqaningiz donolik.
Bitta savol: U yerdagi tizim [asosiy xususiyat]ni ham qiladi? (raqobatchi qila olmaydi)
Narx farqi [X] so'm, lekin natijalardagi farq qancha?"

E'TIROZ 4: "Chunki siz yangi kompaniyasiz, past narxda bering"
Javob: "Bizni tanlayotganingiz uchun rahmat! 
Biz yangi bo'lganimiz uchun narxda emas, xizmat sifatida ustunlikni isbotlaymiz.
Qo'shilish uchun [imtiyoz]ni taklif qilaman — bu sizga qiziqmi?"

─────────────────────────────────────────────
VAQT VA URGENCY E'TIROZLARI
─────────────────────────────────────────────
E'TIROZ 5: "Hozir vaqt emas"
Javob: "Qachon to'g'ri vaqt bo'ladi?
(Aniq javob) Agar [oy/muddat] bo'lsa — bu orada oyiga [X] so'm yo'qolishida davom etadi.
To'g'ri vaqt — muammo borida."

E'TIROZ 6: "Biz hozir boshqa loyihada band"
Javob: "Tushunarli! Ko'p korporatsiyalar shunday boshlamoqda.
Keling, bu loyiha tugagach uchun hozirdan tayyorlanaylik — 15 daqiqalik kirish suhbati qilib qo'yaylik?"

E'TIROZ 7: "Yangi yilda boshlaymiz"
Javob: "Mantiqiy! Yangi yil uchun tayyorgarlik odatda [muddat] oldin boshlanadi.
Agar yangi yildan ishga tushirmoqchi bo'lsangiz — [sanadan] boshlashimiz kerak.
Bu kun nechida?"

─────────────────────────────────────────────
ISHONCH VA SHUBHA E'TIROZLARI
─────────────────────────────────────────────
E'TIROZ 8: "Ishlaydi degan kafolatim yo'q"
Javob: "Siz bilan kelishaman — ishonch ko'rgazmali bo'lishi kerak.
Shuning uchun biz [demo/sinov] taklif qilamiz.
2 haftalik bepul sinov — yoqmasa to'lamaysiz. Boshlasak?"

E'TIROZ 9: "Siz haqingizda eshitmagan edim"
Javob: "To'g'ri, biz marketing o'rniga natijaga sarmoya qilamiz.
[Mijoz ismi/kompaniyasi] ham shu sababdan tanlagan — siz ham ulasha olasizmi?
Men hoziroq reference beray."

E'TIROZ 10: "Hujjat/shartnoma ko'rsata olasizmi?"
Javob: "Albatta! [hujjat turi]ni darhol yuboraman.
Elektron pochta manzilingiz qaysi?"

─────────────────────────────────────────────
RAQOBAT E'TIROZLARI
─────────────────────────────────────────────
E'TIROZ 11: "Biz allaqachon [raqobatchi] ishlatamiz"
Javob: "Yaxshi tanlov! Ular nima uchun yaxshi ishlaydi sizda?
(Tinglash)
Keling, qaysi jihati yetishmayotgan — o'sha borada biz qanday yordam bera olamizni ko'rsataylik."

E'TIROZ 12: "Biz o'zimiz qilamiz / dasturchi bor"
Javob: "Zo'r! O'z rivojlanish qobiliyatingiz kuchli ustunlik.
Savol: Tizimni qurish vaqti va AI/ML integratsiya uchun qancha muddat va narx mo'ljallayapsiz?
Biz bu [muddat]ni [muddatga] tushiramiz."

─────────────────────────────────────────────
KECHIKTIRISH E'TIROZLARI
─────────────────────────────────────────────
E'TIROZ 13: "O'ylab ko'raman"
Javob: "Albatta! Odatda 3 narsa kutiladi: narx, vaqt, yoki ishonch.
Sizda qaysi biri?
(Javobga qarab aniq hal qilish)"

E'TIROZ 14: "Sherigim/xotinim/ota bilan maslahatlashaman"
Javob: "Ajoyib — katta qarorlar birgalikda! 
Ularning asosiy savollari nima bo'ladi deb o'ylaysiz?
Keling, u savollarni hoziroq hal qilaylik — suhbatda ulardan savol kelmasin."

E'TIROZ 15: "Menejmentga ko'rsatishim kerak"
Javob: "Albatta! Menejment uchun qisqa taqdimot tayyorlab beraman.
Ular uchun eng muhim raqamlar: ROI, qaytish muddati, va risk kafolati.
Shu 3 ta raqamni taqdimotga kiritib, ertaga yuboraymi?"

─────────────────────────────────────────────
MAHSULOT VA TEXNIK E'TIROZLAR
─────────────────────────────────────────────
E'TIROZ 16: "Bizning sohaga mos emas"
Javob: "Qiziq! Qaysi jihati tashvish qo'ldiradi?
[Sohaga tegishli mijoz misoli]da ham shunday deb o'ylashgan — keling, ularning tajribasini ko'rsataylik."

E'TIROZ 17: "Integratsiyalar bor? Bizimcha tizimga ulana oladimi?"
Javob: "Ha, [asosiy integratsiyalar] bor. Siz qaysi tizim ishlatayapsiz?
[tizim nomi] — biz bilan ulanish [muddat/narx]."

E'TIROZ 18: "Ma'lumotlar xavfsizligi qanday?"
Javob: "Muhim savol! Biz [standart/sertifikat] talablariga amal qilamiz.
[Xavfsizlik tavsifi]. Batafsil hujjat kerakmi?"

═══════════════════════════════════════════════
YOPISH TEXNIKALARI — COMPLETE GUIDE
═══════════════════════════════════════════════

1. ALTERNATIVE CLOSE (Alternativ yopish)
Har doim 2 ta variant bering — hech qachon "ha yoki yo'q" emas.
"Bugun 16:00 mi yoki ertaga 11:00?"
"Starter tarifdan boshlaymizmi yoki Professional?"

2. ASSUMPTIVE CLOSE (Faraz qiluvchi yopish)
Savdo bo'layotganini faraz qilib harakat qiling.
"Yaxshi, men hozir profil sozlamasini boshlayapman. Korxona nomingiz?"
"Yetkazib berish uchun manzilingiz qaysi?"

3. SUMMARY CLOSE (Xulosa yopish)
Kelishilgan narsalarni sanab, yopishga o'ting.
"Xo'sh, siz [muammo]ni hal qilmoqchisiz, byudjet [X], qarorni siz qabul qilasiz — boshlasak?"

4. PUPPY DOG CLOSE (Ko'chkichak yopish)
Risk 0 — sinab ko'ring, yoqmasa qaytaring.
"2 haftalik bepul sinov qiling — yoqmasa hech nima to'lamaysiz."

5. SCARCITY CLOSE (Tanqislik yopish)
Cheklangan taklif (faqat haqiqiy bo'lsa ishlatish).
"Bu oy faqat 3 ta slot bor — bittasini band qilaylikmi?"
"Bu narx faqat 30 oktyabrgacha amal qiladi."

6. ROI CLOSE (ROI yopish)
Raqamlar bilan qaror qilish osonlashadi.
"Tizim oyiga [X] so'm keltirsa, [narx]ni qoplash uchun [N] ta buyurtma yetarli.
Siz oyiga [N] tadan ko'proq buyurtma qilasizmi?"

7. NEXT STEP CLOSE (Keyingi qadam yopish)
Katta qaror so'ramasdan, kichik qadam.
"Demo ko'rish uchun 15 daqiqa ajratardingizmi? Ertami yoki indinmi?"

═══════════════════════════════════════════════
URGENCY YARATISH — HAQIQIY VA ETIK USULLAR
═══════════════════════════════════════════════

HAQIQIY URGENCY:
1. Muammoningiz har kuni pul yo'qotyapti: "Har kuni [X] so'm ketmoqda"
2. Muddatli taklif (agar haqiqiy bo'lsa): "Bu narx [sana]gacha"
3. Cheklangan joy (agar haqiqiy bo'lsa): "Bu oyda [N] ta slot bor"
4. Mavsum: "Faol savdo davri boshlanishidan oldin tayyorlanish kerak"

NOTO'G'RI URGENCY (Ishlatmang):
✗ Yolg'on muddatlar
✗ Sun'iy tanqislik
✗ Soxta chegirma muddatlari
→ Bu mijozning ishonchini yo'q qiladi va uzun muddatda zarar
"""

# ─────────────────────────────────────────────────────────────
# SEEDER MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

TRAINING_BOOKS = [
    {
        "title": "SPIN Selling — Neil Rackham [Ichki Treningdan]",
        "item_type": "training_book",
        "content": SPIN_SELLING_BOOK.strip(),
        "metadata": {
            "source": "internal_training",
            "book": "SPIN Selling",
            "author": "Neil Rackham",
            "category": "sales_methodology",
            "visible_to_client": False,
            "language": "uz"
        }
    },
    {
        "title": "The Challenger Sale — Dixon & Adamson [Ichki Treningdan]",
        "item_type": "training_book",
        "content": CHALLENGER_SALE_BOOK.strip(),
        "metadata": {
            "source": "internal_training",
            "book": "The Challenger Sale",
            "author": "Matthew Dixon & Brent Adamson",
            "category": "sales_methodology",
            "visible_to_client": False,
            "language": "uz"
        }
    },
    {
        "title": "E'tiroz Yo'naltirish Ensiklopediyasi — 25 ta E'tiroz [Ichki Treningdan]",
        "item_type": "training_book",
        "content": OBJECTION_HANDLING_BIBLE.strip(),
        "metadata": {
            "source": "internal_training",
            "book": "Objection Handling Bible",
            "author": "VertaFlow Sales Intelligence",
            "category": "objection_handling",
            "visible_to_client": False,
            "language": "uz"
        }
    }
]


def seed_training_books(workspace_ids: list = None, skip_existing: bool = True):
    """
    Seeds training books into knowledge_items for given workspaces.
    If workspace_ids is None, seeds for ALL workspaces.
    """
    conn = db.get_connection()

    # Get all workspaces if not specified
    if workspace_ids is None:
        rows = conn.execute("SELECT id FROM businesses;").fetchall()
        workspace_ids = [r["id"] for r in rows]
        if not workspace_ids:
            workspace_ids = ["default"]


    print(f"🚀 {len(TRAINING_BOOKS)} ta kitob → {len(workspace_ids)} ta workspace ga yuklanmoqda...")
    print()

    total_added = 0

    for ws_id in workspace_ids:
        print(f"📂 Workspace: {ws_id}")
        for book in TRAINING_BOOKS:
            # Skip if already exists in this workspace
            if skip_existing:
                existing = conn.execute(
                    "SELECT id FROM knowledge_items WHERE title = ? AND workspace_id = ?;",
                    (book["title"], ws_id)
                ).fetchone()
                if existing:
                    print(f"   ⏭️  Allaqachon mavjud: {book['title'][:60]}...")
                    continue

            # Insert knowledge item
            meta_json = json.dumps(book["metadata"], ensure_ascii=False)
            cursor = conn.execute(
                """INSERT INTO knowledge_items (title, item_type, content, metadata, workspace_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (book["title"], book["item_type"], book["content"], meta_json, ws_id)
            )
            item_id = cursor.lastrowid
            conn.commit()
            total_added += 1
            print(f"   ✅ Qo'shildi (ID={item_id}): {book['title'][:60]}...")

        print()

    conn.close()
    print(f"✅ Jami {total_added} ta kitob qo'shildi.")
    print()

    # Now trigger RAG indexing
    if total_added > 0:
        print("🧠 RAG indekslash boshlanmoqda...")
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from core.verta_rag import get_rag_engine
            rag = get_rag_engine()
            rag.sync_all_knowledge()
            print("✅ RAG indekslash tugadi!")
        except Exception as e:
            print(f"⚠️  RAG indekslash keyinroq (server ishga tushganda) amalga oshiriladi: {e}")
            print("   Server ishga tushganda avtomatik indekslanadi.")

    return total_added


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="VertaFlow Sales Training Books Seeder"
    )
    parser.add_argument(
        "--workspace",
        default="ALL",
        help="Workspace ID (default: ALL workspaces)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-insert even if already exists"
    )
    args = parser.parse_args()

    if args.workspace == "ALL":
        ws_ids = None  # All workspaces
    else:
        ws_ids = [args.workspace]

    seed_training_books(workspace_ids=ws_ids, skip_existing=not args.force)
