# 🌸 Gul Savdo Bot

Telegram orqali gul sotish va auksiyon qilish uchun bot.

## Xususiyatlar

### Foydalanuvchi uchun:
- 🌸 Gul qoshish (rasm, nom, tavsif, narx, telefon, manzil)
- 💎 Almaz sotib olish (tolov cheki orqali)
- 👤 Profil korish
- 📋 Gullarni boshqarish

### Auksiyon tizimi:
- 🔨 Auksiyon boshlash (vaqt tanlash: 30 daqiqa - 24 soat)
- 👥 Ishtirokchilar soni korinadi
- 💬 Barcha ishtirokchilar bir-birining stavkalarini korishadi
- 📊 Stavkalar tarixi
- 🚪 Auksiyondan chiqish imkoniyati
- 🏁 Sotuvchi uchun auksiyonni tugatish tugmasi
- ⏰ Avtomatik tugash (belgilangan vaqtda)
- 🏆 Gholib avtomatik aniqlanadi

### Admin uchun:
- 💳 Karta raqamini ozgartirish
- 💰 Almaz narxini ozgartirish
- 💎 Foydalanuvchilarga almaz qoshish
- 📊 Statistika korish
- 📢 Barcha foydalanuvchilarga xabar yuborish
- ✅ Tolovlarni tasdiqlash/rad etish

## Ornatish

### 1. Talablar
- Python 3.10+
- Telegram Bot Token (@BotFather dan oling)
- Telegram Channel ID

### 2. Kutubxonalarni ornatish

```bash
pip install -r requirements.txt
```

### 3. Sozlamalar

`.env.example` faylini `.env` ga kopiring va sozlang:

```bash
cp .env.example .env
```

`.env` faylini tahrirlang:

```env
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
CHANNEL_ID=-1001234567890
ADMIN_IDS=123456789,987654321
CARD_NUMBER=8600 1234 5678 9012
DIAMOND_PRICE=10000
```

### Qiymatlar:
- `BOT_TOKEN` - @BotFather dan olingan token
- `CHANNEL_ID` - Kanalning ID si (- bilan boshlanadi)
- `ADMIN_IDS` - Admin Telegram ID lari (vergul bilan ajratilgan)
- `CARD_NUMBER` - Tolov uchun karta raqami
- `DIAMOND_PRICE` - 1 almaz narxi (som)

### 4. Botni ishga tushirish

```bash
python bot.py
```

## Narxlar

- Oddiy e'lon: 1 almaz
- Auksiyon e'loni: 2 almaz

## Foydalanish

### Gul qoshish (Oddiy sotish):
1. "🌸 Gul qoshish" tugmasini bosing
2. Gulning rasmini yuboring
3. Gul nomini kiriting
4. Tavsifini yozing
5. Narxini belgilang
6. Telefon raqamingizni kiriting
7. Manzilingizni yozing
8. "🛒 Oddiy sotish" ni tanlang

### Auksiyon boshlash:
1. "🌸 Gul qoshish" tugmasini bosing
2. Gulning rasmini yuboring
3. Gul nomini kiriting
4. Tavsifini yozing
5. Boshlangich narxini belgilang
6. Telefon raqamingizni kiriting
7. Manzilingizni yozing
8. "🔨 Auksiyon" ni tanlang
9. Auksiyon davomiyligini tanlang (30 daqiqa - 24 soat)

### Auksiyonga qoshilish:
1. Kanaldagi auksiyon e'lonida "🔨 Auksiyonga kirish" tugmasini bosing
2. Bot sizni auksiyon xonasiga qoshadi
3. Stavka qoyish uchun narxni yozing (faqat son)
4. Barcha ishtirokchilar yangi stavkalarni korishadi

### Almaz sotib olish:
1. "💎 Almaz sotib olish" tugmasini bosing
2. Almaz sonini tanlang
3. Korsatilgan karta raqamiga tolov qiling
4. Tolov chekini rasm sifatida yuboring
5. Admin tasdiqlashini kuting

## Texnik malumotlar

- Framework: aiogram 3.x
- Database: SQLite + SQLAlchemy (async)
- FSM Storage: Memory
- Scheduler: asyncio (har daqiqada auksiyon vaqtini tekshiradi)

## Loyiha tuzilmasi

```
flower_bot/
├── bot.py              # Asosiy fayl
├── config.py           # Sozlamalar
├── requirements.txt    # Kutubxonalar
├── .env.example        # Sozlamalar namunasi
├── database/
│   ├── __init__.py
│   ├── connection.py   # DB ulanish
│   ├── models.py       # Modellar (User, Flower, Payment, AuctionParticipant, AuctionBid)
│   └── queries.py      # So'rovlar
├── handlers/
│   ├── __init__.py
│   ├── user.py         # Foydalanuvchi handlerlari
│   ├── admin.py        # Admin handlerlari
│   └── auction.py      # Auksiyon handlerlari (chat funksiyasi)
├── keyboards/
│   ├── __init__.py
│   └── keyboards.py    # Klaviaturalar
├── states/
│   ├── __init__.py
│   └── states.py       # FSM holatlari
└── utils/
    ├── __init__.py
    └── scheduler.py    # Avtomatik auksiyon tugash
```

## Auksiyon ishlash tartibi

1. Sotuvchi auksiyon boshlaydi va vaqtni tanlaydi
2. Kanal ga habar joylashadi (link bilan)
3. Foydalanuvchilar link orqali botga kirib auksiyonga qoshiladi
4. Har bir ishtirokchi stavka qoysa, barcha ishtirokchilarga habar boradi
5. Ishtirokchilar "🚪 Auksiyondan chiqish" tugmasi orqali chiqishi mumkin
6. Sotuvchi "🏁 Auksiyonni tugatish" tugmasi bilan auksiyonni tugatishi mumkin
7. Yoki belgilangan vaqt tugaganda avtomatik tugaydi
8. Eng yuqori stavka qoygan gholib boladi va unga alohida habar yuboriladi
