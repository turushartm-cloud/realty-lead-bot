"""Pydantic schemas for validation."""
from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class LeadCreate(BaseModel):
    raw_text: str = Field(..., min_length=5, max_length=5000)
    source_group_id: Optional[int] = None
    source_message_id: Optional[int] = None
    telegram_username: Optional[str] = Field(None, max_length=32)
    phone: Optional[str] = Field(None, pattern=r"^\+?[\d\s\-\(\)]{7,20}$")
    email: Optional[EmailStr] = None

    @field_validator("raw_text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return v.replace("\x00", "").strip()


class LeadUpdate(BaseModel):
    status: Optional[LeadStatus] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=5000)
    priority: Optional[int] = Field(None, ge=0, le=5)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class LeadResponse(BaseModel):
    id: int
    raw_text: str
    extracted_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    telegram_username: Optional[str]
    ai_score: float
    ai_category: Optional[str]
    ai_summary: Optional[str]
    status: LeadStatus
    priority: int
    assigned_to: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    crm_synced: bool

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[LeadResponse]


class AnalyticsSummary(BaseModel):
    total_leads: int
    new_leads_24h: int
    converted_leads: int
    conversion_rate: float
    avg_ai_score: float
    top_source: Optional[str]
    leads_by_status: Dict[str, int]


class TelegramInitData(BaseModel):
    query_id: Optional[str] = None
    user: Optional[str] = None
    auth_date: Optional[int] = None
    hash: str = Field(..., min_length=32)

    @field_validator("auth_date")
    @classmethod
    def check_freshness(cls, v: Optional[int]) -> Optional[int]:
        if v:
            now = int(datetime.now().timestamp())
            if now - v > 86400:
                raise ValueError("Auth data expired")
        return v


class CRMExportRequest(BaseModel):
    lead_ids: List[int] = Field(..., min_length=1, max_length=1000)
    format: str = Field(default="xlsx", pattern="^(xlsx|csv|json)$")
    include_notes: bool = True
    include_activities: bool = False


class UserSettingsUpdate(BaseModel):
    notify_new_lead: Optional[bool] = None
    notify_daily_digest: Optional[bool] = None
    notify_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    keywords: Optional[List[str]] = None
    crm_webhook_url: Optional[str] = None
    auto_export: Optional[bool] = None
