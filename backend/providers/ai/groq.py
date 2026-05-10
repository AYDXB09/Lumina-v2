"""
Groq provider — ultra-fast inference via OpenAI-compatible API.

Groq runs on custom LPU hardware; Llama 3.1 8B typically delivers
sub-second TTFT and 150-250 tok/s — much faster than NVIDIA NIM.

Models:
  llama-3.1-8b-instant    — fastest, ~1-2s TTFT
  llama-3.3-70b-versatile — best quality, ~3-5s TTFT, supports tool calling
"""

from typing import AsyncIterator
from openai import AsyncOpenAI
from providers.ai.base import AIProvider
from config import config


class GroqProvider(AIProvider):

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        self._model = config.GROQ_MODEL

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
