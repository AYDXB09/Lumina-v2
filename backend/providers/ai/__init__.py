"""
AI provider factory — returns the configured provider instance.

Single source of truth: Railway environment variables.
  AI_PROVIDER  — provider name (groq, gemini, anthropic, openrouter, nvidia, k2)
  GROQ_MODEL / GEMINI_MODEL / etc — model name for each provider

To change provider/model: update Railway env vars and redeploy (or restart the service).
"""

import logging
from providers.ai.base import AIProvider
from config import config

logger = logging.getLogger(__name__)

_provider_instance: AIProvider | None = None


def _model_for(provider: str) -> str:
    return {
        "groq":       config.GROQ_MODEL,
        "nvidia":     config.NVIDIA_MODEL,
        "anthropic":  config.ANTHROPIC_MODEL,
        "openrouter": config.OPENROUTER_MODEL,
        "gemini":     config.GEMINI_MODEL,
        "k2":         config.K2_MODEL,
    }.get(provider, config.K2_MODEL)


def get_active_config() -> tuple[str, str]:
    """Return (provider, model) from env vars."""
    provider = (config.AI_PROVIDER or "k2").lower()
    model = _model_for(provider)
    return provider, model


def get_ai_provider() -> AIProvider:
    """Return the provider instance (singleton, built once at startup)."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider, model = get_active_config()
    logger.info("Building AI provider: %s / %s", provider, model)

    if provider == "openrouter":
        from providers.ai.openrouter import OpenRouterProvider
        inst = OpenRouterProvider()
    elif provider == "anthropic":
        from providers.ai.anthropic import AnthropicProvider
        inst = AnthropicProvider()
    elif provider == "nvidia":
        from providers.ai.nvidia import NvidiaProvider
        inst = NvidiaProvider()
    elif provider == "groq":
        from providers.ai.groq import GroqProvider
        inst = GroqProvider()
    elif provider == "gemini":
        from providers.ai.gemini import GeminiProvider
        inst = GeminiProvider()
    else:
        from providers.ai.k2 import K2Provider
        inst = K2Provider()

    _provider_instance = inst
    return inst
