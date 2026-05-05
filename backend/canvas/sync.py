"""
Canvas sync — fetch student's courses + content and store in Supabase.

Called on first login (background) and on manual refresh.
Everything is scoped to one student's Canvas token.
"""

import logging
from datetime import datetime, timezone

from auth.canvas import get_canvas_token
from canvas.client import CanvasClient
from db.client import get_supabase
from config import config

logger = logging.getLogger(__name__)


async def sync_courses(user_id: str, school_id: str) -> list[dict]:
    """
    Fetch all active courses from Canvas and upsert into Supabase.
    Returns list of stored course rows (with Supabase IDs).
    """
    token = await get_canvas_token(user_id)
    client = CanvasClient(config.CANVAS_BASE_URL, token)

    canvas_courses = await client.get_courses()
    if not canvas_courses:
        return []

    sb = get_supabase()
    stored = []

    for c in canvas_courses:
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
            # Upsert enrollment
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
    Fetch all indexable content for a course:
      - Module pages (primary lecture notes / readings)
      - Assignments (descriptions)
      - Announcements

    Returns a dict of content lists for the indexer.
    """
    token = await get_canvas_token(user_id)
    client = CanvasClient(config.CANVAS_BASE_URL, token)

    pages = []
    assignments = []
    announcements = []

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
                                    "title": page.get("title", item.get("title", "")),
                                    "content": body,
                                    "url": page.get("html_url", ""),
                                    "canvas_id": page.get("page_id") or page_url,
                                })
                        except Exception as e:
                            logger.debug("Skipping page %s: %s", page_url, e)
    except Exception as e:
        logger.warning("Module fetch failed for course %d: %s", course_id, e)

    # --- Assignments ---
    try:
        raw = await client.get_assignments(course_id)
        for a in raw:
            if a["description"]:
                assignments.append(a)
    except Exception as e:
        logger.warning("Assignment fetch failed for course %d: %s", course_id, e)

    # --- Announcements (pass single course) ---
    try:
        announcements = await client.get_announcements([course_id])
    except Exception as e:
        logger.warning("Announcement fetch failed for course %d: %s", course_id, e)

    return {
        "pages": pages,
        "assignments": assignments,
        "announcements": announcements,
    }
