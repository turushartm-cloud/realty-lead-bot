"""Leads REST API with pagination, filtering, sorting."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload
from typing import Optional, List
from ..database import get_db_session
from ..models import Lead, LeadStatus, LeadActivity
from ..schemas import LeadResponse, LeadListResponse, LeadUpdate
from ..dependencies import get_current_user
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[LeadStatus] = None,
    search: Optional[str] = None,
    min_score: Optional[float] = Query(None, ge=0, le=1),
    assigned_to: Optional[int] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|ai_score|priority|updated_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    user: dict = Depends(get_current_user)
):
    async with get_db_session() as session:
        query = select(Lead)
        count_query = select(func.count()).select_from(Lead)
        filters = []
        if status:
            filters.append(Lead.status == status)
        if min_score is not None:
            filters.append(Lead.ai_score >= min_score)
        if assigned_to:
            filters.append(Lead.assigned_to == assigned_to)
        if search:
            filters.append(
                (Lead.raw_text.ilike(f"%{search}%")) |
                (Lead.phone.ilike(f"%{search}%")) |
                (Lead.email.ilike(f"%{search}%"))
            )
        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)
        sort_column = getattr(Lead, sort_by)
        query = query.order_by(desc(sort_column) if sort_order == "desc" else asc(sort_column))
        total = await session.scalar(count_query)
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        result = await session.execute(query)
        leads = result.scalars().all()
        return LeadListResponse(
            total=total,
            page=page,
            per_page=per_page,
            items=[LeadResponse.model_validate(l) for l in leads]
        )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: int, user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        result = await session.execute(
            select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.activities))
        )
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: int, update: LeadUpdate, user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        old_status = lead.status
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lead, field, value)
        if "status" in update_data and update_data["status"] != old_status:
            activity = LeadActivity(
                lead_id=lead_id,
                user_id=user["user_id"],
                action="status_change",
                details={"from": old_status, "to": update_data["status"]}
            )
            session.add(activity)
        return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.status = LeadStatus.ARCHIVED
        return {"message": "Lead archived"}
