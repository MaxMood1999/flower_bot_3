from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import json
import asyncio

from database import async_session
from database.queries import (
    get_or_create_user, get_user, update_user_balance,
    create_flower, get_flower, update_flower_status, get_user_flowers,
    get_setting, add_auction_participant, get_auction_participants
)
from keyboards import (
    main_menu_kb, admin_menu_kb, cancel_kb, flower_type_first_kb,
    topup_balance_kb, flower_channel_kb, auction_duration_kb, 
    auction_participant_kb, phone_share_kb, regions_kb
)
from states import FlowerStates, PaymentStates
from config import ADMIN_IDS, CHANNEL_ID, REGULAR_POST_PRICE, AUCTION_POST_PRICE, CARD_NUMBER

router = Router()

# Store for collecting media groups
media_collection_tasks = {}

# Store for pending flower data (user_id -> flower_data)
pending_flowers = {}


def format_price(amount: int) -> str:
    """Format price with thousands separator"""
    return f"{amount:,}".replace(",", " ")


def get_first_name(full_name: str) -> str:
    """Extract first name from full name"""
    if not full_name:
        return "Foydalanuvchi"
    return full_name.split()[0]


def get_menu_kb(user_id: int, user=None):
    """Get appropriate menu keyboard"""
    is_admin = user_id in ADMIN_IDS or (user and user.is_admin)
    return admin_menu_kb() if is_admin else main_menu_kb()


def topup_for_flower_kb(required_amount: int) -> InlineKeyboardMarkup:
    """Keyboard for topping up to publish flower"""
    builder = InlineKeyboardBuilder()
    
    # Add amounts that cover the required amount
    amounts = [10000, 20000, 30000, 50000, 100000, 200000]
    suitable_amounts = [a for a in amounts if a >= required_amount]
    if not suitable_amounts:
        suitable_amounts = [100000, 200000]
    
    row1 = []
    row2 = []
    for i, amount in enumerate(suitable_amounts[:4]):
        btn = InlineKeyboardButton(
            text=f"{format_price(amount)} som", 
            callback_data=f"topup_flower_{amount}"
        )
        if i < 2:
            row1.append(btn)
        else:
            row2.append(btn)
    
    if row1:
        builder.row(*row1)
    if row2:
        builder.row(*row2)
    
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_flower_payment")
    )
    return builder.as_markup()


# ==================== START ====================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    
    # Check if this is auction join link
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("auction_"):
        flower_id = int(args[1].replace("auction_", ""))
        await join_auction(message, flower_id, bot)
        return
    
    # Get user's first name for greeting
    first_name = get_first_name(message.from_user.full_name)
    
    async with async_session() as session:
        user, is_new = await get_or_create_user(
            session, 
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name
        )
        
        regular_price = await get_setting(session, "regular_post_price")
        regular_price = int(regular_price) if regular_price else REGULAR_POST_PRICE
        
        auction_price = await get_setting(session, "auction_post_price")
        auction_price = int(auction_price) if auction_price else AUCTION_POST_PRICE
        
        # Show bonus message for new users
        bonus_text = ""
        if is_new:
            bonus_text = f"\n\n🎁 <b>Tabriklaymiz!</b> Sizga 100,000 som bonus berildi!"
        
        await message.answer(
            f"🌸 Assalomu alaykum, <b>{first_name}</b>!\n\n"
            f"Rebloom gul savdo botiga xush kelibsiz!\n\n"
            f"💰 Sizning balansingiz: {format_price(user.balance)} som\n\n"
            f"📌 Bu bot orqali gullaringizni sotishingiz yoki auksionga qoyishingiz mumkin.\n\n"
            f"💰 Narxlar:\n"
            f"• Oddiy e'lon: {format_price(regular_price)} som\n"
            f"• Auksiyon e'loni: {format_price(auction_price)} som{bonus_text}",
            parse_mode="HTML",
            reply_markup=get_menu_kb(message.from_user.id, user)
        )


