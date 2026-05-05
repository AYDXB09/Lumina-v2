"""
Supabase Storage provider — uses Supabase Storage API via supabase-py.
Buckets are created in Supabase dashboard:
  - student-materials  (private, per-user uploads)
"""

from providers.storage.base import StorageProvider
from db.client import get_supabase


class SupabaseStorageProvider(StorageProvider):

    async def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        sb = get_supabase()
        sb.storage.from_(bucket).upload(
            path=path,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        # Return the public path — caller can get signed URL separately
        return path

    async def download(self, bucket: str, path: str) -> bytes:
        sb = get_supabase()
        return sb.storage.from_(bucket).download(path)

    async def delete(self, bucket: str, path: str) -> None:
        sb = get_supabase()
        sb.storage.from_(bucket).remove([path])

    async def get_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        sb = get_supabase()
        result = sb.storage.from_(bucket).create_signed_url(path, expires_in)
        return result["signedURL"]
