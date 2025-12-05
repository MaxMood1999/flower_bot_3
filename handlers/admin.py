from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import async_session
from database.queries import (
    get_or_create_user, get_user, update_user_balance, set_user_balance,
    get_payment, update_payment_status, get_pending_payments,
    get_setting, set_setting, get_all_users, get_income_stats
)
from keyboards import (
    admin_panel_kb, admin_menu_kb, main_menu_kb, cancel_kb, back_kb
)
from states import AdminStates
from config import ADMIN_IDS, REGULAR_POST_PRICE, AUCTION_POST_PRICE

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def format_price(amount: int) -> str:
    """Format price with thousands separator"""
    return f"{amount:,}".replace(",", " ")


# ==================== ADMIN PANEL ====================

@router.message(F.text == "⚙️ Admin panel")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda ruxsat yoq!")
        return
    
    async with async_session() as session:
        regular_price = await get_setting(session, "regular_post_price")
        regular_price = int(regular_price) if regular_price else REGULAR_POST_PRICE
        
        auction_price = await get_setting(session, "auction_post_price")
        auction_price = int(auction_price) if auction_price else AUCTION_POST_PRICE
        
        card_number = await get_setting(session, "card_number") or "Belgilanmagan"
    
    await message.answer(
        f"⚙️ <b>Admin panel</b>\n\n"
        f"📊 Joriy sozlamalar:\n"
        f"• 💳 Karta: {card_number}\n"
        f"• 🛒 Oddiy e'lon: {format_price(regular_price)} som\n"
        f"• 🔨 Auksiyon: {format_price(auction_price)} som\n\n"
        f"Quyidagi amallardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=admin_panel_kb()
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "🏠 Bosh menyu",
        reply_markup=admin_menu_kb() if is_admin(callback.from_user.id) else main_menu_kb()
    )
    await callback.answer()


# ==================== CHANGE CARD NUMBER ====================

