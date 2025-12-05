import asyncio
from datetime import datetime
from aiogram import Bot

from database import async_session
from database.queries import (
    get_active_auctions, update_flower_status, get_flower,
    get_auction_participants, get_user, get_auction_bids
)
from database.models import User
from sqlalchemy import select
from config import CHANNEL_ID


def format_price(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


async def check_ended_auctions(bot: Bot):
    """Check for auctions that have ended and process them"""
    async with async_session() as session:
        auctions = await get_active_auctions(session)
        
        for flower in auctions:
            if not flower.auction_end_time:
                continue
            
            if datetime.utcnow() > flower.auction_end_time:
                # Auction has ended
                await process_ended_auction(bot, flower.id, session)


async def process_ended_auction(bot: Bot, flower_id: int, session):
    """Process an auction that has ended"""
    flower = await get_flower(session, flower_id)
    
    if not flower or flower.status != "published":
        return
    
    # Get highest bid
    bids = await get_auction_bids(session, flower_id)
    winner = None
    highest_bid = flower.current_bid
    
    if bids and flower.highest_bidder_id:
        top_bid = bids[0] if bids else None
        if top_bid:
            winner = {
                "telegram_id": top_bid.user_telegram_id,
                "name": top_bid.full_name or top_bid.username or "Nomalum",
                "username": top_bid.username,
                "amount": top_bid.amount,
                "bid_id": top_bid.id
            }
            highest_bid = top_bid.amount
    
    # Get owner
    result = await session.execute(select(User).where(User.id == flower.user_id))
    owner = result.scalar_one_or_none()
    
    # Prepare result message
    if winner and highest_bid > flower.price:
        winner_link = f"@{winner['username']}" if winner.get('username') else winner['name']
        
        result_text = (
            f"⏰ <b>AUKSIYON VAQTI TUGADI!</b>\n\n"
            f"🌸 {flower.name}\n\n"
            f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
            f"📊 Stavkalar soni: {flower.bid_count}\n"
            f"🏆 Eng yuqori stavka: {winner['name']}\n"
            f"💵 Stavka: {format_price(highest_bid)} som\n\n"
            f"⚠️ Sotuvchi hali javob bermagan!"
        )
        
        # Notify owner to decide
        if owner:
            try:
                from keyboards import auction_sell_kb
                await bot.send_message(
                    chat_id=owner.telegram_id,
                    text=(
                        f"⏰ <b>Auksiyon vaqti tugadi!</b>\n\n"
                        f"🌸 {flower.name}\n\n"
                        f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
                        f"📊 Stavkalar soni: {flower.bid_count}\n"
                        f"🏆 Eng yuqori stavka: {winner['name']} ({winner_link})\n"
                        f"💵 Stavka: {format_price(highest_bid)} som\n\n"
                        f"Sotishni tasdiqlaysizmi?"
                    ),
                    parse_mode="HTML",
                    reply_markup=auction_sell_kb(flower_id, winner['bid_id'], winner['telegram_id'])
                )
            except Exception:
                pass
    else:
        result_text = (
            f"⏰ <b>AUKSIYON VAQTI TUGADI!</b>\n\n"
            f"🌸 {flower.name}\n\n"
            f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
            f"📊 Stavkalar soni: {flower.bid_count}\n\n"
            f"😔 Afsuski, hech kim stavka qoymadi."
        )
        
        # Update status to ended if no bids
        await update_flower_status(session, flower_id, "ended")
    
    # Broadcast to all participants
    participants = await get_auction_participants(session, flower_id)
    for p in participants:
        try:
            await bot.send_message(
                chat_id=p.user_telegram_id,
                text=result_text,
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    # Update channel message
    try:
        if winner and highest_bid > flower.price:
            channel_text = (
                f"⏰ AUKSIYON VAQTI TUGADI\n\n"
                f"🌸 <b>{flower.name}</b>\n\n"
                f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
                f"📊 Stavkalar soni: {flower.bid_count}\n"
                f"💵 Joriy narx: {format_price(highest_bid)} som\n\n"
                f"⏳ Sotuvchi javobini kutmoqda..."
            )
        else:
            channel_text = (
                f"🏁 AUKSIYON TUGADI\n\n"
                f"🌸 <b>{flower.name}</b>\n\n"
                f"💰 Boshlangich narx: {format_price(flower.price)} som\n"
                f"📊 Stavkalar soni: {flower.bid_count}\n\n"
                f"😔 Sotilmadi"
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


async def scheduler_loop(bot: Bot):
    """Main scheduler loop - runs every minute"""
    while True:
        try:
            await check_ended_auctions(bot)
        except Exception as e:
            print(f"Scheduler error: {e}")
        
        await asyncio.sleep(60)  # Check every minute
