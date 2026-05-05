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
