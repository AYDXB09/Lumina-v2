"""
Canvas routes — course listing and content sync.

GET  /api/canvas/courses          — list student's synced courses
POST /api/canvas/courses/sync     — re-sync from Canvas
GET  /api/canvas/courses/{id}     — single course detail
POST /api/canvas/courses/{id}/index — trigger RAG indexing for a course
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from auth.middleware import get_current_student
from canvas.sync import sync_courses, get_course_content
from db.client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/canvas", tags=["canvas"])


@router.get("/courses")
async def list_courses(user=Depends(get_current_student)):
    """Return courses the student has synced."""
    sb = get_supabase()
    result = sb.table("enrollments").select(
        "course_id, courses(id, canvas_course_id, name, course_code, synced_at)"
    ).eq("user_id", user["sub"]).execute()

    courses = [row["courses"] for row in result.data if row.get("courses")]
    return {"courses": courses}


@router.post("/courses/sync")
async def sync_canvas_courses(
    background_tasks: BackgroundTasks,
    user=Depends(get_current_student),
):
    """
    Pull latest courses from Canvas and upsert into Supabase.
    Returns immediately; indexing happens in background.
    """
    courses = await sync_courses(user["sub"], user["school"])

    # Kick off indexing for each course in background
    for course in courses:
        background_tasks.add_task(
            _index_course_background,
            user["sub"],
            course["canvas_course_id"],
            course["id"],
        )

    return {
        "synced": len(courses),
        "courses": [{"id": c["id"], "name": c["name"]} for c in courses],
        "message": f"Synced {len(courses)} courses. Indexing in background.",
    }


@router.get("/courses/{course_id}")
async def get_course(course_id: str, user=Depends(get_current_student)):
    """Get a single course + its index stats."""
    sb = get_supabase()

    # Verify the student is enrolled
    enroll = sb.table("enrollments").select("course_id").eq(
        "user_id", user["sub"]
    ).eq("course_id", course_id).execute()

    if not enroll.data:
        raise HTTPException(status_code=404, detail="Course not found")

    course = sb.table("courses").select("*").eq("id", course_id).single().execute()
    if not course.data:
        raise HTTPException(status_code=404, detail="Course not found")

    # Chunk count for this course
    chunk_count = sb.table("index_chunks").select(
        "id", count="exact"
    ).eq("course_id", course_id).execute()

    return {
        **course.data,
        "indexed_chunks": chunk_count.count or 0,
    }


@router.post("/courses/{course_id}/index")
async def index_course(
    course_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_student),
):
    """Manually trigger RAG indexing for a course."""
    sb = get_supabase()

    # Get canvas_course_id
    course = sb.table("courses").select("canvas_course_id").eq(
        "id", course_id
    ).single().execute()
    if not course.data:
        raise HTTPException(status_code=404, detail="Course not found")

    background_tasks.add_task(
        _index_course_background,
        user["sub"],
        course.data["canvas_course_id"],
        course_id,
    )

    return {"message": "Indexing started in background"}


# ------------------------------------------------------------------ #
# Background task                                                     #
# ------------------------------------------------------------------ #

async def _index_course_background(
    user_id: str,
    canvas_course_id: str,
    db_course_id: str,
):
    """Fetch Canvas content and index into pgvector."""
    try:
        from rag.indexer import index_course_content
        content = await get_course_content(user_id, int(canvas_course_id))
        await index_course_content(db_course_id, content)
        logger.info("Indexed course %s (%s chunks)", db_course_id, sum(
            len(v) for v in content.values()
        ))
    except Exception as e:
        logger.error("Indexing failed for course %s: %s", db_course_id, e)