async def join_auction(message: Message, flower_id: int, bot: Bot):
    """User joining auction from channel link"""
    async with async_session() as session:
        flower = await get_flower(session, flower_id)
        
        if not flower:
            await message.answer("❌ Bu auksiyon topilmadi!")
            return
        
        if flower.status != "published":
            await message.answer("❌ Bu auksiyon tugagan!")
            return
        
        if not flower.is_auction:
            await message.answer("❌ Bu oddiy e'lon, auksiyon emas!")
            return
        
        if flower.auction_end_time and datetime.utcnow() > flower.auction_end_time:
            await message.answer("❌ Bu auksiyon vaqti tugagan!")
            return
        
        from database.models import User
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == flower.user_id))
        owner = result.scalar_one_or_none()
        
        is_owner = owner and owner.telegram_id == message.from_user.id
        
        await add_auction_participant(
            session, flower_id, message.from_user.id,
            message.from_user.username, message.from_user.full_name
        )
        
        participants = await get_auction_participants(session, flower_id)
        
        remaining = ""
        if flower.auction_end_time:
            delta = flower.auction_end_time - datetime.utcnow()
            if delta.total_seconds() > 0:
                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                remaining = f"⏰ Qolgan vaqt: {hours} soat {minutes} daqiqa\n"
        
        from database.queries import get_auction_bids
        bids = await get_auction_bids(session, flower_id)
        
        bids_text = ""
        if bids:
            bids_text = "\n📊 <b>Stavkalar:</b>\n"
            for i, bid in enumerate(bids[:10], 1):
                name = bid.full_name or bid.username or "Nomalum"
                bids_text += f"{i}. {name}: {format_price(bid.amount)} som\n"
        
        caption = (
            f"🔨 <b>AUKSIYON</b>\n\n"
            f"🌸 <b>{flower.name}</b>\n\n"
            f"📝 {flower.description}\n\n"
            f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
            f"🔨 Joriy narx: {format_price(flower.current_bid)} som\n"
            f"📊 Stavkalar soni: {flower.bid_count}\n"
            f"📍 Manzil: {flower.location}\n\n"
            f"{remaining}"
            f"👥 Ishtirokchilar: {len(participants)}\n"
            f"{bids_text}\n"
            f"{'📢 Siz bu auksiyonning egasisiz!' if is_owner else '💬 Stavka qoyish uchun joriy narxdan yuqori narx kiriting'}"
        )
        
        if flower.media_type == "video":
            await message.answer_video(video=flower.photo_id, caption=caption,
                parse_mode="HTML", reply_markup=auction_participant_kb(flower_id, is_owner))
        else:
            await message.answer_photo(photo=flower.photo_id, caption=caption,
                parse_mode="HTML", reply_markup=auction_participant_kb(flower_id, is_owner))
        
        if not is_owner:
            for p in participants:
                if p.user_telegram_id != message.from_user.id:
                    try:
                        await bot.send_message(chat_id=p.user_telegram_id,
                            text=f"👤 Yangi ishtirokchi qoshildi!\n🌸 Auksiyon: {flower.name}\n👥 Jami: {len(participants)}")
                    except: pass


# ==================== PROFILE ====================

@router.message(F.text == "👤 Mening profilim")
async def my_profile(message: Message):
    async with async_session() as session:
        user, _ = await get_or_create_user(session, message.from_user.id,
            message.from_user.username, message.from_user.full_name)
        
        flowers = await get_user_flowers(session, user.id)
        published_count = len([f for f in flowers if f.status == "published"])
        
        await message.answer(
            f"👤 <b>Sizning profilingiz</b>\n\n"
            f"🆔 ID: <code>{message.from_user.id}</code>\n"
            f"👤 Ism: {message.from_user.full_name or 'Nomalum'}\n"
            f"💰 Balans: {format_price(user.balance)} som\n"
            f"🌸 Jami gullar: {len(flowers)}\n"
            f"📢 Nashr qilingan: {published_count}",
            parse_mode="HTML"
        )


# ==================== MY FLOWERS ====================

