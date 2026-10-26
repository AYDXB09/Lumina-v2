"""
NVIDIA NIM provider — OpenAI-compatible API.
Gives access to DeepSeek, Llama, Mistral and other models
hosted on NVIDIA's inference infrastructure.

Get your API key at: https://build.nvidia.com
"""

from typing import AsyncIterator
from openai import AsyncOpenAI
from providers.ai.base import AIProvider
from config import config


class NvidiaProvider(AIProvider):

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=config.NVIDIA_API_KEY,
            base_url=config.NVIDIA_API_URL,
        )
        self._model = config.NVIDIA_MODEL

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
