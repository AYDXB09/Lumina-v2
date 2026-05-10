"""
AI provider factory — returns the configured provider instance.

Which provider is used is controlled by AI_PROVIDER env var:
  k2          → K2-Think-v2 direct (default)
  openrouter  → OpenRouter (access to many models)
  anthropic   → Anthropic Claude
  nvidia      → NVIDIA NIM (DeepSeek, Llama, etc.)
  groq        → Groq LPU (ultra-fast, llama-3.1-8b-instant default)

School admins can override per-school via ai_config table (future).
"""

from functools import lru_cache
from providers.ai.base import AIProvider
from config import config


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    provider = (config.AI_PROVIDER or "k2").lower()

    if provider == "openrouter":
        from providers.ai.openrouter import OpenRouterProvider
        return OpenRouterProvider()
    elif provider == "anthropic":
        from providers.ai.anthropic import AnthropicProvider
        return AnthropicProvider()
    elif provider == "nvidia":
        from providers.ai.nvidia import NvidiaProvider
        return NvidiaProvider()
    elif provider == "groq":
        from providers.ai.groq import GroqProvider
        return GroqProvider()
    else:
        from providers.ai.k2 import K2Provider
        return K2Provider()
