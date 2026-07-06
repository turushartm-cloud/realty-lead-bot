"""Telegram WebApp authentication endpoints."""
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse
from ..security import validate_telegram_init_data, create_access_token
from ..database import get_db_session
from ..models import User
from sqlalchemy import select
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram")
async def auth_telegram(init_data: str = Header(..., alias="X-Telegram-Init-Data")):
    try:
        tg_data = validate_telegram_init_data(init_data)
        user_id = tg_data["user_id"]
        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                user = User(
                    id=user_id,
                    username=tg_data.get("username"),
                    first_name=tg_data.get("first_name"),
                    last_name=tg_data.get("last_name"),
                    is_active=True
                )
                session.add(user)
                logger.info("New user registered", user_id=user_id)
            user.is_active = True
        token = create_access_token(user_id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": tg_data.get("username"),
                "first_name": tg_data.get("first_name"),
                "is_premium": tg_data.get("is_premium", False)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error("Auth error", error=str(e))
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/me")
async def get_current_user_info(user: dict = None):
    return user
