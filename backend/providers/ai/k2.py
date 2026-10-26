"""
K2-Think-v2 provider — direct API call using OpenAI-compatible SDK.
"""

from typing import AsyncIterator
from openai import AsyncOpenAI
from providers.ai.base import AIProvider
from config import config


class K2Provider(AIProvider):

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=config.K2_API_KEY,
            base_url=config.K2_API_URL.replace("/chat/completions", ""),
        )
        self._model = config.K2_MODEL

    async def stream(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def complete(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return response.choices[0].message.content or ""
