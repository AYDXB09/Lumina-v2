"""
Auth routes — username/password login (Supabase Auth) + one-time Canvas key.

POST /auth/signup           — create Supabase Auth user + link Canvas key, return JWT
POST /auth/login            — email + password (Supabase Auth), return JWT
POST /auth/forgot-password  — email a password-reset link
POST /auth/reset-password   — consume the reset link's token, set new password
GET  /auth/me               — return current user from JWT (incl. masked Canvas key info)
PATCH /auth/canvas-key      — replace the stored Canvas API key
POST /auth/refresh          — silent JWT renewal using refresh token
POST /auth/logout           — delete session from DB

POST /auth/apikey           — LEGACY: Canvas-key-as-login. Kept only so any
                               session started before the password-auth cutover
                               keeps working; not used by the current frontend.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, Request, Depends
from supabase_auth.errors import AuthApiError
from pydantic import BaseModel, EmailStr

from auth.canvas import validate_canvas_api_key
from auth.encrypt import encrypt_token
from auth.jwt_utils import create_access_token, generate_refresh_token, hash_refresh_token
from auth.middleware import get_current_user
from db.client import get_supabase, new_auth_client
from db.seed_config import seed_school_config
from config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "lumina_refresh"


def _frontend_url() -> str:
    return config.FRONTEND_URL or (config.ALLOWED_ORIGINS[0] if config.ALLOWED_ORIGINS else "")


# ------------------------------------------------------------------ #
# Request / Response models                                           #
# ------------------------------------------------------------------ #

class ApiKeyLoginRequest(BaseModel):
    canvas_url: str
    api_key: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    canvas_url: str
    api_key: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    # Exactly one of these is set, depending on which flow Supabase's
    # recovery link used -- see reset_password() below for why both exist.
    token_hash: str | None = None
    access_token: str | None = None
    new_password: str


class CanvasKeyRequest(BaseModel):
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
async def login_with_api_key(body: ApiKeyLoginRequest, response: Response, background_tasks: BackgroundTasks):
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

    return _issue_lumina_session(sb, user, canvas_role, school_id, "api_key", response, background_tasks)


# ------------------------------------------------------------------ #
# Password auth (Supabase Auth) — signup / login / reset               #
# ------------------------------------------------------------------ #

@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest, response: Response, background_tasks: BackgroundTasks):
    """
    One-time account creation: Supabase Auth identity (email + password)
    + Canvas API key, captured together so the key never needs pasting again.
    """
    canvas_url = body.canvas_url.rstrip("/")
    sb = get_supabase()

    # 1. Validate the Canvas key up front — no point creating an auth user
    #    for a key that doesn't work.
    try:
        canvas_user = await validate_canvas_api_key(canvas_url, body.api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # 2. Create the Supabase Auth user
    try:
        auth_result = sb.auth.admin.create_user({
            "email": body.email,
            "password": body.password,
            "email_confirm": True,  # no email confirmation loop for a pilot cohort
        })
    except AuthApiError as e:
        raise HTTPException(status_code=409 if "already" in str(e).lower() else 400, detail=str(e))
    auth_user_id = auth_result.user.id

    # 3-4. Upsert school + role + Lumina user profile. If anything past this point
    #      fails, the auth user from step 2 would otherwise be orphaned (a real
    #      account with no profile row, blocking retry with "already registered") —
    #      so any exception here rolls it back before re-raising.
    try:
        school_result = sb.table("schools").upsert(
            {"name": canvas_url, "canvas_url": canvas_url}, on_conflict="canvas_url",
        ).execute()
        school_id = school_result.data[0]["id"]
        seed_school_config(school_id)
        canvas_role = await _get_canvas_role(canvas_url, body.api_key)

        user_result = sb.table("users").upsert(
            {
                "canvas_user_id":          canvas_user["canvas_user_id"],
                "school_id":               school_id,
                "auth_user_id":            auth_user_id,
                "name":                    canvas_user["name"],
                "email":                   body.email,
                "avatar_url":              canvas_user["avatar_url"],
                "canvas_role":             canvas_role,
                "auth_method":             "password",
                "canvas_access_token":     encrypt_token(body.api_key),
                "canvas_key_last4":        body.api_key[-4:],
                "canvas_token_expires_at": None,
                "last_active_at":          datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="canvas_user_id,school_id",
        ).execute()
        user = user_result.data[0]
    except Exception:
        logger.exception("Signup failed after auth user creation — rolling back auth user %s", auth_user_id)
        try:
            sb.auth.admin.delete_user(auth_user_id)
        except Exception:
            logger.exception("Failed to roll back orphaned auth user %s — needs manual cleanup", auth_user_id)
        raise

    return _issue_lumina_session(sb, user, canvas_role, school_id, "password", response, background_tasks)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, response: Response, background_tasks: BackgroundTasks):
    """Email + password login via Supabase Auth."""
    # Credential check happens on a throwaway client -- see new_auth_client()
    # for why this must never run on the shared service-role singleton.
    try:
        result = new_auth_client().auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    sb = get_supabase()
    user_result = sb.table("users").select("*").eq("auth_user_id", result.user.id).execute()
    if not user_result.data:
        raise HTTPException(status_code=404, detail="No Lumina account found for this login")
    user = user_result.data[0]

    return _issue_lumina_session(
        sb, user, user["canvas_role"], user["school_id"], "password", response, background_tasks,
    )


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """
    Email a password-reset link via Supabase Auth's own built-in mailer.
    Always returns a generic success message — never reveals whether the
    email has an account, to avoid enumeration.

    NOTE: previously this generated the link ourselves (admin.generate_link)
    and sent it via a custom EmailProvider (Resend / Gmail SMTP). Switched
    to Supabase's native reset_password_for_email because it sends over
    HTTPS (Supabase's API), not raw SMTP — Railway filters outbound SMTP
    (port 587) entirely, which made both the Gmail and eventual-Resend paths
    hang/fail from this host. providers/email/ (Resend + Gmail SMTP) is kept
    for other transactional email (parent consent, reports) that isn't
    Auth-flow-shaped and can't route through Supabase's mailer.
    """
    sb = get_supabase()
    try:
        sb.auth.reset_password_for_email(
            body.email,
            {"redirect_to": f"{_frontend_url()}/reset-password"},
        )
    except Exception:
        # Covers "user not found" (AuthApiError) and send failures alike —
        # logged with full traceback for debugging, never surfaced to the
        # caller (would otherwise leak whether an email has an account).
        logger.exception("forgot-password request for %s did not send a link", body.email)

    return {"message": "If an account exists for that email, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """
    Consume the token from the reset-link email and set a new password.

    Supabase's recovery link can land here two different ways depending on
    the project's Auth flow setting:
      - token_hash: newer OTP-style verify -- consumed via verify_otp().
      - access_token: legacy verify flow -- Supabase's own /auth/v1/verify
        endpoint already validated the token server-side and redirected
        here with an already-issued session in the URL hash
        (#access_token=...&type=recovery), no token_hash at all. This is
        what this project actually uses (confirmed 2026-08-13 against a
        real email link) -- resolved via get_user() instead of verify_otp().
    """
    # Both branches below establish/read an end-user session -- run on a
    # throwaway client, never the shared service-role singleton (see
    # new_auth_client()). get_user(jwt) is a one-off lookup and probably
    # wouldn't mutate get_supabase()'s session, but verify_otp() definitely
    # would (it's a full sign-in) -- using a throwaway client for both
    # rather than relying on which gotrue-py calls happen to be "safe".
    try:
        if body.token_hash:
            verify_result = new_auth_client().auth.verify_otp(
                {"token_hash": body.token_hash, "type": "recovery"}
            )
            user_id = verify_result.user.id
        elif body.access_token:
            user_result = new_auth_client().auth.get_user(body.access_token)
            user_id = user_result.user.id
        else:
            raise HTTPException(status_code=400, detail="Reset link is missing its token")
    except AuthApiError:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")

    sb = get_supabase()

    sb.auth.admin.update_user_by_id(user_id, {"password": body.new_password})
    return {"message": "Password updated — you can now sign in with your new password"}


# ------------------------------------------------------------------ #
# Canvas key management                                                #
# ------------------------------------------------------------------ #

@router.patch("/canvas-key")
async def update_canvas_key(body: CanvasKeyRequest, current_user: dict = Depends(get_current_user)):
    """Replace the stored Canvas API key (e.g. after regenerating it in Canvas)."""
    canvas_url = body.canvas_url.rstrip("/")
    try:
        await validate_canvas_api_key(canvas_url, body.api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    sb = get_supabase()
    sb.table("users").update({
        "canvas_access_token": encrypt_token(body.api_key),
        "canvas_key_last4":    body.api_key[-4:],
        "canvas_token_expires_at": None,
    }).eq("id", current_user["sub"]).execute()

    return {"message": "Canvas key updated", "canvas_key_last4": body.api_key[-4:]}


# ------------------------------------------------------------------ #
# Session helpers                                                      #
# ------------------------------------------------------------------ #

def _issue_lumina_session(
    sb, user: dict, canvas_role: str, school_id: str, auth_method: str,
    response: Response, background_tasks: BackgroundTasks,
) -> AuthResponse:
    """Shared tail of every login path: issue JWT + refresh, trigger first-login sync."""
    user_id = user["id"]

    access_token = create_access_token(user_id, canvas_role, school_id)
    raw_refresh, hashed_refresh = generate_refresh_token()

    sb.table("sessions").insert({
        "user_id":       user_id,
        "refresh_token": hashed_refresh,
        "auth_method":   auth_method,
        "expires_at":    (
            datetime.now(timezone.utc) + timedelta(days=config.REFRESH_EXPIRE_DAYS)
        ).isoformat(),
    }).execute()

    _set_refresh_cookie(response, raw_refresh)

    existing_enrollments = sb.table("enrollments").select("course_id").eq(
        "user_id", user_id
    ).limit(1).execute()
    is_first_login = not existing_enrollments.data

    if is_first_login:
        logger.info("First login for user %s — triggering background sync + index", user_id)
        background_tasks.add_task(_first_login_sync, user_id, school_id)

    return AuthResponse(
        access_token=access_token,
        user={
            "id":               user_id,
            "name":             user["name"],
            "email":            user["email"],
            "avatar_url":       user["avatar_url"],
            "canvas_role":      canvas_role,
            "school_id":        school_id,
            "first_login":      is_first_login,
            "canvas_key_last4": user.get("canvas_key_last4"),
        },
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return current user profile from JWT, including masked Canvas key info."""
    sb = get_supabase()
    result = sb.table("users").select(
        "id, name, email, avatar_url, canvas_role, school_id, last_active_at, "
        "canvas_key_last4, canvas_token_expires_at"
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

async def _first_login_sync(user_id: str, school_id: str) -> None:
    """
    Triggered once on a student's very first login.
    Syncs all courses from Canvas and indexes their content into pgvector.
    Runs entirely in the background — does not block the login response.
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)
    try:
        from canvas.sync import sync_courses, get_course_content
        from rag.indexer import index_course_content

        courses = await sync_courses(user_id, school_id)
        _log.info("First-login sync: %d courses for user %s", len(courses), user_id)

        for course in courses:
            try:
                content = await get_course_content(user_id, int(course["canvas_course_id"]))
                chunks  = await index_course_content(course["id"], content)
                _log.info("First-login index: course %s → %d chunks", course["id"], chunks)
            except Exception as e:
                _log.error("First-login index failed for course %s: %s", course.get("id"), e)
    except Exception as e:
        _log.error("First-login sync failed for user %s: %s", user_id, e)


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
