"""
Auth routes — Canvas API Key login, session management.

POST /auth/apikey    — validate Canvas key, upsert user, return JWT
GET  /auth/me        — return current user from JWT
POST /auth/refresh   — silent JWT renewal using refresh token
POST /auth/logout    — delete session from DB
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel

from auth.canvas import validate_canvas_api_key
from auth.encrypt import encrypt_token
from auth.jwt_utils import create_access_token, generate_refresh_token, hash_refresh_token
from auth.middleware import get_current_user
from db.client import get_supabase
from db.seed_config import seed_school_config
from config import config

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "lumina_refresh"


# ------------------------------------------------------------------ #
# Request / Response models                                           #
# ------------------------------------------------------------------ #

class ApiKeyLoginRequest(BaseModel):
    canvas_url: str
    api_key: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",      # lax works for same-site; change to "none" if cross-origin
        max_age=config.REFRESH_EXPIRE_DAYS * 24 * 3600,
        path="/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/auth")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@router.post("/apikey", response_model=AuthResponse)
async def login_with_api_key(body: ApiKeyLoginRequest, response: Response):
    """
    Validate student's Canvas API key, upsert user in Supabase,
    issue Lumina JWT + refresh token.
    """
    canvas_url = body.canvas_url.rstrip("/")

    # 1. Validate key against Canvas
    try:
        canvas_user = await validate_canvas_api_key(canvas_url, body.api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    sb = get_supabase()

    # 2. Upsert school
    school_result = sb.table("schools").upsert(
        {"name": canvas_url, "canvas_url": canvas_url},
        on_conflict="canvas_url",
    ).execute()
    school_id = school_result.data[0]["id"]

    # 3. Seed default config if new school
    seed_school_config(school_id)

    # 4. Determine Canvas role via enrollments
    canvas_role = await _get_canvas_role(canvas_url, body.api_key)

    # 5. Upsert user
    user_result = sb.table("users").upsert(
        {
            "canvas_user_id":          canvas_user["canvas_user_id"],
            "school_id":               school_id,
            "name":                    canvas_user["name"],
            "email":                   canvas_user["email"],
            "avatar_url":              canvas_user["avatar_url"],
            "canvas_role":             canvas_role,
            "auth_method":             "api_key",
            "canvas_access_token":     encrypt_token(body.api_key),
            "canvas_token_expires_at": None,
            "last_active_at":          datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="canvas_user_id,school_id",
    ).execute()
    user = user_result.data[0]
    user_id = user["id"]

    # 6. Issue tokens
    access_token = create_access_token(user_id, canvas_role, school_id)
    raw_refresh, hashed_refresh = generate_refresh_token()

    # 7. Store refresh token
    sb.table("sessions").insert({
        "user_id":      user_id,
        "refresh_token": hashed_refresh,
        "auth_method":  "api_key",
        "expires_at":   (
            datetime.now(timezone.utc) +
            timedelta(days=config.REFRESH_EXPIRE_DAYS)
        ).isoformat(),
    }).execute()

    # 8. Set refresh cookie
    _set_refresh_cookie(response, raw_refresh)

    return AuthResponse(
        access_token=access_token,
        user={
            "id":         user_id,
            "name":       user["name"],
            "email":      user["email"],
            "avatar_url": user["avatar_url"],
            "role":       canvas_role,
            "school_id":  school_id,
        },
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return current user profile from JWT."""
    sb = get_supabase()
    result = sb.table("users").select(
        "id, name, email, avatar_url, canvas_role, school_id, last_active_at"
    ).eq("id", current_user["sub"]).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    # Update last_active_at
    sb.table("users").update(
        {"last_active_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", current_user["sub"]).execute()

    return result.data


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """
    Silent JWT renewal. Reads refresh token from httpOnly cookie.
    Issues new JWT + rotates refresh token.
    """
    raw_refresh = request.cookies.get(REFRESH_COOKIE)
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="No refresh token")

    hashed = hash_refresh_token(raw_refresh)
    sb = get_supabase()
    now = datetime.now(timezone.utc)

    # Find valid session
    result = sb.table("sessions").select("*").eq(
        "refresh_token", hashed
    ).gt("expires_at", now.isoformat()).execute()

    if not result.data:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid")

    session = result.data[0]
    user_id = session["user_id"]

    # Get user
    user_result = sb.table("users").select(
        "id, canvas_role, school_id"
    ).eq("id", user_id).single().execute()
    user = user_result.data

    # Rotate refresh token
    new_raw, new_hashed = generate_refresh_token()
    sb.table("sessions").update({
        "refresh_token": new_hashed,
        "last_used_at":  now.isoformat(),
        "expires_at":    (now + timedelta(days=config.REFRESH_EXPIRE_DAYS)).isoformat(),
    }).eq("id", session["id"]).execute()

    access_token = create_access_token(user_id, user["canvas_role"], user["school_id"])
    _set_refresh_cookie(response, new_raw)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user),
):
    """Invalidate session — delete from DB + clear cookie."""
    raw_refresh = request.cookies.get(REFRESH_COOKIE)
    if raw_refresh:
        hashed = hash_refresh_token(raw_refresh)
        get_supabase().table("sessions").delete().eq(
            "refresh_token", hashed
        ).execute()

    _clear_refresh_cookie(response)
    return {"message": "Logged out"}


# ------------------------------------------------------------------ #
# Internal helper                                                     #
# ------------------------------------------------------------------ #

async def _get_canvas_role(canvas_url: str, api_key: str) -> str:
    """
    Determine if the user is a student or teacher from Canvas enrollments.
    Defaults to 'student' if unable to determine.
    """
    import httpx
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{canvas_url}/api/v1/courses",
                headers=headers,
                params={"enrollment_type": "teacher", "per_page": 1},
            )
        if resp.is_success and resp.json():
            return "teacher"
    except Exception:
        pass
    return "student"
