"""Storage provider factory."""

from functools import lru_cache
from providers.storage.base import StorageProvider


@lru_cache(maxsize=1)
def get_storage_provider() -> StorageProvider:
    # Supabase Storage is the only backend for now
    from providers.storage.supabase_storage import SupabaseStorageProvider
    return SupabaseStorageProvider()
