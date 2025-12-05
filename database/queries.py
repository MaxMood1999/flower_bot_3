from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Flower, Payment, Settings, AuctionParticipant, AuctionBid
from typing import Optional, List, Tuple
from datetime import datetime

# New user bonus amount
NEW_USER_BONUS = 100000


# ==================== USER QUERIES ====================

async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, telegram_id: int, username: str = None, full_name: str = None) -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        balance=NEW_USER_BONUS  # Give bonus to new users
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str = None, full_name: str = None) -> Tuple[User, bool]:
    """Get or create user. Returns (user, is_new) tuple"""
    user = await get_user(session, telegram_id)
    is_new = False
    if not user:
        user = await create_user(session, telegram_id, username, full_name)
        is_new = True
    return user, is_new


async def update_user_balance(session: AsyncSession, telegram_id: int, amount: int) -> bool:
    """Add or subtract from user balance"""
    user = await get_user(session, telegram_id)
    if user:
        user.balance += amount
        await session.commit()
        return True
    return False


async def set_user_balance(session: AsyncSession, telegram_id: int, amount: int) -> bool:
    """Set user balance to specific amount"""
    user = await get_user(session, telegram_id)
    if user:
        user.balance = amount
        await session.commit()
        return True
    return False


async def get_all_users(session: AsyncSession) -> List[User]:
    result = await session.execute(select(User))
    return result.scalars().all()


async def set_user_admin(session: AsyncSession, telegram_id: int, is_admin: bool) -> bool:
    user = await get_user(session, telegram_id)
    if user:
        user.is_admin = is_admin
        await session.commit()
        return True
    return False


# ==================== FLOWER QUERIES ====================

async def create_flower(session: AsyncSession, user_id: int, photo_id: str, name: str, 
                        description: str, price: int, is_auction: bool, 
                        phone_number: str, location: str, auction_end_time: datetime = None,
                        media_ids: str = None) -> Flower:
    flower = Flower(
        user_id=user_id,
        photo_id=photo_id,
        media_ids=media_ids,
        name=name,
        description=description,
        price=price,
        is_auction=is_auction,
        current_bid=price if is_auction else 0,
        bid_count=0,
        phone_number=phone_number,
        location=location,
        status="pending",
        auction_end_time=auction_end_time
    )
    session.add(flower)
    await session.commit()
    await session.refresh(flower)
    return flower


async def get_flower(session: AsyncSession, flower_id: int) -> Optional[Flower]:
    result = await session.execute(
        select(Flower).where(Flower.id == flower_id)
    )
    return result.scalar_one_or_none()


