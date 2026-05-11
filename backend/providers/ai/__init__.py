"""
AI provider factory — returns the configured provider instance.

Provider + model are read from Supabase ai_config (school_id IS NULL = global).
Falls back to env vars if no DB row exists.
Cache TTL: 60 seconds — change in Supabase dashboard, takes effect within 1 min.
No redeployment needed.

To change provider/model: update the global row in ai_config table:
  UPDATE ai_config SET provider='groq', model_id='llama-3.3-70b-versatile'
  WHERE school_id IS NULL;

Or insert if it doesn't exist:
  INSERT INTO ai_config (school_id, provider, model_id)
  VALUES (NULL, 'groq', 'llama-3.3-70b-versatile')
  ON CONFLICT (school_id) DO UPDATE SET provider=EXCLUDED.provider, model_id=EXCLUDED.model_id;
"""

import logging
import time
from providers.ai.base import AIProvider
from config import config

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Config cache                                                        #
# ------------------------------------------------------------------ #

_CACHE_TTL = 60  # seconds
_cached_provider: str | None = None
_cached_model: str | None = None
_cache_ts: float = 0.0
_provider_instance: AIProvider | None = None
_instance_key: tuple | None = None   # (provider, model) — bust when config changes


def _env_model(provider: str) -> str:
    return {
        "groq":        config.GROQ_MODEL,
        "nvidia":      config.NVIDIA_MODEL,
        "anthropic":   config.ANTHROPIC_MODEL,
        "openrouter":  config.OPENROUTER_MODEL,
        "gemini":      config.GEMINI_MODEL,
        "k2":          config.K2_MODEL,
    }.get(provider, config.K2_MODEL)


def _load_config_from_db() -> tuple[str, str]:
    """Read provider + model from Supabase global_config table. Sync."""
    try:
        from db.client import get_supabase
        sb = get_supabase()
        rows = sb.table("global_config").select("key, value").in_("key", ["ai_provider", "ai_model"]).execute()
        if rows.data:
            data = {r["key"]: r["value"] for r in rows.data}
            provider = data.get("ai_provider", "").lower()
            model    = data.get("ai_model", "")
            if provider:
                return provider, model or _env_model(provider)
    except Exception as e:
        logger.warning("global_config DB read failed (using env fallback): %s", e)

    # Fallback to env vars
    p = (config.AI_PROVIDER or "k2").lower()
    return p, _env_model(p)


def get_active_config() -> tuple[str, str]:
    """Return (provider, model) — cached 60s."""
    global _cached_provider, _cached_model, _cache_ts
    now = time.monotonic()
    if _cached_provider and (now - _cache_ts) < _CACHE_TTL:
        return _cached_provider, _cached_model   # type: ignore[return-value]
    provider, model = _load_config_from_db()
    _cached_provider, _cached_model, _cache_ts = provider, model, now
    logger.info("ai_config loaded: provider=%s model=%s", provider, model)
    return provider, model


def get_ai_provider() -> AIProvider:
    """Return cached provider instance; rebuilds when config changes."""
    global _provider_instance, _instance_key

    provider, model = get_active_config()
    key = (provider, model)

    if _provider_instance is not None and _instance_key == key:
        return _provider_instance

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

    # Override model if DB specifies something different from env default
    if hasattr(inst, "_model"):
        inst._model = model

    _provider_instance = inst
    _instance_key = key
    return inst