@router.message(F.text == "📋 Mening gullarim")
async def my_flowers(message: Message):
    async with async_session() as session:
        user, _ = await get_or_create_user(session, message.from_user.id,
            message.from_user.username, message.from_user.full_name)
        
        flowers = await get_user_flowers(session, user.id)
        
        if not flowers:
            await message.answer("🌸 Sizda hali gullar yoq.")
            return
        
        text = "📋 <b>Sizning gullaringiz:</b>\n\n"
        for flower in flowers:
            status_emoji = {"pending": "⏳", "published": "✅", "sold": "💰", "ended": "🏁"}.get(flower.status, "❓")
            auction_text = " (Auksiyon)" if flower.is_auction else ""
            text += f"{status_emoji} <b>{flower.name}</b>{auction_text}\n"
            text += f"   💰 Narx: {format_price(flower.price)} som\n"
            if flower.is_auction and flower.current_bid > 0:
                text += f"   🔨 Joriy stavka: {format_price(flower.current_bid)} som\n"
                text += f"   📊 Stavkalar: {flower.bid_count}\n"
            text += f"   📍 Holat: {flower.status}\n\n"
        
        await message.answer(text, parse_mode="HTML")


# ==================== ADD FLOWER ====================

@router.message(F.text == "🌸 Gul qoshish")
async def add_flower_start(message: Message, state: FSMContext):
    async with async_session() as session:
        regular_price = await get_setting(session, "regular_post_price")
        regular_price = int(regular_price) if regular_price else REGULAR_POST_PRICE
        
        auction_price = await get_setting(session, "auction_post_price")
        auction_price = int(auction_price) if auction_price else AUCTION_POST_PRICE
    
    await state.set_state(FlowerStates.waiting_type)
    await message.answer(
        f"🌸 <b>Gul qoshish</b>\n\n"
        f"Qanday turdagi e'lon qo'ymoqchisiz?\n\n"
        f"🛒 <b>Oddiy sotish</b> - belgilangan narxda sotish\n"
        f"   💰 Narxi: {format_price(regular_price)} som\n\n"
        f"🔨 <b>Auksiyon</b> - eng yuqori narx taklif qilgan oladi\n"
        f"   💰 Narxi: {format_price(auction_price)} som",
        parse_mode="HTML",
        reply_markup=flower_type_first_kb()
    )


