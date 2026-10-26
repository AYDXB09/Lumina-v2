"""
AIProvider base class — all AI providers implement this interface.
The rest of the app calls provider.stream() regardless of which model is used.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class AIProvider(ABC):

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """
        Stream response tokens as an async generator.
        Yields plain text chunks.
        """
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Non-streaming completion — returns full response string."""
        ...
