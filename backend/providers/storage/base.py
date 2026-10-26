"""
StorageProvider base class — all storage backends implement this interface.
Used for student-uploaded files (PDFs, notes, etc.).
"""

from abc import ABC, abstractmethod


class StorageProvider(ABC):

    @abstractmethod
    async def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file. Returns the public or signed URL.
        path format: {user_id}/{filename}
        """
        ...

    @abstractmethod
    async def download(self, bucket: str, path: str) -> bytes:
        """Download a file by its storage path."""
        ...

    @abstractmethod
    async def delete(self, bucket: str, path: str) -> None:
        """Delete a file from storage."""
        ...

    @abstractmethod
    async def get_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        """Return a signed URL valid for `expires_in` seconds."""
        ...
