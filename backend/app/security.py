"""Security: Telegram initData validation + JWT tokens."""
import hmac
import hashlib
import json
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from .config import settings
import structlog

logger = structlog.get_logger()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_telegram_init_data(init_data: str) -> Dict[str, Any]:
    try:
        parsed = urllib.parse.parse_qs(init_data)
        data_dict = {k: v[0] for k, v in parsed.items()}

        received_hash = data_dict.pop("hash", None)
        if not received_hash:
            raise ValueError("Missing hash parameter")

        auth_date = int(data_dict.get("auth_date", 0))
        now = int(datetime.now().timestamp())

        if now - auth_date > 86400:
            raise ValueError("Init data expired")

        data_check_arr = [f"{k}={v}" for k, v in sorted(data_dict.items())]
        data_check_string = "\n".join(data_check_arr)

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=settings.BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()

        computed_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            logger.warning("Invalid init_data hash detected")
            raise ValueError("Invalid hash")

        user_data = json.loads(data_dict.get("user", "{}"))

        return {
            "user_id": user_data.get("id"),
            "username": user_data.get("username"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "language_code": user_data.get("language_code"),
            "is_premium": user_data.get("is_premium", False),
            "auth_date": auth_date,
            "query_id": data_dict.get("query_id")
        }

    except Exception as e:
        logger.error("Init data validation failed", error=str(e))
        raise ValueError(f"Invalid init data: {str(e)}")


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def verify_access_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
        token_type = payload.get("type")

        if token_type != "access":
            return None

        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            return None

        return user_id

    except JWTError as e:
        logger.warning("JWT verification failed", error=str(e))
        return None