@router.callback_query(FlowerStates.waiting_type, F.data.in_(["select_regular", "select_auction"]))
async def flower_type_selected(callback: CallbackQuery, state: FSMContext):
    is_auction = callback.data == "select_auction"
    await state.update_data(is_auction=is_auction, media_list=[], media_collected=False)
    await state.set_state(FlowerStates.waiting_media)
    
    type_text = "🔨 Auksiyon" if is_auction else "🛒 Oddiy sotish"
    
    await callback.message.edit_text(
        f"✅ Tanlandi: <b>{type_text}</b>\n\n"
        f"📸 Gulning rasmi hamda Rebloom yozuvi bilan video yuboring:\n\n"
        f"<i>Bir yoki bir nechta rasm/video yuborishingiz mumkin.\n"
        f"Barcha media fayllarni yuborib bo'lgach, biroz kuting.</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )
    await callback.answer()


async def process_media_collection(user_id: int, state: FSMContext, message: Message):
    await asyncio.sleep(1.5)
    
    data = await state.get_data()
    media_list = data.get('media_list', [])
    
    if media_list and not data.get('media_collected'):
        await state.update_data(media_collected=True)
        await state.set_state(FlowerStates.waiting_name)
        await message.answer("🌸 Gulning nomini yozing:", reply_markup=cancel_kb())
    
    if user_id in media_collection_tasks:
        del media_collection_tasks[user_id]


@router.message(FlowerStates.waiting_media, F.photo)
async def flower_photo_received(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get('media_collected'):
        return
    
    media_list = data.get('media_list', [])
    photo_id = message.photo[-1].file_id
    media_list.append({'type': 'photo', 'file_id': photo_id})
    await state.update_data(media_list=media_list)
    
    user_id = message.from_user.id
    if user_id in media_collection_tasks:
        media_collection_tasks[user_id].cancel()
    
    task = asyncio.create_task(process_media_collection(user_id, state, message))
    media_collection_tasks[user_id] = task


@router.message(FlowerStates.waiting_media, F.video)
async def flower_video_received(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get('media_collected'):
        return
    
    media_list = data.get('media_list', [])
    video_id = message.video.file_id
    media_list.append({'type': 'video', 'file_id': video_id})
    await state.update_data(media_list=media_list)
    
    user_id = message.from_user.id
    if user_id in media_collection_tasks:
        media_collection_tasks[user_id].cancel()
    
    task = asyncio.create_task(process_media_collection(user_id, state, message))
    media_collection_tasks[user_id] = task


@router.message(FlowerStates.waiting_media)
async def flower_media_invalid(message: Message):
    await message.answer("❌ Iltimos, rasm yoki video yuboring!")


@router.message(FlowerStates.waiting_name)
async def flower_name_received(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(FlowerStates.waiting_description)
    await message.answer("📝 Gul holati haqida qisqacha malumot yozing:", reply_markup=cancel_kb())


@router.message(FlowerStates.waiting_description)
async def flower_description_received(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(FlowerStates.waiting_price)
    
    data = await state.get_data()
    is_auction = data.get('is_auction', False)
    
    price_text = "💰 Auksiyon uchun boshlangich narxni yozing (som):" if is_auction else "💰 Gulning narxini yozing (som):"
    await message.answer(price_text, reply_markup=cancel_kb())


@router.message(FlowerStates.waiting_price)
async def flower_price_received(message: Message, state: FSMContext):
    try:
        price = int(message.text.replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
        await state.update_data(price=price)
        
        await state.set_state(FlowerStates.waiting_phone)
        await message.answer(
            "📞 Telefon raqamingizni kiriting yoki ulashish tugmasini bosing:",
            reply_markup=phone_share_kb()
        )
    except ValueError:
        await message.answer("❌ Iltimos, togri narx kiriting (faqat son)!")


@router.message(FlowerStates.waiting_phone, F.contact)
async def flower_phone_contact_received(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(FlowerStates.waiting_location)
    
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)
    
    await message.answer(
        "📍 Viloyatingizni tanlang:",
        reply_markup=regions_kb()
    )


@router.message(FlowerStates.waiting_phone, F.text)
async def flower_phone_text_received(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await cancel_text_action(message, state)
        return
    
    if message.text in ["🌸 Gul qoshish", "💰 Balans toldirish", "👤 Mening profilim", "📋 Mening gullarim", "⚙️ Admin panel"]:
        return
    
    await state.update_data(phone=message.text)
    await state.set_state(FlowerStates.waiting_location)
    
    await message.answer(
        "📍 Viloyatingizni tanlang:",
        reply_markup=regions_kb()
    )


@router.callback_query(FlowerStates.waiting_location, F.data.startswith("region_"))
async def flower_region_selected(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Region selected from keyboard"""
    region_map = {
        "region_toshkent_shahar": "Toshkent shahri",
        "region_toshkent_viloyat": "Toshkent viloyati",
        "region_andijon": "Andijon",
        "region_buxoro": "Buxoro",
        "region_fargona": "Farg'ona",
        "region_jizzax": "Jizzax",
        "region_xorazm": "Xorazm",
        "region_namangan": "Namangan",
        "region_navoiy": "Navoiy",
        "region_qashqadaryo": "Qashqadaryo",
        "region_samarqand": "Samarqand",
        "region_sirdaryo": "Sirdaryo",
        "region_surxondaryo": "Surxondaryo",
        "region_qoraqalpogiston": "Qoraqalpog'iston Respublikasi",
    }
    
    location = region_map.get(callback.data, "Noma'lum")
    await state.update_data(location=location)
    data = await state.get_data()
    
    is_auction = data.get('is_auction', False)
    
    if is_auction:
        await state.set_state(FlowerStates.waiting_auction_duration)
        await callback.message.edit_text(
            f"✅ Viloyat: <b>{location}</b>\n\n"
            f"🔨 <b>Auksiyon davomiyligini tanlang:</b>\n\nAuksiyon qancha vaqt davom etsin?",
            parse_mode="HTML",
            reply_markup=auction_duration_kb()
        )
    else:
        await callback.message.edit_text(f"✅ Viloyat: <b>{location}</b>\n\n⏳ E'lon joylanmoqda...", parse_mode="HTML")
        await try_publish_flower(callback.message, state, bot, is_auction=False, callback=callback)
    
    await callback.answer()


@router.message(FlowerStates.waiting_location)
async def flower_location_text_received(message: Message, state: FSMContext):
    """If user types location manually instead of selecting"""
    await message.answer("❌ Iltimos, viloyatni tugmalar orqali tanlang!", reply_markup=regions_kb())


@router.callback_query(FlowerStates.waiting_auction_duration, F.data.startswith("duration_"))
async def auction_duration_selected(callback: CallbackQuery, state: FSMContext, bot: Bot):
    minutes = int(callback.data.split("_")[1])
    await state.update_data(auction_minutes=minutes)
    await try_publish_flower(callback.message, state, bot, is_auction=True, callback=callback)


async def try_publish_flower(message: Message, state: FSMContext, bot: Bot, is_auction: bool, callback: CallbackQuery = None):
    """Try to publish flower - if not enough balance, redirect to payment"""
    user_id = callback.from_user.id if callback else message.from_user.id
    username = callback.from_user.username if callback else message.from_user.username
    full_name = callback.from_user.full_name if callback else message.from_user.full_name
    
    async with async_session() as session:
        if is_auction:
            required_price = await get_setting(session, "auction_post_price")
            required_price = int(required_price) if required_price else AUCTION_POST_PRICE
        else:
            required_price = await get_setting(session, "regular_post_price")
            required_price = int(required_price) if required_price else REGULAR_POST_PRICE
        
        user, _ = await get_or_create_user(session, user_id, username, full_name)
        card_number = await get_setting(session, "card_number") or CARD_NUMBER
        
        if user.balance < required_price:
            # Save flower data for later
            data = await state.get_data()
            pending_flowers[user_id] = {
                'data': data,
                'is_auction': is_auction,
                'required_price': required_price,
                'username': username,
                'full_name': full_name
            }
            
            shortage = required_price - user.balance
            
            await state.set_state(PaymentStates.waiting_screenshot_for_flower)
            
            text = (
                f"⚠️ <b>Hisobingizda mablag' yetarli emas!</b>\n\n"
                f"💰 Sizning balansingiz: {format_price(user.balance)} som\n"
                f"💰 Kerak: {format_price(required_price)} som\n"
                f"💰 Kamomad: {format_price(shortage)} som\n\n"
                f"💳 Karta raqami: <code>{card_number}</code>\n\n"
                f"📸 Tolov qiling va chek rasmini yuboring.\n"
                f"✅ Admin tasdiqlaganidan keyin e'loningiz avtomatik joylanadi."
            )
            
            if callback:
                await callback.message.edit_text(text, parse_mode="HTML", reply_markup=topup_for_flower_kb(shortage))
            else:
                await message.answer(text, parse_mode="HTML", reply_markup=topup_for_flower_kb(shortage))
            
            if callback:
                await callback.answer()
            return
        
        # Enough balance - publish immediately
        await publish_flower_final(message, state, bot, is_auction, callback)


async def publish_flower_final(message: Message, state: FSMContext, bot: Bot, is_auction: bool, callback: CallbackQuery = None, user_id_override: int = None):
    """Actually publish the flower to channel"""
    user_id = user_id_override or (callback.from_user.id if callback else message.from_user.id)
    
    # Get data from pending or state
    if user_id in pending_flowers:
        flower_data = pending_flowers[user_id]
        data = flower_data['data']
        is_auction = flower_data['is_auction']
        username = flower_data['username']
        full_name = flower_data['full_name']
        del pending_flowers[user_id]
    else:
        data = await state.get_data()
        username = callback.from_user.username if callback else message.from_user.username
        full_name = callback.from_user.full_name if callback else message.from_user.full_name
    
    async with async_session() as session:
        if is_auction:
            required_price = await get_setting(session, "auction_post_price")
            required_price = int(required_price) if required_price else AUCTION_POST_PRICE
        else:
            required_price = await get_setting(session, "regular_post_price")
            required_price = int(required_price) if required_price else REGULAR_POST_PRICE
        
        user, _ = await get_or_create_user(session, user_id, username, full_name)
        
        # Deduct balance
        await update_user_balance(session, user_id, -required_price)
        
        media_list = data.get('media_list', [])
        
        auction_end_time = None
        if is_auction:
            minutes = data.get('auction_minutes', 60)
            auction_end_time = datetime.utcnow() + timedelta(minutes=minutes)
        
        first_media = media_list[0] if media_list else {'type': 'photo', 'file_id': ''}
        
        flower = await create_flower(
            session,
            user_id=user.id,
            photo_id=first_media['file_id'],
            name=data['name'],
            description=data['description'],
            price=data['price'],
            is_auction=is_auction,
            phone_number=data['phone'],
            location=data['location'],
            auction_end_time=auction_end_time
        )
        
        flower.media_ids = json.dumps(media_list)
        flower.media_type = first_media['type']
        flower.seller_username = username
        flower.seller_telegram_id = user_id
        await session.commit()
        
        if is_auction:
            await add_auction_participant(session, flower.id, user_id, username, full_name)
        
        duration_text = ""
        if is_auction:
            minutes = data.get('auction_minutes', 60)
            if minutes < 60:
                duration_text = f"⏰ Davomiyligi: {minutes} daqiqa\n"
            else:
                hours = minutes // 60
                duration_text = f"⏰ Davomiyligi: {hours} soat\n"
        
        if is_auction:
            channel_text = (
                f"🔨 AUKSIYON\n\n"
                f"🌸 <b>{data['name']}</b>\n\n"
                f"📝 {data['description']}\n\n"
                f"💰 Boshlangich narx: {format_price(data['price'])} som\n"
                f"📍 Manzil: {data['location']}\n\n"
                f"{duration_text}"
                f"🔨 Joriy narx: {format_price(data['price'])} som\n"
                f"📊 Stavkalar soni: 0"
            )
        else:
            channel_text = (
                f"🛒 SOTILADI\n\n"
                f"🌸 <b>{data['name']}</b>\n\n"
                f"📝 {data['description']}\n\n"
                f"💰 Narx: {format_price(data['price'])} som\n"
                f"📍 Manzil: {data['location']}"
            )
        
        try:
            bot_info = await bot.get_me()
            
            if len(media_list) == 1:
                if first_media['type'] == 'video':
                    sent_message = await bot.send_video(
                        chat_id=CHANNEL_ID, video=first_media['file_id'],
                        caption=channel_text, parse_mode="HTML",
                        reply_markup=flower_channel_kb(flower.id, is_auction, username, bot_info.username)
                    )
                else:
                    sent_message = await bot.send_photo(
                        chat_id=CHANNEL_ID, photo=first_media['file_id'],
                        caption=channel_text, parse_mode="HTML",
                        reply_markup=flower_channel_kb(flower.id, is_auction, username, bot_info.username)
                    )
            else:
                media_group = []
                for i, media in enumerate(media_list):
                    if media['type'] == 'photo':
                        if i == 0:
                            media_group.append(InputMediaPhoto(media=media['file_id'], caption=channel_text, parse_mode="HTML"))
                        else:
                            media_group.append(InputMediaPhoto(media=media['file_id']))
                    else:
                        if i == 0:
                            media_group.append(InputMediaVideo(media=media['file_id'], caption=channel_text, parse_mode="HTML"))
                        else:
                            media_group.append(InputMediaVideo(media=media['file_id']))
                
                sent_messages = await bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
                sent_message = sent_messages[0]
                
                await bot.send_message(
                    chat_id=CHANNEL_ID, text="👆 Yuqoridagi e'lon uchun:",
                    reply_markup=flower_channel_kb(flower.id, is_auction, username, bot_info.username),
                    reply_to_message_id=sent_message.message_id
                )
            
            await update_flower_status(session, flower.id, "published", sent_message.message_id)
            
            # Refresh user balance
            user = await get_user(session, user_id)
            
            success_text = (
                f"✅ {'Auksiyoningiz' if is_auction else 'Gullingiz'} muvaffaqiyatli joylandi!\n\n"
                f"💰 {format_price(required_price)} som yechib olindi.\n"
                f"💰 Qolgan balans: {format_price(user.balance)} som"
            )
            
            if is_auction:
                success_text += f"\n\n{duration_text}📢 Ishtirokchilar habarlarini botda korasiz."
            
            await bot.send_message(
                chat_id=user_id,
                text=success_text,
                reply_markup=get_menu_kb(user_id, user)
            )
                
        except Exception as e:
            await update_user_balance(session, user_id, required_price)
            await bot.send_message(
                chat_id=user_id,
                text=f"❌ Xatolik yuz berdi: {str(e)}\n\nMablag' qaytarildi.",
                reply_markup=get_menu_kb(user_id)
            )
    
    await state.clear()


# ==================== PAYMENT FOR PENDING FLOWER ====================

@router.callback_query(F.data.startswith("topup_flower_"))
async def topup_flower_amount_selected(callback: CallbackQuery, state: FSMContext):
    amount = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        card_number = await get_setting(session, "card_number") or CARD_NUMBER
    
    await state.update_data(topup_amount=amount)
    await state.set_state(PaymentStates.waiting_screenshot_for_flower)
    
    await callback.message.edit_text(
        f"💰 Siz {format_price(amount)} som toldirmoqchisiz\n\n"
        f"💳 Karta raqami: <code>{card_number}</code>\n\n"
        f"📸 Tolovni amalga oshiring va chek rasmini yuboring:\n\n"
        f"✅ Admin tasdiqlaganidan keyin e'loningiz avtomatik joylanadi.",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(PaymentStates.waiting_screenshot_for_flower, F.photo)
async def payment_screenshot_for_flower_received(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    screenshot_id = message.photo[-1].file_id
    amount = data.get('topup_amount', 0)
    
    # If no amount selected, estimate from pending flower
    if not amount and message.from_user.id in pending_flowers:
        amount = pending_flowers[message.from_user.id]['required_price']
    
    async with async_session() as session:
        from database.queries import create_payment
        user, _ = await get_or_create_user(
            session, message.from_user.id,
            message.from_user.username, message.from_user.full_name
        )
        
        payment = await create_payment(session, user.id, amount, screenshot_id)
        
        # Mark payment as flower-related
        from database.models import Payment
        payment_obj = await session.get(Payment, payment.id)
        # We'll use a convention: store user_id in a way admin handler knows it's for flower
        
        from keyboards import payment_confirm_kb
        
        # Special keyboard for flower payment
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_flower_approve_{payment.id}_{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_flower_reject_{payment.id}_{message.from_user.id}")
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=screenshot_id,
                    caption=(
                        f"💳 <b>Yangi tolov (E'lon uchun)!</b>\n\n"
                        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
                        f"🆔 ID: <code>{message.from_user.id}</code>\n"
                        f"💰 Summa: {format_price(amount)} som\n\n"
                        f"🌸 <b>Foydalanuvchi e'lon joylash uchun tolov qilmoqda</b>\n\n"
                        f"Tolovni tasdiqlaysizmi?"
                    ),
                    parse_mode="HTML",
                    reply_markup=builder.as_markup()
                )
            except: pass
    
    await message.answer(
        "✅ Tolov cheki yuborildi!\n\n"
        "⏳ Admin tekshirib tasdiqlaganidan keyin e'loningiz avtomatik joylanadi.\n"
        "Iltimos kuting...",
        reply_markup=get_menu_kb(message.from_user.id, user)
    )
    await state.clear()


@router.callback_query(F.data == "cancel_flower_payment")
async def cancel_flower_payment(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    # Remove pending flower data
    if user_id in pending_flowers:
        del pending_flowers[user_id]
    
    await state.clear()
    
    async with async_session() as session:
        user = await get_user(session, callback.from_user.id)
    
    await callback.message.delete()
    await callback.message.answer(
        "❌ E'lon bekor qilindi.\n\nQaytadan urinib ko'rishingiz mumkin.",
        reply_markup=get_menu_kb(callback.from_user.id, user)
    )
    await callback.answer()


# ==================== TOP UP BALANCE (Regular) ====================

@router.message(F.text == "💰 Balans toldirish")
async def topup_balance_start(message: Message, state: FSMContext):
    async with async_session() as session:
        card_number = await get_setting(session, "card_number") or CARD_NUMBER
        user, _ = await get_or_create_user(session, message.from_user.id,
            message.from_user.username, message.from_user.full_name)
    
    await message.answer(
        f"💰 <b>Balans toldirish</b>\n\n"
        f"💳 Karta raqami: <code>{card_number}</code>\n"
        f"💰 Joriy balans: {format_price(user.balance)} som\n\n"
        f"Qancha mablag' toldirmoqchisiz?",
        parse_mode="HTML",
        reply_markup=topup_balance_kb()
    )


@router.callback_query(F.data.startswith("topup_") & ~F.data.startswith("topup_flower_"))
async def topup_amount_selected(callback: CallbackQuery, state: FSMContext):
    amount = int(callback.data.split("_")[1])
    
    async with async_session() as session:
        card_number = await get_setting(session, "card_number") or CARD_NUMBER
    
    await state.update_data(topup_amount=amount)
    await state.set_state(PaymentStates.waiting_screenshot)
    
    await callback.message.edit_text(
        f"💰 Siz {format_price(amount)} som toldirmoqchisiz\n\n"
        f"💳 Karta raqami: <code>{card_number}</code>\n\n"
        f"📸 Tolovni amalga oshiring va chek rasmini yuboring:",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(PaymentStates.waiting_screenshot, F.photo)
async def payment_screenshot_received(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    screenshot_id = message.photo[-1].file_id
    amount = data['topup_amount']
    
    async with async_session() as session:
        from database.queries import create_payment
        user, _ = await get_or_create_user(session, message.from_user.id,
            message.from_user.username, message.from_user.full_name)
        
        payment = await create_payment(session, user.id, amount, screenshot_id)
        
        from keyboards import payment_confirm_kb
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=screenshot_id,
                    caption=(
                        f"💳 <b>Yangi tolov!</b>\n\n"
                        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
                        f"🆔 ID: <code>{message.from_user.id}</code>\n"
                        f"💰 Summa: {format_price(amount)} som\n\n"
                        f"Tolovni tasdiqlaysizmi?"
                    ),
                    parse_mode="HTML",
                    reply_markup=payment_confirm_kb(payment.id, message.from_user.id)
                )
            except: pass
    
    await message.answer(
        "✅ Tolov cheki yuborildi!\n\n⏳ Admin tekshirib, balans qoshadi. Iltimos kuting.",
        reply_markup=get_menu_kb(message.from_user.id, user)
    )
    await state.clear()


@router.message(PaymentStates.waiting_screenshot)
async def payment_screenshot_invalid(message: Message):
    await message.answer("❌ Iltimos, chek rasmini yuboring!")


# ==================== CANCEL ====================

@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    user_id = callback.from_user.id
    if user_id in media_collection_tasks:
        media_collection_tasks[user_id].cancel()
        del media_collection_tasks[user_id]
    
    async with async_session() as session:
        user = await get_user(session, callback.from_user.id)
    
    await callback.message.delete()
    await callback.message.answer("❌ Amal bekor qilindi.", reply_markup=get_menu_kb(callback.from_user.id, user))
    await callback.answer()


async def cancel_text_action(message: Message, state: FSMContext):
    await state.clear()
    
    user_id = message.from_user.id
    if user_id in media_collection_tasks:
        media_collection_tasks[user_id].cancel()
        del media_collection_tasks[user_id]
    
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)
    
    await message.answer("❌ Amal bekor qilindi.", reply_markup=get_menu_kb(message.from_user.id, user))


# Export pending_flowers for admin handler
def get_pending_flower(user_id: int):
    return pending_flowers.get(user_id)

def has_pending_flower(user_id: int):
    return user_id in pending_flowers
