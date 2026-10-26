"""
Study plan generator.

Cross-course by design: a study plan is only useful if it prioritizes across
everything the student has due, not just the currently-selected course.

Pipeline:
  1. _gather_commitments — pull assignments/quizzes/exams (index_chunks) across
     every enrolled course, plus cached calendar events, into one normalized list.
  2. _build_skeleton — deterministic day-by-day allocation (no AI). Decides WHICH
     days get study sessions for WHICH commitment, and how many. This is plain
     code, not a model decision, so the schedule is always logically sound
     (no exam with zero prep days, no day overloaded, no double-booking).
  3. _fill_content — one AI call (provider-agnostic via provider.complete(),
     works identically across all 6 providers since it doesn't rely on
     tool-calling) that turns the skeleton into actual task text + a plain-
     English "reason" per task, plus a plan-level summary explaining the
     overall prioritization.

Storage: one row per user in study_plans (global plan, not per-course).
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Commitment type weighting — higher = more prep days allocated
TYPE_WEIGHT = {
    "exam": 3,
    "quiz": 2,
    "ia": 3,
    "assignment": 1,
}

MAX_TASKS_PER_DAY = 3
LOOKAHEAD_DAYS = 30  # how far out to plan


# ------------------------------------------------------------------ #
# Step 1 — gather commitments across all enrolled courses             #
# ------------------------------------------------------------------ #

async def _gather_commitments(user_id: str) -> list[dict]:
    from db.client import get_supabase
    sb = get_supabase()

    enrollments = sb.table("enrollments").select(
        "course_id, courses(name)"
    ).eq("user_id", user_id).execute()

    course_map = {
        e["course_id"]: (e.get("courses") or {}).get("name", "Course")
        for e in (enrollments.data or [])
        if e.get("course_id")
    }
    course_ids = list(course_map.keys())
    if not course_ids:
        return []

    chunks = sb.table("index_chunks").select(
        "course_id, source_id, source_type, metadata"
    ).in_("course_id", course_ids).in_(
        "source_type", ["assignment", "quiz"]
    ).execute()

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=LOOKAHEAD_DAYS)

    seen: dict[str, dict] = {}
    for c in (chunks.data or []):
        meta = c.get("metadata") or {}
        due_raw = meta.get("due_at")
        if not due_raw:
            continue
        try:
            due = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if not (now < due <= horizon):
            continue  # only future commitments within the planning window

        sid = c["source_id"]
        if sid in seen:
            continue

        is_exam = bool(meta.get("is_exam"))
        ctype = "exam" if is_exam else c["source_type"]

        seen[sid] = {
            "id": sid,
            "course": course_map.get(c["course_id"], "Course"),
            "title": meta.get("title", "Untitled"),
            "type": ctype,
            "due_at": due.isoformat(),
        }

    return list(seen.values())


async def _gather_calendar_blocked_days(user_id: str) -> set[str]:
    """
    Return a set of ISO date strings (YYYY-MM-DD) that already have an
    all-day personal calendar event, so the skeleton avoids stacking study
    tasks on days the student is already unavailable.
    """
    from db.client import get_supabase
    sb = get_supabase()

    rows = sb.table("calendar_cache").select("events").eq("user_id", user_id).execute()
    blocked = set()
    for row in (rows.data or []):
        for e in (row.get("events") or []):
            if e.get("all_day") and e.get("type") == "personal":
                try:
                    date_str = datetime.fromisoformat(e["start"]).date().isoformat()
                    blocked.add(date_str)
                except (ValueError, KeyError):
                    continue
    return blocked


# ------------------------------------------------------------------ #
# Step 2 — deterministic day-by-day skeleton                          #
# ------------------------------------------------------------------ #

def _sessions_for(commitment: dict, today: datetime) -> int:
    """How many prep sessions a commitment gets, based on urgency + weight."""
    due = datetime.fromisoformat(commitment["due_at"])
    days_until = max(1, (due.date() - today.date()).days)
    weight = TYPE_WEIGHT.get(commitment["type"], 1)
    # Spread sessions across the available runway, capped so we don't
    # over-allocate a single commitment when it's weeks out.
    return max(1, min(days_until, weight * 2))


def _build_skeleton(commitments: list[dict], blocked_days: set[str], today: datetime) -> dict[str, list[dict]]:
    """
    Returns {date_str: [commitment, ...]} — which commitment(s) get worked
    on which day. Task text/reasoning is filled in later by the AI; this
    step only decides placement, so it stays correct even if the AI call
    fails or returns something odd for a slot.
    """
    # Nearest-due + heaviest-weight first, so tight/important commitments
    # claim their slots before looser ones fill in the remaining days.
    ordered = sorted(
        commitments,
        key=lambda c: (
            datetime.fromisoformat(c["due_at"]),
            -TYPE_WEIGHT.get(c["type"], 1),
        ),
    )

    day_buckets: dict[str, list[dict]] = {}

    for commitment in ordered:
        due = datetime.fromisoformat(commitment["due_at"])
        days_until = max(1, (due.date() - today.date()).days)
        n_sessions = _sessions_for(commitment, today)

        # Candidate days: every day between today and due date (exclusive of
        # the due date itself — don't schedule "study" on the day it's due).
        candidates = [
            (today + timedelta(days=i)).date().isoformat()
            for i in range(days_until)
        ]
        candidates = [d for d in candidates if d not in blocked_days]
        if not candidates:
            continue

        # Spread sessions evenly across the candidate runway.
        stride = max(1, len(candidates) // n_sessions)
        chosen = candidates[::stride][:n_sessions]

        for date_str in chosen:
            bucket = day_buckets.setdefault(date_str, [])
            if len(bucket) >= MAX_TASKS_PER_DAY:
                continue  # day is full — commitment loses this slot, keeps its others
            bucket.append(commitment)

    return day_buckets


# ------------------------------------------------------------------ #
# Step 3 — AI fills in task content + reasoning                       #
# ------------------------------------------------------------------ #

def _strip_json_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


async def _fill_content(skeleton: dict[str, list[dict]], commitments: list[dict]) -> dict:
    from providers.ai import get_ai_provider

    if not skeleton:
        return {"summary": "Nothing due in the next 30 days — no plan needed right now.", "days": []}

    commitment_lines = "\n".join(
        f"- {c['course']}: {c['title']} ({c['type']}), due {c['due_at'][:10]}"
        for c in commitments
    )
    skeleton_lines = "\n".join(
        f"{date}: " + ", ".join(f"{c['course']} — {c['title']} ({c['type']})" for c in items)
        for date, items in sorted(skeleton.items())
    )

    system = (
        "You are a study planner. You are given a fixed day-by-day skeleton (which "
        "commitment gets which days — already decided, do not change it) and the full "
        "list of upcoming assignments/exams. Your job is ONLY to write the actual task "
        "content and a short reason for each slot, plus a 2-3 sentence overall summary "
        "explaining your prioritization in plain language the student can understand and "
        "push back on.\n\n"
        "Respond with ONLY valid JSON, no markdown fences, matching exactly this shape:\n"
        '{"summary": "...", "days": [{"date": "YYYY-MM-DD", "tasks": [{"course": "...", '
        '"title": "specific study task, not just the assignment name", "duration_min": 30, '
        '"reason": "short plain-language reason this task/session was placed here"}]}]}'
    )
    user_msg = (
        f"Upcoming commitments:\n{commitment_lines}\n\n"
        f"Fixed day-by-day skeleton (course + commitment per slot):\n{skeleton_lines}\n\n"
        "Fill in specific, useful task titles and reasons for every slot in the skeleton."
    )

    provider = get_ai_provider()
    raw = await provider.complete(
        messages=[{"role": "user", "content": user_msg}],
        system=system,
        temperature=0.4,
        max_tokens=3000,
    )

    for attempt_text in (raw, None):
        text = attempt_text if attempt_text is not None else raw
        try:
            return json.loads(_strip_json_fences(text))
        except (json.JSONDecodeError, TypeError):
            continue

    # Retry once with a stricter instruction if the model returned malformed JSON —
    # weaker models (e.g. via OpenRouter) are more likely to add stray prose.
    logger.warning("Study plan JSON parse failed, retrying with stricter prompt")
    retry_raw = await provider.complete(
        messages=[{"role": "user", "content": user_msg}],
        system=system + "\n\nIMPORTANT: Output ONLY the JSON object. No prose, no markdown fences.",
        temperature=0.2,
        max_tokens=3000,
    )
    try:
        return json.loads(_strip_json_fences(retry_raw))
    except (json.JSONDecodeError, TypeError):
        logger.error("Study plan generation failed after retry — falling back to skeleton-only")
        # Fall back to the deterministic skeleton with generic task text, so the
        # feature degrades gracefully instead of failing outright.
        return {
            "summary": "Generated from your upcoming due dates. (AI task details unavailable — showing raw schedule.)",
            "days": [
                {
                    "date": date,
                    "tasks": [
                        {"course": c["course"], "title": f"Study: {c['title']}", "duration_min": 30, "reason": f"Due {c['due_at'][:10]}"}
                        for c in items
                    ],
                }
                for date, items in sorted(skeleton.items())
            ],
        }


# ------------------------------------------------------------------ #
# Entry point                                                         #
# ------------------------------------------------------------------ #

async def generate_study_plan(user_id: str) -> dict:
    today = datetime.now(timezone.utc)
    commitments = await _gather_commitments(user_id)
    blocked_days = await _gather_calendar_blocked_days(user_id)
    skeleton = _build_skeleton(commitments, blocked_days, today)
    return await _fill_content(skeleton, commitments)
