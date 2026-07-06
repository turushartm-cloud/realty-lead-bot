"""FastAPI dependencies."""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .security import verify_access_token, validate_telegram_init_data
from .database import get_db_session
import structlog

logger = structlog.get_logger()
security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer)
) -> dict:
    """Dependency to get authenticated user from JWT or Telegram initData."""

    # Try JWT first
    if credentials and credentials.credentials:
        user_id = verify_access_token(credentials.credentials)
        if user_id:
            return {"user_id": user_id, "auth_method": "jwt"}

    # Try Telegram initData
    init_data = request.headers.get("X-Telegram-Init-Data")
    if init_data:
        try:
            tg_data = validate_telegram_init_data(init_data)
            return {
                "user_id": tg_data["user_id"],
                "auth_method": "telegram",
                "telegram_data": tg_data
            }
        except ValueError as e:
            logger.warning("Invalid Telegram initData", error=str(e))

    raise HTTPException(status_code=401, detail="Authentication required")


async def get_db():
    """Database session dependency."""
    async with get_db_session() as session:
        yield session
