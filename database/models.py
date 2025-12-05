from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    balance = Column(Integer, default=0)  # Balans so'mda
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    flowers = relationship("Flower", back_populates="owner")
    payments = relationship("Payment", back_populates="user")


class Flower(Base):
    __tablename__ = "flowers"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    photo_id = Column(String(255), nullable=False)  # First media for reference
    media_ids = Column(Text, nullable=True)  # All media IDs (JSON list)
    media_type = Column(String(50), default="photo")  # photo or video or mixed
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)  # Boshlang'ich narx
    is_auction = Column(Boolean, default=False)
    current_bid = Column(Integer, default=0)
    bid_count = Column(Integer, default=0)  # Stavkalar soni
    highest_bidder_id = Column(Integer, nullable=True)
    phone_number = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    seller_username = Column(String(255), nullable=True)
    seller_telegram_id = Column(Integer, nullable=True)
    status = Column(String(50), default="pending")  # pending, published, sold, ended
    message_id = Column(Integer, nullable=True)  # Kanaldagi xabar ID
    auction_end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="flowers")
    participants = relationship("AuctionParticipant", back_populates="flower")
    bids = relationship("AuctionBid", back_populates="flower")


class AuctionParticipant(Base):
    __tablename__ = "auction_participants"
    
    id = Column(Integer, primary_key=True)
    flower_id = Column(Integer, ForeignKey("flowers.id"), nullable=False)
    user_telegram_id = Column(Integer, nullable=False)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    flower = relationship("Flower", back_populates="participants")


class AuctionBid(Base):
    __tablename__ = "auction_bids"
    
    id = Column(Integer, primary_key=True)
    flower_id = Column(Integer, ForeignKey("flowers.id"), nullable=False)
    user_telegram_id = Column(Integer, nullable=False)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    amount = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    flower = relationship("Flower", back_populates="bids")


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # Summasi so'mda
    screenshot_id = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="payments")


class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
