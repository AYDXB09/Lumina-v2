"""
Lumina Backend — Configuration.
All values loaded from environment variables (Railway Variables in production).
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:

    # ------------------------------------------------------------------ #
    # Supabase                                                             #
    # ------------------------------------------------------------------ #
    SUPABASE_URL: str         = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # ------------------------------------------------------------------ #
    # Auth                                                                 #
    # ------------------------------------------------------------------ #
    JWT_SECRET: str          = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str       = "HS256"
    JWT_EXPIRE_MINUTES: int  = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days
    REFRESH_EXPIRE_DAYS: int = int(os.getenv("REFRESH_EXPIRE_DAYS", "90"))
    ENCRYPTION_KEY: str      = os.getenv("ENCRYPTION_KEY", "")  # Fernet key for Canvas tokens

    # ------------------------------------------------------------------ #
    # AI Providers                                                         #
    # ------------------------------------------------------------------ #
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "k2")  # k2 | openrouter | anthropic | nvidia | groq

    # K2-Think-v2 (direct)
    K2_API_KEY: str = os.getenv("K2_API_KEY", "")
    K2_API_URL: str = os.getenv("K2_API_URL", "https://api.k2think.ai/v1/chat/completions")
    K2_MODEL: str   = os.getenv("K2_MODEL", "MBZUAI-IFM/K2-Think-v2")

    # OpenRouter
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_API_URL: str = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
    OPENROUTER_MODEL: str   = os.getenv("OPENROUTER_MODEL", "MBZUAI-IFM/K2-Think-v2")

    # Anthropic direct
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str   = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    # NVIDIA NIM (OpenAI-compatible)
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_API_URL: str = os.getenv("NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_MODEL: str   = os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-r1-0528")

    # Groq (LPU — ultra-fast inference)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Google Gemini (OpenAI-compatible endpoint — free tier via AI Studio)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # ------------------------------------------------------------------ #
    # Email — Resend                                                       #
    # ------------------------------------------------------------------ #
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    EMAIL_FROM: str     = os.getenv("EMAIL_FROM", "Lumina <noreply@lumina.school>")

    # ------------------------------------------------------------------ #
    # Canvas                                                               #
    # ------------------------------------------------------------------ #
    CANVAS_BASE_URL: str = os.getenv("CANVAS_BASE_URL", "https://dwight.instructure.com")

    # ------------------------------------------------------------------ #
    # Server                                                               #
    # ------------------------------------------------------------------ #
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    ALLOWED_ORIGINS: list[str] = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174"
    ).split(",")

    # ------------------------------------------------------------------ #
    # Legacy (kept during ChromaDB → pgvector migration)                  #
    # ------------------------------------------------------------------ #
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")


config = Config()
