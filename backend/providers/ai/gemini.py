"""
Google Gemini provider — via OpenAI-compatible endpoint.

Uses Google's drop-in OpenAI-compatible API so no extra SDK needed.
Free tier: Gemini 2.0 Flash — 15 RPM, 1M TPM, no credit card required.
Get a key at: https://aistudio.google.com

Base URL: https://generativelanguage.googleapis.com/v1beta/openai/
"""

import logging
from typing import AsyncIterator
from openai import AsyncOpenAI
from providers.ai.base import AIProvider
from config import config

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=config.GEMINI_API_KEY,
            base_url=config.GEMINI_API_URL,
            max_retries=0,
        )
        self._model = config.GEMINI_MODEL

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

        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=all_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                extra_body={"thinking": {"type": "disabled"}},
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logger.error("Gemini stream error: %s", e)
            raise

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
            extra_body={"thinking": {"type": "disabled"}},
        )
        return response.choices[0].message.content or ""
