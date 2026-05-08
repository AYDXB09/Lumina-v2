"""
Canvas sync — fetch student's courses + content and store in Supabase.

Called on first login (background) and on manual refresh.
Everything is scoped to one student's Canvas token.

Content now includes:
  • Module pages      — lecture notes, readings
  • Assignments       — descriptions + rubric text + is_exam flag
  • Quizzes           — includes Canvas quiz-type exams, timed assessments
  • Announcements
  • Submission feedback — teacher comments on the student's own submissions

Meeting frequency (weekly_meeting_frequency) is stored in courses.canvas_data
and used as a hint for extracurricular classification.
"""

import logging
from datetime import datetime, timezone

from auth.canvas import get_canvas_token
from canvas.client import CanvasClient
from db.client import get_supabase
from config import config

logger = logging.getLogger(__name__)


async def _ensure_canvas_ical(user_id: str, client: CanvasClient) -> None:
    """
    Fetch /users/self/profile → calendar.ics and store it in
    users.calendar_sources as the auto-connected Canvas calendar.
    Only adds the entry if it doesn't already exist.
    """
    sb = get_supabase()
    user_row = sb.table("users").select("calendar_sources").eq("id", user_id).single().execute()
    sources: list = (user_row.data or {}).get("calendar_sources") or []

    # Already has a canvas auto-source
    if any(s.get("id") == "canvas" for s in sources):
        return

    profile = await client.get_profile()
    ical_url = (profile.get("calendar") or {}).get("ics")
    if not ical_url:
        logger.debug("No iCal URL in Canvas profile for user %s", user_id)
        return

    sources.append({
        "id":    "canvas",
        "label": "Canvas Calendar",
        "url":   ical_url,
        "auto":  True,
    })
    sb.table("users").update({"calendar_sources": sources}).eq("id", user_id).execute()
    logger.info("Canvas iCal URL stored for user %s", user_id)


async def sync_courses(user_id: str, school_id: str) -> list[dict]:
    """
    Fetch all active courses from Canvas and upsert into Supabase.
    Also enriches canvas_data with meeting_frequency for each course.
    Auto-discovers the Canvas iCal URL and stores it in users.calendar_sources.
    Returns list of stored course rows (with Supabase IDs).
    """
    token = await get_canvas_token(user_id)
    client = CanvasClient(config.CANVAS_BASE_URL, token)

    # Auto-discover Canvas iCal URL from user profile (first sync only)
    try:
        await _ensure_canvas_ical(user_id, client)
    except Exception as e:
        logger.debug("Canvas iCal discovery skipped: %s", e)

    canvas_courses = await client.get_courses()
    if not canvas_courses:
        return []

    sb = get_supabase()
    stored = []

    for c in canvas_courses:
        # Fetch meeting frequency — lightweight call, used for extracurricular signal
        try:
            meetings = await client.get_course_meetings(int(c["canvas_course_id"]))
            c["canvas_data"].update(meetings)
        except Exception as e:
            logger.debug("Meeting fetch skipped for course %s: %s", c["canvas_course_id"], e)

        result = sb.table("courses").upsert(
            {
                "canvas_course_id": str(c["canvas_course_id"]),
                "school_id": school_id,
                "name": c["name"],
                "course_code": c["course_code"],
                "canvas_data": c["canvas_data"],
                "synced_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="canvas_course_id,school_id",
        ).execute()

        if result.data:
            stored.append(result.data[0])
            sb.table("enrollments").upsert(
                {
                    "user_id": user_id,
                    "course_id": result.data[0]["id"],
                    "canvas_role": "student",
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="user_id,course_id",
            ).execute()

    logger.info("Synced %d courses for user %s", len(stored), user_id)
    return stored


async def get_course_content(
    user_id: str,
    course_id: int,           # Canvas course ID (integer)
) -> dict:
    """
    Fetch all indexable content for a course.

    Returns a dict consumed by rag/indexer.py:
      pages         — module pages
      assignments   — with rubric text and is_exam flag
      quizzes       — Canvas quizzes / timed exams
      announcements
      submissions   — teacher feedback on student's own submissions
    """
    token = await get_canvas_token(user_id)
    client = CanvasClient(config.CANVAS_BASE_URL, token)

    pages         = []
    assignments   = []
    quizzes       = []
    announcements = []
    submissions   = []

    # --- Modules + Pages ---
    try:
        modules = await client.get_modules(course_id)
        for module in modules:
            for item in module.get("items", []):
                if item.get("type") == "Page":
                    page_url = item.get("page_url") or item.get("url", "").split("/")[-1]
                    if page_url:
                        try:
                            page = await client.get_page(course_id, page_url)
                            body = CanvasClient.strip_html(page.get("body") or "")
                            if body:
                                pages.append({
                                    "title":     page.get("title", item.get("title", "")),
                                    "content":   body,
                                    "url":       page.get("html_url", ""),
                                    "canvas_id": page.get("page_id") or page_url,
                                })
                        except Exception as e:
                            logger.debug("Skipping page %s: %s", page_url, e)
    except Exception as e:
        logger.warning("Module fetch failed for course %d: %s", course_id, e)

    # --- Assignments (with rubric) ---
    try:
        raw = await client.get_assignments(course_id)
        for a in raw:
            if a.get("description"):
                assignments.append(a)
    except Exception as e:
        logger.warning("Assignment fetch failed for course %d: %s", course_id, e)

    # --- Quizzes / Canvas Exams ---
    try:
        raw_quizzes = await client.get_quizzes(course_id)
        for q in raw_quizzes:
            if q.get("description") or q.get("title"):
                quizzes.append(q)
    except Exception as e:
        logger.warning("Quiz fetch failed for course %d: %s", course_id, e)

    # --- Announcements ---
    try:
        announcements = await client.get_announcements([course_id])
    except Exception as e:
        logger.warning("Announcement fetch failed for course %d: %s", course_id, e)

    # --- Student's own submission feedback ---
    try:
        submissions = await client.get_student_submissions(course_id)
    except Exception as e:
        logger.warning("Submission fetch failed for course %d: %s", course_id, e)

    return {
        "pages":         pages,
        "assignments":   assignments,
        "quizzes":       quizzes,
        "announcements": announcements,
        "submissions":   submissions,
    }
