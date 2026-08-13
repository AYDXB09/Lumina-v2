"""
Supabase client — singleton used across the backend.
Uses the service role key (bypasses RLS for server-side operations).
"""

from supabase import create_client, Client
from config import config

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment"
            )
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return _client


def new_auth_client() -> Client:
    """
    A throwaway client for operations that establish an end-user session
    (sign_in_with_password, verify_otp) -- NEVER call those on get_supabase().

    Those calls swap the client's Postgrest auth header from the service
    role key to the just-authenticated user's own JWT, so every .table()
    call after that, on that same client, runs as that user instead of the
    service role. Since every table has RLS enabled with zero policies
    (deny-all), the very next query silently returns 0 rows instead of
    erroring -- this is exactly what caused a correct login to report
    "No Lumina account found" right after Supabase itself confirmed the
    password was right (found 2026-08-13: get_supabase() is a process-wide
    singleton, so this didn't just break the current request -- it
    poisoned the shared client's identity for whatever request happened
    to reuse it next, until another auth call rotated it again).

    Cheap to create (mostly httpx client setup) -- fine to call per-request.
    """
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
