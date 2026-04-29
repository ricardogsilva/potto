import datetime as dt
import logging

import jwt

from ..schemas.auth import PottoUser

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"


def create_access_token(
    user: PottoUser,
    secret: str,
    expires_minutes: int = 60,
) -> str:
    payload = {
        "sub": user.id,
        "username": user.username,
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise
    except jwt.InvalidTokenError as err:
        logger.warning(f"Invalid JWT token: {err}")
        raise
