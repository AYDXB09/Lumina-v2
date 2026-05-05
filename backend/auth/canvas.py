"""
CanvasAuthProvider — validates Canvas credentials and fetches user identity.

Abstraction layer: get_canvas_token(user_id) works identically for
api_key, oauth, and lti auth methods.
"""

import httpx
from db.client import get_supabase
from auth.encrypt import decrypt_token


async def validate_canvas_api_key(canvas_url: str, api_key: str) -> dict:
    """
    Validate a student's Canvas API key by calling /api/v1/users/self.
    Returns Canvas user profile on success, raises ValueError on failure.
    """
    canvas_url = canvas_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{canvas_url}/api/v1/users/self", headers=headers)

    if resp.status_code == 401:
        raise ValueError("Invalid Canvas API key — please check and try again.")
    if resp.status_code == 404:
        raise ValueError("Canvas URL not found — please check the URL and try again.")
    if not resp.is_success:
        raise ValueError(f"Canvas returned {resp.status_code} — please try again.")

    data = resp.json()
    return {
        "canvas_user_id": str(data["id"]),
        "name": data.get("name", ""),
        "email": data.get("email") or data.get("login_id", ""),
        "avatar_url": data.get("avatar_url", ""),
    }


async def get_canvas_token(user_id: str) -> str:
    """
    Retrieve the current valid Canvas token for a user.
    Handles all auth methods transparently:
      - api_key: read + decrypt from DB (never expires)
      - oauth:   read + refresh if near expiry  (TODO: Phase 4)
      - lti:     read + refresh if near expiry  (TODO: Phase 5)
    """
    sb = get_supabase()
    result = sb.table("users").select(
        "canvas_access_token, canvas_refresh_token, canvas_token_expires_at, auth_method"
    ).eq("id", user_id).single().execute()

    if not result.data:
        raise ValueError(f"User {user_id} not found")

    user = result.data
    auth_method = user["auth_method"]

    if auth_method == "api_key":
        # API keys don't expire — just decrypt and return
        return decrypt_token(user["canvas_access_token"])

    if auth_method in ("oauth", "lti"):
        # TODO Phase 4/5: check expiry, refresh if needed
        # For now, return the stored token
        return decrypt_token(user["canvas_access_token"])

    raise ValueError(f"Unknown auth_method: {auth_method}")