async def get_flower_by_user_id(session: AsyncSession, user_id: int) -> Optional[Flower]:
    """Get flower by internal user_id"""
    result = await session.execute(
        select(Flower).where(Flower.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_flower_status(session: AsyncSession, flower_id: int, status: str, message_id: int = None):
    flower = await get_flower(session, flower_id)
    if flower:
        flower.status = status
        if message_id:
            flower.message_id = message_id
        await session.commit()


async def update_flower_bid(session: AsyncSession, flower_id: int, bid: int, bidder_telegram_id: int):
    flower = await get_flower(session, flower_id)
    if flower:
        flower.current_bid = bid
        flower.highest_bidder_id = bidder_telegram_id
        flower.bid_count = (flower.bid_count or 0) + 1
        await session.commit()


async def get_user_flowers(session: AsyncSession, user_id: int) -> List[Flower]:
    result = await session.execute(
        select(Flower).where(Flower.user_id == user_id)
    )
    return result.scalars().all()


async def get_active_auctions(session: AsyncSession) -> List[Flower]:
    result = await session.execute(
        select(Flower).where(
            Flower.is_auction == True,
            Flower.status == "published"
        )
    )
    return result.scalars().all()


# ==================== AUCTION PARTICIPANT QUERIES ====================

async def add_auction_participant(session: AsyncSession, flower_id: int, 
                                   user_telegram_id: int, username: str = None, 
                                   full_name: str = None) -> AuctionParticipant:
    # Check if already exists
    existing = await get_auction_participant(session, flower_id, user_telegram_id)
    if existing:
        if not existing.is_active:
            existing.is_active = True
            await session.commit()
        return existing
    
    participant = AuctionParticipant(
        flower_id=flower_id,
        user_telegram_id=user_telegram_id,
        username=username,
        full_name=full_name,
        is_active=True
    )
    session.add(participant)
    await session.commit()
    await session.refresh(participant)
    return participant


async def get_auction_participant(session: AsyncSession, flower_id: int, 
                                   user_telegram_id: int) -> Optional[AuctionParticipant]:
    result = await session.execute(
        select(AuctionParticipant).where(
            AuctionParticipant.flower_id == flower_id,
            AuctionParticipant.user_telegram_id == user_telegram_id
        )
    )
    return result.scalar_one_or_none()


async def get_auction_participants(session: AsyncSession, flower_id: int, 
                                    active_only: bool = True) -> List[AuctionParticipant]:
    query = select(AuctionParticipant).where(AuctionParticipant.flower_id == flower_id)
    if active_only:
        query = query.where(AuctionParticipant.is_active == True)
    result = await session.execute(query)
    return result.scalars().all()


async def remove_auction_participant(session: AsyncSession, flower_id: int, 
                                      user_telegram_id: int) -> bool:
    participant = await get_auction_participant(session, flower_id, user_telegram_id)
    if participant:
        participant.is_active = False
        await session.commit()
        return True
    return False


async def get_user_active_auction(session: AsyncSession, user_telegram_id: int) -> Optional[AuctionParticipant]:
    """Get user's current active auction participation"""
    result = await session.execute(
        select(AuctionParticipant).where(
            AuctionParticipant.user_telegram_id == user_telegram_id,
            AuctionParticipant.is_active == True
        )
    )
    return result.scalar_one_or_none()


# ==================== AUCTION BID QUERIES ====================

async def add_auction_bid(session: AsyncSession, flower_id: int, user_telegram_id: int,
                          username: str, full_name: str, amount: int) -> AuctionBid:
    bid = AuctionBid(
        flower_id=flower_id,
        user_telegram_id=user_telegram_id,
        username=username,
        full_name=full_name,
        amount=amount
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)
    return bid


async def get_auction_bids(session: AsyncSession, flower_id: int) -> List[AuctionBid]:
    result = await session.execute(
        select(AuctionBid).where(AuctionBid.flower_id == flower_id).order_by(AuctionBid.amount.desc())
    )
    return result.scalars().all()


async def get_highest_bid(session: AsyncSession, flower_id: int) -> Optional[AuctionBid]:
    result = await session.execute(
        select(AuctionBid).where(AuctionBid.flower_id == flower_id).order_by(AuctionBid.amount.desc()).limit(1)
    )
    return result.scalar_one_or_none()


# ==================== PAYMENT QUERIES ====================

async def create_payment(session: AsyncSession, user_id: int, amount: int, screenshot_id: str) -> Payment:
    payment = Payment(
        user_id=user_id,
        amount=amount,
        screenshot_id=screenshot_id,
        status="pending"
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_payment(session: AsyncSession, payment_id: int) -> Optional[Payment]:
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()


async def get_pending_payments(session: AsyncSession) -> List[Payment]:
    result = await session.execute(
        select(Payment).where(Payment.status == "pending")
    )
    return result.scalars().all()


async def update_payment_status(session: AsyncSession, payment_id: int, status: str):
    payment = await get_payment(session, payment_id)
    if payment:
        payment.status = status
        await session.commit()


# ==================== SETTINGS QUERIES ====================

async def get_setting(session: AsyncSession, key: str) -> Optional[str]:
    result = await session.execute(
        select(Settings).where(Settings.key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(session: AsyncSession, key: str, value: str):
    result = await session.execute(
        select(Settings).where(Settings.key == key)
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        setting = Settings(key=key, value=value)
        session.add(setting)
    await session.commit()


# ==================== INCOME STATISTICS ====================

async def get_income_stats(session: AsyncSession) -> dict:
    """Get approved payments statistics by period"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Daily income
    daily_result = await session.execute(
        select(func.sum(Payment.amount)).where(
            and_(
                Payment.status == "approved",
                Payment.created_at >= today_start
            )
        )
    )
    daily_income = daily_result.scalar() or 0
    
    # Weekly income
    weekly_result = await session.execute(
        select(func.sum(Payment.amount)).where(
            and_(
                Payment.status == "approved",
                Payment.created_at >= week_start
            )
        )
    )
    weekly_income = weekly_result.scalar() or 0
    
    # Monthly income
    monthly_result = await session.execute(
        select(func.sum(Payment.amount)).where(
            and_(
                Payment.status == "approved",
                Payment.created_at >= month_start
            )
        )
    )
    monthly_income = monthly_result.scalar() or 0
    
    # Yearly income
    yearly_result = await session.execute(
        select(func.sum(Payment.amount)).where(
            and_(
                Payment.status == "approved",
                Payment.created_at >= year_start
            )
        )
    )
    yearly_income = yearly_result.scalar() or 0
    
    # Total income (all time)
    total_result = await session.execute(
        select(func.sum(Payment.amount)).where(Payment.status == "approved")
    )
    total_income = total_result.scalar() or 0
    
    # Payment counts
    daily_count = await session.execute(
        select(func.count(Payment.id)).where(
            and_(Payment.status == "approved", Payment.created_at >= today_start)
        )
    )
    weekly_count = await session.execute(
        select(func.count(Payment.id)).where(
            and_(Payment.status == "approved", Payment.created_at >= week_start)
        )
    )
    monthly_count = await session.execute(
        select(func.count(Payment.id)).where(
            and_(Payment.status == "approved", Payment.created_at >= month_start)
        )
    )
    yearly_count = await session.execute(
        select(func.count(Payment.id)).where(
            and_(Payment.status == "approved", Payment.created_at >= year_start)
        )
    )
    
    return {
        "daily": {"amount": daily_income, "count": daily_count.scalar() or 0},
        "weekly": {"amount": weekly_income, "count": weekly_count.scalar() or 0},
        "monthly": {"amount": monthly_income, "count": monthly_count.scalar() or 0},
        "yearly": {"amount": yearly_income, "count": yearly_count.scalar() or 0},
        "total": total_income
    }
