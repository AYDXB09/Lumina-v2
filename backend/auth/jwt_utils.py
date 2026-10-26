"""
JWT utilities — issue and verify Lumina session tokens.
"""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
from config import config


# ------------------------------------------------------------------ #
# JWT                                                                  #
# ------------------------------------------------------------------ #

def create_access_token(user_id: str, canvas_role: str, school_id: str) -> str:
    """Issue a short-lived Lumina JWT."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": canvas_role,
        "school": school_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def verify_access_token(token: str) -> dict:
    """
    Verify and decode a Lumina JWT.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])


# ------------------------------------------------------------------ #
# Refresh tokens                                                       #
# ------------------------------------------------------------------ #

def generate_refresh_token() -> tuple[str, str]:
    """
    Returns (raw_token, hashed_token).
    Store the hash in DB, send raw to client.
    """
    raw = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
