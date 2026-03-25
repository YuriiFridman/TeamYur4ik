import datetime
import logging
from typing import Optional, Dict

import jwt

import config

logger = logging.getLogger(__name__)


def create_token(user_id: int, username: str) -> str:
    """
    Create a signed JWT token containing user_id, username and an expiry timestamp.
    The token is signed with SECRET_KEY using JWT_ALGORITHM.
    """
    payload = {
        "user_id": user_id,
        "username": username,
        # Token expires after JWT_EXPIRY_HOURS hours from now
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=config.JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict]:
    """
    Decode and verify a JWT token.
    Returns {"user_id": int, "username": str} on success.
    Returns None if the token is expired or otherwise invalid.
    """
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        return {"user_id": payload["user_id"], "username": payload["username"]}
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
