"""
Seed default platform_config and ai_config rows for a new school.
Called once when a school is first created.
"""

from db.client import get_supabase


def seed_school_config(school_id: str) -> None:
    """
    Insert default config rows for a new school.
    Uses upsert so it's safe to call multiple times.
    """
    sb = get_supabase()

    # ------------------------------------------------------------------ #
    # platform_config defaults                                             #
    # ------------------------------------------------------------------ #
    platform_rows = [
        {
            "school_id":   school_id,
            "key":         "ai_provider",
            "value":       "k2",
            "encrypted":   False,
            "description": "AI provider: k2 | openrouter | anthropic | bedrock",
        },
        {
            "school_id":   school_id,
            "key":         "ai_model",
            "value":       "MBZUAI-IFM/K2-Think-v2",
            "encrypted":   False,
            "description": "Model ID passed to the AI provider",
        },
        {
            "school_id":   school_id,
            "key":         "ai_api_url",
            "value":       "https://api.k2think.ai/v1/chat/completions",
            "encrypted":   False,
            "description": "Base URL for AI API calls",
        },
        {
            "school_id":   school_id,
            "key":         "email_provider",
            "value":       "resend",
            "encrypted":   False,
            "description": "Email provider: resend",
        },
        {
            "school_id":   school_id,
            "key":         "email_from",
            "value":       "Lumina <noreply@lumina.school>",
            "encrypted":   False,
            "description": "From address for transactional emails",
        },
        {
            "school_id":   school_id,
            "key":         "storage_provider",
            "value":       "supabase",
            "encrypted":   False,
            "description": "File storage provider: supabase | s3",
        },
        {
            "school_id":   school_id,
            "key":         "index_on_first_login",
            "value":       "true",
            "encrypted":   False,
            "description": "Auto-index Canvas content on student first login",
        },
        {
            "school_id":   school_id,
            "key":         "max_rag_chunks",
            "value":       "8",
            "encrypted":   False,
            "description": "Max RAG chunks injected into AI context per query",
        },
        {
            "school_id":   school_id,
            "key":         "socratic_mode",
            "value":       "true",
            "encrypted":   False,
            "description": "AI uses Socratic method (guides vs gives answers)",
        },
    ]

    sb.table("platform_config").upsert(
        platform_rows, on_conflict="school_id,key"
    ).execute()

    # ------------------------------------------------------------------ #
    # ai_config defaults                                                   #
    # ------------------------------------------------------------------ #
    sb.table("ai_config").upsert(
        {
            "school_id": school_id,
            "provider":  "k2",
            "model_id":  "MBZUAI-IFM/K2-Think-v2",
            "settings":  {
                "temperature":  0.7,
                "max_tokens":   4096,
                "stream":       True,
            },
        },
        on_conflict="school_id",
    ).execute()

    # ------------------------------------------------------------------ #
    # feature_flags defaults                                               #
    # ------------------------------------------------------------------ #
    flag_rows = [
        {"school_id": school_id, "feature": "voice_mode",      "enabled": True},
        {"school_id": school_id, "feature": "mind_map",        "enabled": True},
        {"school_id": school_id, "feature": "adaptive_quiz",   "enabled": True},
        {"school_id": school_id, "feature": "parent_reports",  "enabled": False},
        {"school_id": school_id, "feature": "teacher_view",    "enabled": False},
    ]

    sb.table("feature_flags").upsert(
        flag_rows, on_conflict="school_id,feature"
    ).execute()
