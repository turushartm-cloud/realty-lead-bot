"""ORM models with optimized indexes and constraints."""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    Float, ForeignKey, Index, UniqueConstraint, Enum,
    JSON, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class LeadSource(str, enum.Enum):
    TELEGRAM_GROUP = "telegram_group"
    TELEGRAM_CHANNEL = "telegram_channel"
    DIRECT_MESSAGE = "direct_message"
    MINI_APP = "mini_app"
    MANUAL = "manual"


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    username = Column(String(32), index=True)
    first_name = Column(String(64))
    last_name = Column(String(64))
    phone = Column(String(20))
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    leads = relationship("Lead", back_populates="assigned_to_user")
    settings = relationship("UserSettings", uselist=False, back_populates="user")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    notify_new_lead = Column(Boolean, default=True)
    notify_daily_digest = Column(Boolean, default=True)
    notify_threshold = Column(Float, default=0.7)

    keywords = Column(JSON, default=list)
    excluded_groups = Column(JSON, default=list)

    crm_webhook_url = Column(String(512))
    auto_export = Column(Boolean, default=False)

    user = relationship("User", back_populates="settings")


class MonitoredGroup(Base):
    __tablename__ = "monitored_groups"

    id = Column(BigInteger, primary_key=True)
    title = Column(String(255))
    username = Column(String(32), index=True)
    member_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    added_by = Column(BigInteger, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    leads = relationship("Lead", back_populates="group")


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("source_group_id", "source_message_id", name="uq_lead_message"),
        Index("idx_lead_status_created", "status", "created_at"),
        Index("idx_lead_phone", "phone"),
        Index("idx_lead_ai_score", "ai_score"),
    )

    id = Column(Integer, primary_key=True)

    source = Column(Enum(LeadSource), default=LeadSource.TELEGRAM_GROUP)
    source_group_id = Column(BigInteger, ForeignKey("monitored_groups.id"))
    source_message_id = Column(BigInteger)
    source_chat_id = Column(BigInteger)

    raw_text = Column(Text)
    extracted_name = Column(String(128))
    phone = Column(String(20))
    email = Column(String(128))
    telegram_username = Column(String(32), index=True)

    ai_score = Column(Float, default=0.0)
    ai_category = Column(String(50))
    ai_summary = Column(Text)
    ai_keywords_matched = Column(JSON, default=list)

    status = Column(Enum(LeadStatus), default=LeadStatus.NEW, index=True)
    assigned_to = Column(BigInteger, ForeignKey("users.id"), index=True)
    priority = Column(Integer, default=0)

    crm_synced = Column(Boolean, default=False)
    crm_id = Column(String(64))
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))

    group = relationship("MonitoredGroup", back_populates="leads")
    assigned_to_user = relationship("User", back_populates="leads")
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")


class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    action = Column(String(50))
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lead = relationship("Lead", back_populates="activities")


class AnalyticsDaily(Base):
    __tablename__ = "analytics_daily"
    __table_args__ = (UniqueConstraint("date", "metric_type", name="uq_daily_metric"),)

    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True), index=True)
    metric_type = Column(String(50))
    value = Column(Float, default=0)
    group_id = Column(BigInteger, ForeignKey("monitored_groups.id"))
