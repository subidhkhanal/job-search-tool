import hmac
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from .config import get_settings

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def verify_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    return (
        hmac.compare_digest(username, settings.APP_USERNAME)
        and hmac.compare_digest(password, settings.APP_PASSWORD)
    )


def create_access_token(username: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
