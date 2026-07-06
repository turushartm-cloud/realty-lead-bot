"""Export endpoints for leads."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from ..database import get_db_session
from ..models import Lead
from ..dependencies import get_current_user
import pandas as pd
import io
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/export", tags=["export"])


@router.get("/excel")
async def export_excel(
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user)
):
    async with get_db_session() as session:
        query = select(Lead)
        if status:
            query = query.where(Lead.status == status)
        if date_from:
            query = query.where(Lead.created_at >= date_from)
        if date_to:
            query = query.where(Lead.created_at <= date_to)
        result = await session.execute(query)
        leads = result.scalars().all()
        data = [{
            "ID": l.id,
            "Status": l.status.value,
            "AI Score": l.ai_score,
            "Category": l.ai_category,
            "Name": l.extracted_name,
            "Phone": l.phone,
            "Email": l.email,
            "Telegram": l.telegram_username,
            "Summary": l.ai_summary,
            "Created": l.created_at,
            "Notes": l.notes
        } for l in leads]
        df = pd.DataFrame(data)
        output = io.BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=leads_{datetime.now().strftime('%Y%m%d')}.xlsx"}
        )