@router.callback_query(F.data == "admin_change_card")
async def admin_change_card(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_card_number)
    await callback.message.edit_text(
        "💳 Yangi karta raqamini kiriting:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(AdminStates.waiting_card_number)
async def admin_card_number_received(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    card_number = message.text.strip()
    
    async with async_session() as session:
        await set_setting(session, "card_number", card_number)
    
    await message.answer(
        f"✅ Karta raqami ozgartirildi!\n\n"
        f"💳 Yangi karta: <code>{card_number}</code>",
        parse_mode="HTML",
        reply_markup=admin_menu_kb()
    )
    await state.clear()


# ==================== CHANGE REGULAR POST PRICE ====================

@router.callback_query(F.data == "admin_change_regular_price")
async def admin_change_regular_price(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_diamond_price)  # reusing state
    await state.update_data(price_type="regular")
    await callback.message.edit_text(
        "🛒 Oddiy e'lon uchun yangi narxni kiriting (som):",
        reply_markup=cancel_kb()
    )
    await callback.answer()


# ==================== CHANGE AUCTION POST PRICE ====================

@router.callback_query(F.data == "admin_change_auction_price")
async def admin_change_auction_price(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_diamond_price)  # reusing state
    await state.update_data(price_type="auction")
    await callback.message.edit_text(
        "🔨 Auksiyon e'loni uchun yangi narxni kiriting (som):",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(AdminStates.waiting_diamond_price)
async def admin_price_received(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        price = int(message.text.replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
        
        data = await state.get_data()
        price_type = data.get("price_type", "regular")
        
        async with async_session() as session:
            if price_type == "auction":
                await set_setting(session, "auction_post_price", str(price))
                type_text = "Auksiyon e'loni"
            else:
                await set_setting(session, "regular_post_price", str(price))
                type_text = "Oddiy e'lon"
        
        await message.answer(
            f"✅ {type_text} narxi ozgartirildi!\n\n"
            f"💰 Yangi narx: {format_price(price)} som",
            reply_markup=admin_menu_kb()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, togri narx kiriting (faqat son)!")


# ==================== ADD BALANCE TO USER ====================

@router.callback_query(F.data == "admin_add_balance")
async def admin_add_balance(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_user_id_for_diamonds)
    await callback.message.edit_text(
        "👤 Foydalanuvchi Telegram ID sini kiriting:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(AdminStates.waiting_user_id_for_diamonds)
async def admin_user_id_received(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.strip())
        
        async with async_session() as session:
            user = await get_user(session, user_id)
            if not user:
                await message.answer(
                    "❌ Bunday foydalanuvchi topilmadi!",
                    reply_markup=cancel_kb()
                )
                return
        
        await state.update_data(target_user_id=user_id)
        await state.set_state(AdminStates.waiting_diamond_amount)
        await message.answer(
            f"👤 Foydalanuvchi topildi!\n"
            f"💰 Joriy balans: {format_price(user.balance)} som\n\n"
            f"Qancha mablag' qoshish kerak (som)?",
            reply_markup=cancel_kb()
        )
    except ValueError:
        await message.answer("❌ Iltimos, togri ID kiriting (faqat son)!")


@router.message(AdminStates.waiting_diamond_amount)
async def admin_balance_amount_received(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    
    try:
        amount = int(message.text.strip().replace(" ", "").replace(",", ""))
        data = await state.get_data()
        target_user_id = data['target_user_id']
        
        async with async_session() as session:
            await update_user_balance(session, target_user_id, amount)
            user = await get_user(session, target_user_id)
        
        await message.answer(
            f"✅ Balans qoshildi!\n\n"
            f"👤 Foydalanuvchi ID: {target_user_id}\n"
            f"💰 Qoshilgan: {format_price(amount)} som\n"
            f"💰 Yangi balans: {format_price(user.balance)} som",
            reply_markup=admin_menu_kb()
        )
        
        # Notify user
        try:
            await bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 Sizga {format_price(amount)} som qoshildi!\n\n"
                     f"💰 Yangi balans: {format_price(user.balance)} som"
            )
        except Exception:
            pass
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, togri son kiriting!")


# ==================== STATISTICS ====================

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    async with async_session() as session:
        users = await get_all_users(session)
        total_users = len(users)
        total_balance = sum(u.balance for u in users)
    
    await callback.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: {total_users}\n"
        f"💰 Jami balans: {format_price(total_balance)} som",
        parse_mode="HTML",
        reply_markup=back_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "back")
async def back_to_admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    async with async_session() as session:
        regular_price = await get_setting(session, "regular_post_price")
        regular_price = int(regular_price) if regular_price else REGULAR_POST_PRICE
        
        auction_price = await get_setting(session, "auction_post_price")
        auction_price = int(auction_price) if auction_price else AUCTION_POST_PRICE
        
        card_number = await get_setting(session, "card_number") or "Belgilanmagan"
    
    await callback.message.edit_text(
        f"⚙️ <b>Admin panel</b>\n\n"
        f"📊 Joriy sozlamalar:\n"
        f"• 💳 Karta: {card_number}\n"
        f"• 🛒 Oddiy e'lon: {format_price(regular_price)} som\n"
        f"• 🔨 Auksiyon: {format_price(auction_price)} som\n\n"
        f"Quyidagi amallardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()

# ==================== INCOME STATISTICS ====================

@router.callback_query(F.data == "admin_income_stats")
async def admin_income_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    async with async_session() as session:
        stats = await get_income_stats(session)
    
    from datetime import datetime
    today = datetime.utcnow().strftime("%d.%m.%Y")
    
    text = (
        f"💵 <b>Daromad hisoboti</b>\n"
        f"📅 {today}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>Kunlik:</b>\n"
        f"   💰 {format_price(stats['daily']['amount'])} som\n"
        f"   📝 {stats['daily']['count']} ta tolov\n\n"
        f"📊 <b>Haftalik:</b>\n"
        f"   💰 {format_price(stats['weekly']['amount'])} som\n"
        f"   📝 {stats['weekly']['count']} ta tolov\n\n"
        f"📊 <b>Oylik:</b>\n"
        f"   💰 {format_price(stats['monthly']['amount'])} som\n"
        f"   📝 {stats['monthly']['count']} ta tolov\n\n"
        f"📊 <b>Yillik:</b>\n"
        f"   💰 {format_price(stats['yearly']['amount'])} som\n"
        f"   📝 {stats['yearly']['count']} ta tolov\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 <b>Jami daromad:</b> {format_price(stats['total'])} som"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_kb()
    )
    await callback.answer()


# ==================== BROADCAST ====================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_broadcast_message)
    await callback.message.edit_text(
        "📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_message)
async def admin_broadcast_message_received(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    
    broadcast_text = message.text
    
    async with async_session() as session:
        users = await get_all_users(session)
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=f"📢 <b>Xabar:</b>\n\n{broadcast_text}",
                parse_mode="HTML"
            )
            success_count += 1
        except Exception:
            fail_count += 1
    
    await message.answer(
        f"✅ Xabar yuborildi!\n\n"
        f"✅ Muvaffaqiyatli: {success_count}\n"
        f"❌ Xato: {fail_count}",
        reply_markup=admin_menu_kb()
    )
    await state.clear()


# ==================== PENDING PAYMENTS ====================

@router.callback_query(F.data == "admin_pending_payments")
async def admin_pending_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    async with async_session() as session:
        payments = await get_pending_payments(session)
    
    if not payments:
        await callback.message.edit_text(
            "📋 Kutilayotgan tolovlar yoq.",
            reply_markup=back_kb()
        )
    else:
        await callback.message.edit_text(
            f"📋 Kutilayotgan tolovlar soni: {len(payments)}\n\n"
            f"Har bir tolov alohida xabar sifatida yuborilgan.",
            reply_markup=back_kb()
        )
    await callback.answer()


# ==================== PAYMENT APPROVAL ====================

@router.callback_query(F.data.startswith("pay_approve_"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    parts = callback.data.split("_")
    payment_id = int(parts[2])
    user_telegram_id = int(parts[3])
    
    async with async_session() as session:
        payment = await get_payment(session, payment_id)
        if not payment:
            await callback.answer("❌ Tolov topilmadi!", show_alert=True)
            return
        
        if payment.status != "pending":
            await callback.answer("❌ Bu tolov allaqachon korib chiqilgan!", show_alert=True)
            return
        
        # Update payment status
        await update_payment_status(session, payment_id, "approved")
        
        # Add balance to user
        await update_user_balance(session, user_telegram_id, payment.amount)
        
        user = await get_user(session, user_telegram_id)
    
    # Edit admin message
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>TASDIQLANGAN</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    
    # Notify user
    try:
        await bot.send_message(
            chat_id=user_telegram_id,
            text=f"✅ Tolovingiz tasdiqlandi!\n\n"
                 f"💰 Qoshilgan: {format_price(payment.amount)} som\n"
                 f"💰 Yangi balans: {format_price(user.balance)} som"
        )
    except Exception:
        pass
    
    await callback.answer("✅ Tolov tasdiqlandi!")


@router.callback_query(F.data.startswith("pay_reject_"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    parts = callback.data.split("_")
    payment_id = int(parts[2])
    user_telegram_id = int(parts[3])
    
    async with async_session() as session:
        payment = await get_payment(session, payment_id)
        if not payment:
            await callback.answer("❌ Tolov topilmadi!", show_alert=True)
            return
        
        if payment.status != "pending":
            await callback.answer("❌ Bu tolov allaqachon korib chiqilgan!", show_alert=True)
            return
        
        # Update payment status
        await update_payment_status(session, payment_id, "rejected")
    
    # Edit admin message
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>RAD ETILGAN</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    
    # Notify user
    try:
        await bot.send_message(
            chat_id=user_telegram_id,
            text=f"❌ Tolovingiz rad etildi.\n\n"
                 f"Iltimos, qaytadan urinib koring yoki admin bilan boganing."
        )
    except Exception:
        pass
    
    await callback.answer("❌ Tolov rad etildi!")


# ==================== FLOWER PAYMENT APPROVAL ====================

@router.callback_query(F.data.startswith("pay_flower_approve_"))
async def approve_flower_payment(callback: CallbackQuery, bot: Bot):
    """Approve payment for flower and auto-publish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    parts = callback.data.split("_")
    payment_id = int(parts[3])
    user_telegram_id = int(parts[4])
    
    async with async_session() as session:
        payment = await get_payment(session, payment_id)
        if not payment:
            await callback.answer("❌ Tolov topilmadi!", show_alert=True)
            return
        
        if payment.status != "pending":
            await callback.answer("❌ Bu tolov allaqachon korib chiqilgan!", show_alert=True)
            return
        
        # Update payment status
        await update_payment_status(session, payment_id, "approved")
        
        # Add balance to user
        await update_user_balance(session, user_telegram_id, payment.amount)
        
        user = await get_user(session, user_telegram_id)
    
    # Edit admin message
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>TASDIQLANGAN</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    
    # Check if user has pending flower
    from handlers.user import has_pending_flower, publish_flower_final, pending_flowers
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.memory import MemoryStorage
    
    if has_pending_flower(user_telegram_id):
        # Auto-publish the flower
        try:
            # Create a dummy state context
            class DummyState:
                async def get_data(self):
                    return pending_flowers.get(user_telegram_id, {}).get('data', {})
                async def clear(self):
                    pass
                async def update_data(self, **kwargs):
                    pass
            
            dummy_state = DummyState()
            flower_data = pending_flowers.get(user_telegram_id, {})
            
            await publish_flower_final(
                message=None,
                state=dummy_state,
                bot=bot,
                is_auction=flower_data.get('is_auction', False),
                callback=None,
                user_id_override=user_telegram_id
            )
            
            await callback.answer("✅ Tolov tasdiqlandi va e'lon joylandi!")
        except Exception as e:
            # If publish fails, just notify user about balance
            try:
                await bot.send_message(
                    chat_id=user_telegram_id,
                    text=f"✅ Tolovingiz tasdiqlandi!\n\n"
                         f"💰 Qoshilgan: {format_price(payment.amount)} som\n"
                         f"💰 Yangi balans: {format_price(user.balance)} som\n\n"
                         f"⚠️ E'lonni joylashda xatolik: {str(e)}\n"
                         f"Iltimos, qaytadan urinib ko'ring."
                )
            except: pass
            await callback.answer("✅ Tolov tasdiqlandi!")
    else:
        # No pending flower, just notify about balance
        try:
            await bot.send_message(
                chat_id=user_telegram_id,
                text=f"✅ Tolovingiz tasdiqlandi!\n\n"
                     f"💰 Qoshilgan: {format_price(payment.amount)} som\n"
                     f"💰 Yangi balans: {format_price(user.balance)} som"
            )
        except: pass
        await callback.answer("✅ Tolov tasdiqlandi!")


@router.callback_query(F.data.startswith("pay_flower_reject_"))
async def reject_flower_payment(callback: CallbackQuery, bot: Bot):
    """Reject payment for flower"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Sizda ruxsat yoq!", show_alert=True)
        return
    
    parts = callback.data.split("_")
    payment_id = int(parts[3])
    user_telegram_id = int(parts[4])
    
    async with async_session() as session:
        payment = await get_payment(session, payment_id)
        if not payment:
            await callback.answer("❌ Tolov topilmadi!", show_alert=True)
            return
        
        if payment.status != "pending":
            await callback.answer("❌ Bu tolov allaqachon korib chiqilgan!", show_alert=True)
            return
        
        # Update payment status
        await update_payment_status(session, payment_id, "rejected")
    
    # Remove pending flower data
    from handlers.user import pending_flowers
    if user_telegram_id in pending_flowers:
        del pending_flowers[user_telegram_id]
    
    # Edit admin message
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>RAD ETILGAN</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    
    # Notify user
    try:
        await bot.send_message(
            chat_id=user_telegram_id,
            text=f"❌ Tolovingiz rad etildi.\n\n"
                 f"E'loningiz joylanmadi. Iltimos, qaytadan urinib ko'ring."
        )
    except: pass
    
    await callback.answer("❌ Tolov rad etildi!")
