# /home/kinfolkt/verta-platform/core/verta_templates.py
"""
VertaFlow — Industry Sales Templates Repository (Creator / Admin Only)
Pre-configured, high-converting SPIN Selling & Challenger closer templates
tailored specifically for the Uzbek market and high-demand business niches.
"""

from typing import Dict, Any, List

NICHE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "mebel": {
        "id": "mebel",
        "name": "Mebel Fabrikasi & Buyurtma Mebel",
        "icon": "🪑",
        "category": "Ishlab chiqarish & Savdo",
        "description": "Oshxona, shkaf-kupe, yotoqxona va ofis mebellari uchun bepul zamer (o'lchov olish) va kafolatga asoslangan savdo voronkasi.",
        "business_name": "Grand Mebel Fabrikasi",
        "business_desc": "Oshxona, yotoqxona va premium mebellarni individual o'lchamda ishlab chiqarish va bepul o'rnatib berish.",
        "avg_check": "4 500 000 so'm",
        "persona": {
            "name": "Madina",
            "role": "Mebel dizayneri va savdo maslahatchisi",
            "tone": "friendly_closer",
            "max_discount": "10%"
        },
        "faq_list": [
            {
                "question": "Oshxona mebellarining narxi qanchadan boshlanadi?",
                "answer": "Oshxona mebellari 1 pogon metri 2 500 000 so'mdan boshlanadi. Narx tanlangan fasad (Akril, MDF, Emal) va mexanizmlarga (Blum, Samet) bog'liq."
            },
            {
                "question": "O'lchov olish (zamer) pullikmi?",
                "answer": "Yo'q, Toshkent shahri bo'ylab uyingizga usta-texnologimiz borib professional o'lchov olishi va 3D eskiz chizishi mutlaqo bepul."
            },
            {
                "question": "Mebellarga kafolat bormi va furnituralar qayerdan?",
                "answer": "Barcha mebellarimizga 5 yillik rasmiy kafolat beramiz. Furnituralar Avstriyaning Blum va Turkiyaning Samet brendlaridan foydalaniladi."
            },
            {
                "question": "Buyurtma necha kunda tayyor bo'ladi?",
                "answer": "Shartnoma tuzilib, 3D dizayn tasdiqlangach, 7-12 ish kunida to'liq tayyorlab, bepul yetkazib o'rnatib beramiz."
            }
        ],
        "battlecards": [
            {
                "name": "Bozordagi arzon sexlar",
                "keywords": ["bozorda arzon", "ustaxonada arzonroq", "1.5 million", "boshqa sex"],
                "their_weakness": "Kafolatsiz, arzon Xitoy samorez va petlyalar ishlatadi, 1 yilda fasad shishib qoladi.",
                "reframe_talk_track": "Bozorda 500 ming arzon topish mumkin, lekin 1 yilda eshiklari tushib qolsa yoki shishsa, boshqatdan mebel qilishga to'g'ri keladi. Biz esa 5 yil rasmiy kafolat va asl Blum mexanizmlari bilan o'rnatamiz.",
                "landmine_question": "Usta sizga yozma 5 yillik rasmiy kafolat beryaptimi yoki og'zaki va'da qilyaptimi?"
            }
        ]
    },
    "oqim_kurs": {
        "id": "oqim_kurs",
        "name": "O'quv Markazi / IT Akademiya",
        "icon": "📚",
        "category": "Ta'lim & Kasb-hunar",
        "description": "IELTS, Dasturlash (Frontend, Backend, Python), Grafik dizayn va SMM kurslari uchun bepul sinov darsiga yozish voronkasi.",
        "business_name": "Apex IT & Language Academy",
        "business_desc": "Zamonaviy IT kasblari, General English va IELTS bo'yicha amaliy ta'lim va ishga joylashish kafolati.",
        "avg_check": "650 000 so'm",
        "persona": {
            "name": "Jasur",
            "role": "Ta'lim bo'yicha kordinator",
            "tone": "friendly_closer",
            "max_discount": "15%"
        },
        "faq_list": [
            {
                "question": "Kurslar narxi qancha va davomiyligi qanaqa?",
                "answer": "Kurslarimiz oyiga 600 000 dan 900 000 so'mgacha. Davomiyligi yo'nalishga qarab 3 oydan 8 oygacha."
            },
            {
                "question": "Oldin o'qimaganman, noldan boshlasam bo'ladimi?",
                "answer": "Albatta! 80% o'quvchilarimiz mutlaqo noldan boshlashadi. Har bir guruh daraja bo'yicha alohida saralanadi."
            },
            {
                "question": "Sinov darsi bormi, ko'rib kelsam bo'ladimi?",
                "answer": "Ha, birinchi darsimiz mutlaqo bepul! Dars jarayoni va ustozimiz bilan shaxsan tanishib, keyin qaror qabul qilishingiz mumkin."
            },
            {
                "question": "Kurs tugagach sertifikat va ishga joylashish bormi?",
                "answer": "Ha, xalqaro andozadagi sertifikat beriladi va eng yaxshi bitiruvchilarni hamkor IT kompaniyalarimizga stajirovkaga yo'naltiramiz."
            }
        ],
        "battlecards": [
            {
                "name": "Online bepul kurslar / YouTube",
                "keywords": ["youtubeda bor", "o'zim o'rganaman", "tekin kurs", "telegram kanal"],
                "their_weakness": "Mentorsiz, amaliy kod tekshiruvi yo'q, 95% odam 2 haftada tashlab ketadi.",
                "reframe_talk_track": "YouTubeda ma'lumot ko'p, lekin xatoingizni tekshirib, portfolio qildiradigan mentor bo'lmasa, oylab vaqt yo'qotiladi. Bizda har bir topshiriq jonli tekshiriladi.",
                "landmine_question": "Mustaqil o'rganganda kim sizning xatolaringizni to'g'rilab, portfolioingizni ishga tayyorlab beradi?"
            }
        ]
    },
    "klinika": {
        "id": "klinika",
        "name": "Tibbiyot Klinikasi & Stomatologiya",
        "icon": "🏥",
        "category": "Salomatlik & Tibbiyot",
        "description": "Tish davolash, implantatsiya, breketlar va shifokor ko'rigiga yozish bo'yicha g'amxo'r va ishonchli savdo voronkasi.",
        "business_name": "Shifo Dent Zamonaviy Stomatologiya",
        "business_desc": "Og'riqsiz tish davolash, Germaniya implantlari va estetik tabassum yaratish markazi.",
        "avg_check": "1 200 000 so'm",
        "persona": {
            "name": "Nilufar",
            "role": "Klinika tibbiy administratori",
            "tone": "corporate_formal",
            "max_discount": "5%"
        },
        "faq_list": [
            {
                "question": "Shifokor ko'rigi va maslahati qancha turadi?",
                "answer": "Birlamchi shifokor ko'rigi va davolash rejasi tuzib berish mutlaqo bepul."
            },
            {
                "question": "Davolash og'riqlimi?",
                "answer": "Mutlaqo og'riqsiz! Biz Germaniyaning eng so'nggi kompyuterli anesteziya tizimidan foydalanamiz, igna sanchishi ham sezilmaydi."
            },
            {
                "question": "Implantatsiya narxi qancha va qaysi davlatniki?",
                "answer": "Shveysariyaning Straumann va Janubiy Koreyaning Osstem implantlari ishlatiladi. Narxlar 2.5 mln so'mdan boshlanadi va umrbod kafolat beriladi."
            },
            {
                "question": "Bo'lib to'lash imkoniyati bormi?",
                "answer": "Ha, breket va implantatsiya xizmatlarimizga foizsiz muddatli to'lov (rassrochka) mavjud."
            }
        ],
        "battlecards": [
            {
                "name": "Oddiy poliklinika / xususiy kabinet",
                "keywords": ["davlat poliklinikasi", "arzon stomatologiya", "mahalladagi usta"],
                "their_weakness": "Eski uskunalar, to'liq sterilizatsiya nazorati yo'qligi, kafolatsiz.",
                "reframe_talk_track": "Tish — bir umrlik salomatlik. Arzon joyda noto'g'ri plomba yoki nosteril asbob tushsa, asabni yo'qotish yoki qayta davolash 3 barobar qimmatga tushadi. Bizda 100% germetik avtoklav sterilizatsiya kafolatlanadi.",
                "landmine_question": "Siz borayotgan joyda asboblar qaysi standartda sterilizatsiya qilinishini ko'rsatib bera olishadimi?"
            }
        ]
    },
    "avto": {
        "id": "avto",
        "name": "Avtoservis & Ehtiyot Qismlar",
        "icon": "🚗",
        "category": "Avtomobil & Servis",
        "description": "Kompyuter diagnostikasi, moy almashtirish, xodovoy qismlar va original ehtiyot qismlar buyurtmasi voronkasi.",
        "business_name": "ProAuto Servis Markazi",
        "business_desc": "Barcha turdagi avtomobillarni kompyuter diagnostika qilish, sifatli ta'mirlash va original zapchastlar.",
        "avg_check": "450 000 so'm",
        "persona": {
            "name": "Dilshod",
            "role": "Katta usta va qabul muhandisi",
            "tone": "direct_closer",
            "max_discount": "5%"
        },
        "faq_list": [
            {
                "question": "Diagnostika narxi qancha va necha daqiqa vaqt oladi?",
                "answer": "Kompyuter diagnostikasi 80 000 so'm, atigi 15 daqiqa vaqt oladi va barcha tizimlar bo'yicha yozma hisobot beriladi."
            },
            {
                "question": "Zapchastlar o'zingizda bormi yoki olib kelish kerakmi?",
                "answer": "Omborimizda 5000 dan ortiq original va sifatli dublikat qismlar bor. O'zingiz bozor qidirib yurmaysiz, usta joyida o'rnatib beradi."
            },
            {
                "question": "Bajarilgan ishga kafolat berasizmi?",
                "answer": "Albatta, barcha ta'mirlash ishlari va o'rnatilgan zapchastlarga 6 oydan 1 yilgacha rasmiy kafolat beriladi."
            }
        ],
        "battlecards": [
            {
                "name": "Ko'chadagi usta / Sergeli bozori",
                "keywords": ["ko'chadagi usta", "bozorda arzon", "tanish usta"],
                "their_weakness": "Chek yo'q, kafolat yo'q, noto'g'ri diagnostika qilib keraksiz zapchast almashtiradi.",
                "reframe_talk_track": "Ko'p haydovchilar arzon ustaga borib, asl muammo qolib boshqa detalni almashtirib sarson bo'lishadi. Bizda litsenziyalangan skaner bilan aniq sabab topiladi.",
                "landmine_question": "Agar ko'chadagi usta detalni almashtirgach muammo tuzalmasa, zapchast pulingizni qaytarib beradimi?"
            }
        ]
    },
    "kiyim": {
        "id": "kiyim",
        "name": "Kiyim-kechak & Brend Do'koni",
        "icon": "👗",
        "category": "Chakana Savdo & Moda",
        "description": "Erkaklar va ayollar kiyimlari, poyabzallar, o'lcham tanlash va O'zbekiston bo'ylab kuryer yetkazib berish voronkasi.",
        "business_name": "Moda Elegance Uzbekistan",
        "business_desc": "Turkiya va Yevropaning eng so'nggi urfdagi sifatli liboslari, krossovka va aksessuarlari.",
        "avg_check": "380 000 so'm",
        "persona": {
            "name": "Kamola",
            "role": "Moda va stil bo'yicha maslahatchi",
            "tone": "friendly_closer",
            "max_discount": "10%"
        },
        "faq_list": [
            {
                "question": "Yetkazib berish shartlari qanaqa va narxi qancha?",
                "answer": "Toshkent shahri bo'ylab 24 soat ichida bepul yetkazamiz. Viloyatlarga BTS yoki O'zbekiston pochtasi orqali 2 kunda yetkaziladi."
            },
            {
                "question": "Razmer to'g'ri kelmasa almashtirib beriladimi?",
                "answer": "Ha, albatta! Kuryer sizga kiyib ko'rish uchun 2 ta razmer olib boradi. Agar ma'qul kelmasa, bemalol almashtirib beramiz."
            },
            {
                "question": "To'lovni oldindan qilish kerakmi?",
                "answer": "Yo'q, to'lovni mahsulotni qo'lingizga olib, ko'rib tekshirganingizdan keyin Click, Payme yoki naqd pulda qilasiz."
            }
        ],
        "battlecards": [
            {
                "name": "Xitoy arzon bozorlari",
                "keywords": ["bozorda 100 ming", "temu", "aliexpress", "sintetika"],
                "their_weakness": "Sintetika, 2 marta yuvganda rangi ketadi, razmeri to'g'ri kelmaydi.",
                "reframe_talk_track": "Bozordagi arzon kiyimlar 1-yuvishdayoq cho'zilib, shaklini yo'qotadi. Bizning kiyimlarimiz 100% paxta va Turkiya matosi bo'lib, 2-3 mavsum yangidek saqlanadi.",
                "landmine_question": "Bozorga borib tiqilinchda yurish va kiyib ko'rish noqulayligi siz uchun qulaymi yoki kuryer uyingizga olib kelganimi?"
            }
        ]
    },
    "real_estate": {
        "id": "real_estate",
        "name": "Ko'chmas Mulk / Novostroyka",
        "icon": "🏠",
        "category": "Ko'chmas Mulk & Investitsiya",
        "description": "Yangi qurilayotgan xonadonlar, foizsiz muddatli to'lov (rassrochka) va obyekt ko'rigiga taklif qilish voronkasi.",
        "business_name": "Tashkent City Residences",
        "business_desc": "Toshkentning markaziy tumanlarida zamonaviy qulayliklarga ega premium va biznes klass turar-joy majmualari.",
        "avg_check": "65 000 $",
        "persona": {
            "name": "Rustam",
            "role": "Investitsiya va ko'chmas mulk bo'yicha ekspert",
            "tone": "corporate_formal",
            "max_discount": "5%"
        },
        "faq_list": [
            {
                "question": "Kvadrat metri necha puldan boshlanadi?",
                "answer": "1 kv. metri 9 500 000 so'mdan boshlanadi. Qavat va ko'rinishga (panoramik derazalar) qarab hisoblanadi."
            },
            {
                "question": "Bo'lib to'lash (muddatli to'lov) shartlari qanaqa?",
                "answer": "30% boshlang'ich to'lov bilan 24 oygacha 0% foizsiz muddatli to'lov (rassrochka) mavjud. Hech qanday bank foizlarisiz."
            },
            {
                "question": "Topshirilish muddati qachon va kadastr bormi?",
                "answer": "Majmuamiz 2026-yil 4-choragida to'liq topshiriladi va har bir xonadonga alohida davlat kadastri rasmiylashtirib beriladi."
            },
            {
                "question": "Xonadonlar qanday holatda topshiriladi?",
                "answer": "Xonadonlar 'White Box' (suvoqdan chiqqan, santexnika va radiatorlar o'rnatilgan, ikki qavatli baquvvat eshik) holatida topshiriladi."
            }
        ],
        "battlecards": [
            {
                "name": "Shubhali arzon kotlovanlar",
                "keywords": ["boshqa joyda 6 million", "arzon novostroyka", "katlavan"],
                "their_weakness": "Hujjatlari to'liq emas, qurilishi yillab to'xtab qolish xavfi yuqori.",
                "reframe_talk_track": "Kvartira xaridida 10-15 million tejash deb ruxsatsiz yoki muddati kechikadigan quruvchiga pul tikish juda xavfli. Bizda barcha shaharsozlik ruxsatnomalari va bank akkreditatsiyasi mavjud.",
                "landmine_question": "Boshqa kompaniyaning barcha qurilish ruxsatnomalari va yer ajratish qarorlari Davlat arxitekturasidan tasdiqlanganmi?"
            }
        ]
    }
}

def get_all_templates() -> List[Dict[str, Any]]:
    """Returns summary list of all available niche templates."""
    result = []
    for tid, t in NICHE_TEMPLATES.items():
        result.append({
            "id": t["id"],
            "name": t["name"],
            "icon": t["icon"],
            "category": t["category"],
            "description": t["description"],
            "avg_check": t["avg_check"],
            "faq_count": len(t["faq_list"]),
            "battlecard_count": len(t["battlecards"])
        })
    return result

def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full template details."""
    return NICHE_TEMPLATES.get(template_id)
