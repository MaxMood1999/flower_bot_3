from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime

from database import async_session
from database.queries import (
    get_or_create_user, get_user, get_flower, update_flower_bid,
    add_auction_participant, get_auction_participants, remove_auction_participant,
    get_user_active_auction, add_auction_bid, get_auction_bids, update_flower_status
)
from database.models import User, AuctionBid, Flower
from sqlalchemy import select
from keyboards import cancel_kb, main_menu_kb, admin_menu_kb, auction_participant_kb, flower_channel_kb, auction_sell_kb
from config import CHANNEL_ID, ADMIN_IDS

router = Router()


def format_price(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def get_menu_kb(user_id: int, user=None):
    is_admin = user_id in ADMIN_IDS or (user and user.is_admin)
    return admin_menu_kb() if is_admin else main_menu_kb()


async def update_channel_auction_message(bot: Bot, flower, session):
    """Update the channel message with current bid info"""
    try:
        participants = await get_auction_participants(session, flower.id)
        
        remaining = ""
        if flower.auction_end_time:
            delta = flower.auction_end_time - datetime.utcnow()
            if delta.total_seconds() > 0:
                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                remaining = f"⏰ Qolgan vaqt: {hours} soat {minutes} daqiqa\n"
        
        channel_text = (
            f"🔨 AUKSIYON\n\n"
            f"🌸 <b>{flower.name}</b>\n\n"
            f"📝 {flower.description}\n\n"
            f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
            f"📍 Manzil: {flower.location}\n\n"
            f"{remaining}"
            f"🔨 <b>Joriy narx: {format_price(flower.current_bid)} som</b>\n"
            f"📊 <b>Stavkalar soni: {flower.bid_count}</b>\n"
            f"👥 Ishtirokchilar: {len(participants)}"
        )
        
        bot_info = await bot.get_me()
        await bot.edit_message_caption(
            chat_id=CHANNEL_ID,
            message_id=flower.message_id,
            caption=channel_text,
            parse_mode="HTML",
            reply_markup=flower_channel_kb(flower.id, True, flower.seller_username, bot_info.username)
        )
    except Exception as e:
        print(f"Error updating channel message: {e}")


@router.message(F.text.regexp(r'^\d[\d\s,]*$'))
async def process_auction_bid(message: Message, bot: Bot):
    """Process bid from auction participant (only numbers)"""
    async with async_session() as session:
        # Check if user is in any active auction
        participant = await get_user_active_auction(session, message.from_user.id)
        
        if not participant:
            return  # Not in any auction, ignore
        
        flower = await get_flower(session, participant.flower_id)
        
        if not flower or flower.status != "published":
            await message.answer("❌ Bu auksiyon tugagan!", reply_markup=get_menu_kb(message.from_user.id))
            return
        
        # Check if auction time has ended
        if flower.auction_end_time and datetime.utcnow() > flower.auction_end_time:
            await message.answer("❌ Auksiyon vaqti tugagan!", reply_markup=get_menu_kb(message.from_user.id))
            return
        
        # Get owner
        result = await session.execute(select(User).where(User.id == flower.user_id))
        owner = result.scalar_one_or_none()
        
        is_owner = owner and owner.telegram_id == message.from_user.id
        
        # Owner can't bid
        if is_owner:
            await message.answer("❌ Siz bu auksiyonning egasisiz, stavka qoya olmaysiz!")
            return
        
        # Parse bid amount
        try:
            bid = int(message.text.replace(" ", "").replace(",", ""))
        except ValueError:
            return
        
        current_bid = flower.current_bid or flower.price
        
        # Check bid is higher than current
        if bid <= current_bid:
            await message.answer(
                f"❌ Stavka joriy narxdan ({format_price(current_bid)} som) yuqori bolishi kerak!"
            )
            return
        
        # Save bid
        auction_bid = await add_auction_bid(
            session, 
            flower.id, 
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
            bid
        )
        
        # Update flower current bid and bid count
        flower.current_bid = bid
        flower.highest_bidder_id = message.from_user.id
        flower.bid_count = (flower.bid_count or 0) + 1
        await session.commit()
        
        # Confirm to bidder
        await message.answer(
            f"✅ Stavkangiz qabul qilindi: {format_price(bid)} som\n\n"
            f"📊 Siz {flower.bid_count}-chi stavka qo'ydingiz"
        )
        
        # Refresh flower
        flower = await get_flower(session, flower.id)
        
        user_name = message.from_user.full_name or message.from_user.username or "Nomalum"
        user_link = f"@{message.from_user.username}" if message.from_user.username else user_name
        
        # Notify owner with SELL button
        if owner:
            try:
                await bot.send_message(
                    chat_id=owner.telegram_id,
                    text=(
                        f"💰 <b>Yangi stavka!</b>\n\n"
                        f"🌸 Auksiyon: {flower.name}\n"
                        f"👤 Ishtirokchi: {user_name}\n"
                        f"📱 Telegram: {user_link}\n"
                        f"💵 Stavka: {format_price(bid)} som\n"
                        f"📊 Stavkalar soni: {flower.bid_count}\n\n"
                        f"Shu narxga sotmoqchimisiz?"
                    ),
                    parse_mode="HTML",
                    reply_markup=auction_sell_kb(flower.id, auction_bid.id, message.from_user.id)
                )
            except Exception:
                pass
        
        # Broadcast to other participants
        participants = await get_auction_participants(session, flower.id)
        for p in participants:
            if p.user_telegram_id == message.from_user.id:
                continue
            if owner and p.user_telegram_id == owner.telegram_id:
                continue  # Owner already notified with sell button
            try:
                await bot.send_message(
                    chat_id=p.user_telegram_id,
                    text=(
                        f"💰 <b>Yangi stavka!</b>\n\n"
                        f"🌸 {flower.name}\n"
                        f"👤 {user_name}: {format_price(bid)} som\n"
                        f"📊 Stavkalar soni: {flower.bid_count}\n\n"
                        f"🔨 Joriy narx: {format_price(flower.current_bid)} som"
                    ),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        
        # Update channel message
        await update_channel_auction_message(bot, flower, session)


@router.callback_query(F.data.startswith("sell_"))
async def sell_to_bidder(callback: CallbackQuery, bot: Bot):
    """Owner sells to specific bidder"""
    parts = callback.data.split("_")
    flower_id = int(parts[1])
    bid_id = int(parts[2])
    bidder_telegram_id = int(parts[3])
    
    async with async_session() as session:
        flower = await get_flower(session, flower_id)
        
        if not flower:
            await callback.answer("❌ Auksiyon topilmadi!", show_alert=True)
            return
        
        # Verify owner
        result = await session.execute(select(User).where(User.id == flower.user_id))
        owner = result.scalar_one_or_none()
        
        if not owner or owner.telegram_id != callback.from_user.id:
            await callback.answer("❌ Siz bu auksiyonning egasi emassiz!", show_alert=True)
            return
        
        if flower.status != "published":
            await callback.answer("❌ Bu auksiyon allaqachon tugagan!", show_alert=True)
            return
        
        # Get the bid
        result = await session.execute(select(AuctionBid).where(AuctionBid.id == bid_id))
        bid = result.scalar_one_or_none()
        
        if not bid:
            await callback.answer("❌ Stavka topilmadi!", show_alert=True)
            return
        
        # Get winner info
        winner_name = bid.full_name or bid.username or "Nomalum"
        winner_link = f"@{bid.username}" if bid.username else winner_name
        
        # Update flower status
        await update_flower_status(session, flower_id, "sold")
        
        # Get all bids to find position
        all_bids = await get_auction_bids(session, flower_id)
        position = 1
        for i, b in enumerate(all_bids, 1):
            if b.id == bid_id:
                position = i
                break
        
        # Notify winner
        try:
            await bot.send_message(
                chat_id=bidder_telegram_id,
                text=(
                    f"🎉 <b>Tabriklaymiz! Siz yutdingiz!</b>\n\n"
                    f"🌸 {flower.name}\n"
                    f"💰 Sizning stavkangiz: {format_price(bid.amount)} som\n\n"
                    f"📞 Sotuvchi telefoni: {flower.phone_number}\n"
                    f"📍 Manzil: {flower.location}\n\n"
                    f"Sotuvchi bilan bog'laning!"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass
        
        # Notify all participants
        participants = await get_auction_participants(session, flower_id)
        for p in participants:
            if p.user_telegram_id in [bidder_telegram_id, callback.from_user.id]:
                continue
            try:
                await bot.send_message(
                    chat_id=p.user_telegram_id,
                    text=(
                        f"🏁 <b>AUKSIYON TUGADI!</b>\n\n"
                        f"🌸 {flower.name}\n"
                        f"💰 Yakuniy narx: {format_price(bid.amount)} som"
                    ),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        
        # Update channel - reply to original message (WITHOUT buyer info)
        try:
            sold_text = (
                f"✅ <b>SOTILDI!</b>\n\n"
                f"🌸 {flower.name}\n\n"
                f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
                f"📊 Stavkalar soni: {flower.bid_count}\n"
                f"💵 Yakuniy narx: {format_price(bid.amount)} som"
            )
            
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=sold_text,
                parse_mode="HTML",
                reply_to_message_id=flower.message_id
            )
            
            # Also update original message caption (WITHOUT buyer info)
            channel_text = (
                f"🏁 AUKSIYON TUGADI - SOTILDI\n\n"
                f"🌸 <b>{flower.name}</b>\n\n"
                f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
                f"📊 Stavkalar soni: {flower.bid_count}\n"
                f"💵 Yakuniy narx: {format_price(bid.amount)} som"
            )
            
            await bot.edit_message_caption(
                chat_id=CHANNEL_ID,
                message_id=flower.message_id,
                caption=channel_text,
                parse_mode="HTML",
                reply_markup=None
            )
        except Exception as e:
            print(f"Error updating channel: {e}")
        
        # Update callback message
        await callback.message.edit_text(
            f"✅ Sotildi!\n\n"
            f"🌸 {flower.name}\n"
            f"👤 Xaridor: {winner_name} ({winner_link})\n"
            f"💰 Narx: {format_price(bid.amount)} som",
            reply_markup=None
        )
        
    await callback.answer("✅ Muvaffaqiyatli sotildi!")


@router.callback_query(F.data.startswith("leave_auction_"))
async def leave_auction(callback: CallbackQuery, bot: Bot):
    """User leaving auction"""
    flower_id = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        flower = await get_flower(session, flower_id)
        
        if not flower:
            await callback.answer("❌ Auksiyon topilmadi!", show_alert=True)
            return
        
        # Remove participant
        await remove_auction_participant(session, flower_id, callback.from_user.id)
        
        participants = await get_auction_participants(session, flower_id)
        
        # Notify others
        user_name = callback.from_user.full_name or callback.from_user.username or "Nomalum"
        for p in participants:
            if p.user_telegram_id != callback.from_user.id:
                try:
                    await bot.send_message(
                        chat_id=p.user_telegram_id,
                        text=f"🚪 {user_name} auksiyondan chiqdi.\n👥 Qolgan ishtirokchilar: {len(participants)}"
                    )
                except Exception:
                    pass
        
        user = await get_user(session, callback.from_user.id)
    
    await callback.message.delete()
    await callback.message.answer(
        "✅ Siz auksiyondan chiqdingiz.",
        reply_markup=get_menu_kb(callback.from_user.id, user)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("end_auction_"))
async def end_auction(callback: CallbackQuery, bot: Bot):
    """Owner ending auction without selling"""
    flower_id = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        flower = await get_flower(session, flower_id)
        
        if not flower:
            await callback.answer("❌ Auksiyon topilmadi!", show_alert=True)
            return
        
        # Verify owner
        result = await session.execute(select(User).where(User.id == flower.user_id))
        owner = result.scalar_one_or_none()
        
        if not owner or owner.telegram_id != callback.from_user.id:
            await callback.answer("❌ Siz bu auksiyonning egasi emassiz!", show_alert=True)
            return
        
        # Update flower status
        await update_flower_status(session, flower_id, "ended")
        
        # Notify all participants
        participants = await get_auction_participants(session, flower_id)
        for p in participants:
            if p.user_telegram_id == callback.from_user.id:
                continue
            try:
                await bot.send_message(
                    chat_id=p.user_telegram_id,
                    text=(
                        f"🏁 <b>AUKSIYON TUGADI!</b>\n\n"
                        f"🌸 {flower.name}\n\n"
                        f"Sotuvchi auksiyonni yopdi."
                    ),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        
        # Update channel message
        try:
            channel_text = (
                f"🏁 AUKSIYON YOPILDI\n\n"
                f"🌸 <b>{flower.name}</b>\n\n"
                f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
                f"📊 Stavkalar soni: {flower.bid_count}\n"
                f"💵 Oxirgi narx: {format_price(flower.current_bid)} som\n\n"
                f"❌ Sotuvchi tomonidan yopildi."
            )
            
            await bot.edit_message_caption(
                chat_id=CHANNEL_ID,
                message_id=flower.message_id,
                caption=channel_text,
                parse_mode="HTML",
                reply_markup=None
            )
        except Exception:
            pass
        
        user = await get_user(session, callback.from_user.id)
    
    await callback.message.delete()
    await callback.message.answer(
        "✅ Auksiyon tugatildi!",
        reply_markup=get_menu_kb(callback.from_user.id, user)
    )
    await callback.answer()


# Handle text messages in auction (chat functionality removed - only bids allowed)
@router.message(F.text)
async def check_auction_message(message: Message):
    """Check if user in auction and guide them"""
    async with async_session() as session:
        participant = await get_user_active_auction(session, message.from_user.id)
        
        if participant:
            # User is in auction but sent non-numeric message
            flower = await get_flower(session, participant.flower_id)
            if flower and flower.status == "published":
                current_bid = flower.current_bid or flower.price
                await message.answer(
                    f"❌ Faqat narx kiriting!\n\n"
                    f"🔨 Joriy narx: {format_price(current_bid)} som\n"
                    f"📊 Stavkalar soni: {flower.bid_count}\n\n"
                    f"💡 Joriy narxdan yuqori narx kiriting"
                )
