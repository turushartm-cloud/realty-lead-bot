"""CRM integration endpoints."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from typing import List
from ..database import get_db_session
from ..models import Lead, LeadStatus
from ..schemas import CRMExportRequest
from ..dependencies import get_current_user
import pandas as pd
import io
import json
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/crm", tags=["crm"])


@router.post("/export")
async def export_leads(request: CRMExportRequest, user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        result = await session.execute(select(Lead).where(Lead.id.in_(request.lead_ids)))
        leads = result.scalars().all()
        if not leads:
            raise HTTPException(status_code=404, detail="No leads found")
        data = []
        for lead in leads:
            row = {
                "ID": lead.id,
                "Source": lead.source.value,
                "Status": lead.status.value,
                "AI Score": lead.ai_score,
                "Category": lead.ai_category,
                "Name": lead.extracted_name,
                "Phone": lead.phone,
                "Email": lead.email,
                "Telegram": lead.telegram_username,
                "Summary": lead.ai_summary,
                "Created": lead.created_at.isoformat() if lead.created_at else None,
                "Notes": lead.notes if request.include_notes else None
            }
            data.append(row)
        df = pd.DataFrame(data)
        if request.format == "xlsx":
            output = io.BytesIO()
            df.to_excel(output, index=False, engine="openpyxl")
            output.seek(0)
            return {
                "filename": f"leads_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "content": output.getvalue().hex(),
                "format": "xlsx"
            }
        elif request.format == "csv":
            return {
                "filename": f"leads_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "content": df.to_csv(index=False),
                "format": "csv"
            }
        else:
            return {
                "filename": f"leads_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                "content": json.dumps(data, ensure_ascii=False, indent=2),
                "format": "json"
            }


@router.post("/sync/{lead_id}")
async def sync_to_crm(lead_id: int, user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.crm_synced = True
        lead.crm_id = f"CRM-{lead_id}"
        logger.info("Lead synced to CRM", lead_id=lead_id, user_id=user["user_id"])
        return {"message": "Lead synced", "crm_id": lead.crm_id}


@router.post("/bulk-sync")
async def bulk_sync(lead_ids: List[int], user: dict = Depends(get_current_user)):
    async with get_db_session() as session:
        result = await session.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        leads = result.scalars().all()
        synced = 0
        for lead in leads:
            lead.crm_synced = True
            lead.crm_id = f"CRM-{lead.id}"
            synced += 1
        return {"synced": synced, "total": len(lead_ids)}
