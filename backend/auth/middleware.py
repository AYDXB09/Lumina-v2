"""
JWT middleware — FastAPI dependency for protected routes.

Usage:
    from auth.middleware import get_current_user

    @app.get("/api/protected")
    async def protected(user=Depends(get_current_user)):
        return {"user_id": user["sub"]}
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.jwt_utils import verify_access_token

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Extract and verify Lumina JWT from Authorization: Bearer <token> header.
    Returns decoded payload: { sub: user_id, role, school, exp, iat }
    """
    try:
        payload = verify_access_token(credentials.credentials)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired — please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_student(user=Depends(get_current_user)) -> dict:
    """Require student role."""
    if user.get("role") not in ("student", "teacher"):
        raise HTTPException(status_code=403, detail="Student access required")
    return user


async def get_current_teacher(user=Depends(get_current_user)) -> dict:
    """Require teacher role."""
    if user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    return user
