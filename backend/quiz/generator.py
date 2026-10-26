"""
Adaptive quiz generator.

Ported from v1's QuizView.jsx concept (one question at a time, difficulty
tied to a running mastery score) with two fixes:
  1. Mastery is persisted to `mastery_scores`, not just held in React state —
     v1 lost all progress on refresh.
  2. Uses real semantic search (rag/search.py) for question context instead
     of v1's "first 3 transcript chunks, truncated at 4000 chars."

One question generated per call via provider.complete() (model-agnostic,
same JSON-in-response-text pattern as backend/studyplan/generator.py) —
not a whole quiz up front, so difficulty can adapt after every answer.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

DIFFICULTY_BANDS = (
    (0.3, "beginner"),
    (0.7, "intermediate"),
    (1.01, "advanced"),  # anything up to and including 1.0
)

MASTERY_LEARNING_RATE = 0.3  # weight given to the newest answer vs. history


def _difficulty_for(mastery: float) -> str:
    for threshold, label in DIFFICULTY_BANDS:
        if mastery < threshold:
            return label
    return "advanced"


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


async def _get_mastery(user_id: str, course_id: str, concept: str) -> float:
    from db.client import get_supabase
    sb = get_supabase()
    result = sb.table("mastery_scores").select("score").eq(
        "user_id", user_id
    ).eq("course_id", course_id).eq("concept", concept).maybe_single().execute()
    # .maybe_single().execute() returns None (not a response with .data=None)
    # when zero rows match — must guard on `result` itself, not just `.data`.
    if result and result.data:
        return result.data["score"]
    return 0.5  # no history yet — start at intermediate


async def update_mastery(user_id: str, course_id: str, concept: str, correct: bool) -> float:
    """Exponential moving average — recent answers matter more than old ones."""
    from db.client import get_supabase
    sb = get_supabase()

    current = await _get_mastery(user_id, course_id, concept)
    outcome = 1.0 if correct else 0.0
    new_score = round(
        (1 - MASTERY_LEARNING_RATE) * current + MASTERY_LEARNING_RATE * outcome, 4
    )
    new_score = max(0.0, min(1.0, new_score))

    sb.table("mastery_scores").upsert({
        "user_id": user_id,
        "course_id": course_id,
        "concept": concept,
        "score": new_score,
        "evidence": [],  # reserved for future: store which questions informed this score
    }, on_conflict="user_id,course_id,concept").execute()

    return new_score


async def generate_question(
    user_id: str,
    course_id: str,
    topic: str,
    exclude_questions: list[str] | None = None,
) -> dict:
    """
    Returns {question, options, correct_index, hint, difficulty, mastery}.
    On repeated JSON parse failure, raises — the quiz can't proceed without
    a real question, unlike study plan's graceful skeleton-only fallback.
    """
    from providers.ai import get_ai_provider
    from rag.search import search, format_context

    mastery = await _get_mastery(user_id, course_id, topic)
    difficulty = _difficulty_for(mastery)

    results = await search(topic, course_id, user_id)
    context = format_context(results) or f"Course topic: {topic} (no indexed material found — use general knowledge)"

    avoid = ""
    if exclude_questions:
        avoid = "\nDo NOT repeat these already-asked questions:\n" + "\n".join(
            f"- {q}" for q in exclude_questions[-5:]
        )

    system = (
        "You are an adaptive quiz generator. Generate exactly one multiple-choice "
        "question testing understanding of the given topic, calibrated to the stated "
        "difficulty level. Respond with ONLY valid JSON, no markdown fences, matching "
        'exactly: {"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], '
        '"correct_index": 0, "hint": "a hint that guides without giving away the answer"}'
    )
    user_msg = f"Topic: {topic}\nDifficulty: {difficulty}\n\n{context}{avoid}"

    provider = get_ai_provider()
    raw = await provider.complete(
        messages=[{"role": "user", "content": user_msg}],
        system=system,
        temperature=0.6,
        max_tokens=800,
    )

    try:
        data = json.loads(_strip_json_fences(raw))
    except (json.JSONDecodeError, TypeError):
        logger.warning("Quiz question JSON parse failed, retrying with stricter prompt")
        retry_raw = await provider.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=system + "\n\nIMPORTANT: Output ONLY the JSON object. No prose, no markdown fences.",
            temperature=0.3,
            max_tokens=800,
        )
        data = json.loads(_strip_json_fences(retry_raw))  # let this raise if it still fails

    if not data.get("question") or not isinstance(data.get("options"), list):
        raise ValueError("Malformed question payload from AI")

    return {
        "question": data["question"],
        "options": data["options"],
        "correct_index": int(data.get("correct_index", 0)),
        "hint": data.get("hint", ""),
        "difficulty": difficulty,
        "mastery": mastery,
    }
