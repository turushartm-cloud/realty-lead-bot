"""Analytics API with charts data."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from ..database import get_db_session
from ..models import Lead, LeadStatus, AnalyticsDaily, MonitoredGroup
from ..schemas import AnalyticsSummary
from ..dependencies import get_current_user
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        total = await session.scalar(select(func.count()).select_from(Lead))
        new_24h = await session.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.created_at >= func.now() - func.text("INTERVAL '1 day'")
            )
        )
        converted = await session.scalar(
            select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.CONVERTED)
        )
        conversion_rate = (converted / total * 100) if total > 0 else 0
        avg_score = await session.scalar(
            select(func.avg(Lead.ai_score)).select_from(Lead)
        ) or 0
        status_counts = {}
        for status in LeadStatus:
            count = await session.scalar(
                select(func.count()).select_from(Lead).where(Lead.status == status)
            )
            status_counts[status.value] = count
        return AnalyticsSummary(
            total_leads=total,
            new_leads_24h=new_24h,
            converted_leads=converted,
            conversion_rate=round(conversion_rate, 2),
            avg_ai_score=round(float(avg_score), 2),
            top_source="telegram_group",
            leads_by_status=status_counts
        )


@router.get("/timeline")
async def get_timeline(days: int = 30, user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        start_date = datetime.now() - timedelta(days=days)
        result = await session.execute(
            select(
                func.date(Lead.created_at).label("date"),
                func.count().label("count"),
                func.avg(Lead.ai_score).label("avg_score")
            )
            .where(Lead.created_at >= start_date)
            .group_by(func.date(Lead.created_at))
            .order_by(func.date(Lead.created_at))
        )
        data = result.all()
        return {
            "labels": [str(row.date) for row in data],
            "leads": [row.count for row in data],
            "avg_scores": [round(float(row.avg_score or 0), 2) for row in data]
        }


@router.get("/by-category")
async def get_by_category(user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        result = await session.execute(
            select(Lead.ai_category, func.count().label("count"))
            .group_by(Lead.ai_category)
            .order_by(desc("count"))
        )
        return {
            "categories": [row.ai_category for row in result],
            "counts": [row.count for row in result]
        }


@router.get("/by-group")
async def get_by_group(user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        result = await session.execute(
            select(MonitoredGroup.title, func.count().label("count"))
            .join(Lead, Lead.source_group_id == MonitoredGroup.id)
            .group_by(MonitoredGroup.title)
            .order_by(desc("count"))
            .limit(10)
        )
        return {
            "groups": [row.title for row in result],
            "counts": [row.count for row in result]
        }
