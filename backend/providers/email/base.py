"""
EmailProvider base class — all email backends implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailMessage:
    to: str                        # recipient email
    subject: str
    html: str                      # HTML body
    text: str | None = None        # plain-text fallback
    from_name: str = "Lumina"
    from_email: str = "noreply@lumina.school"
    reply_to: str | None = None


class EmailProvider(ABC):

    @abstractmethod
    async def send(self, message: EmailMessage) -> str:
        """
        Send an email. Returns the provider's message ID.
        Raises on failure.
        """
        ...
