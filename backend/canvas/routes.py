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
    """
    Return courses the student has synced.
    canvas_data is included so the frontend can use account_id and
    weekly_meeting_frequency for extracurricular classification.
    """
    sb = get_supabase()
    result = sb.table("enrollments").select(
        "course_id, courses(id, canvas_course_id, name, course_code, canvas_data, synced_at)"
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


@router.get("/courses/{course_id}/assignments")
async def get_course_assignments(course_id: str, user=Depends(get_current_student)):
    """
    Return unique assignments for a course with FULL descriptions.

    Strategy:
    1. If chunk 0 has metadata.full_description → use that (set by indexer ≥ current version).
    2. Otherwise fall back to stitching all chunks in order, skipping the 100-char overlap
       on each chunk after the first (CHUNK_OVERLAP = 100 in indexer.py).
    """
    sb = get_supabase()

    enroll = sb.table("enrollments").select("course_id").eq(
        "user_id", user["sub"]
    ).eq("course_id", course_id).execute()
    if not enroll.data:
        raise HTTPException(status_code=404, detail="Course not found")

    result = sb.table("index_chunks").select(
        "source_id, content, metadata"
    ).eq("course_id", course_id).eq("source_type", "assignment").execute()

    # Group all chunks by source_id
    groups: dict[str, list] = {}
    for row in result.data:
        sid = row["source_id"]
        groups.setdefault(sid, []).append(row)

    CHUNK_OVERLAP = 100  # must match rag/indexer.py

    assignments = []
    for sid, rows in groups.items():
        # Sort chunks by chunk index
        rows.sort(key=lambda r: (r.get("metadata") or {}).get("chunk", 0))
        first_meta = rows[0].get("metadata") or {}

        # Prefer the full_description stored in chunk 0 (new indexer behaviour)
        full_description = first_meta.get("full_description")

        if not full_description:
            # Legacy: stitch chunks, skipping the overlapping prefix after chunk 0
            parts = [rows[0]["content"]]
            for r in rows[1:]:
                chunk_text = r["content"]
                # Skip the overlap prefix (100 chars) to avoid duplication
                parts.append(chunk_text[CHUNK_OVERLAP:] if len(chunk_text) > CHUNK_OVERLAP else chunk_text)
            full_description = "\n".join(p for p in parts if p.strip())

        assignments.append({
            "id":          sid,
            "title":       first_meta.get("title", "Untitled"),
            "due_at":      first_meta.get("due_at"),
            "url":         first_meta.get("url", ""),
            "description": full_description,
        })

    assignments.sort(key=lambda a: a.get("due_at") or "9999")
    return {"assignments": assignments}


@router.get("/courses/{course_id}/announcements")
async def get_course_announcements(course_id: str, user=Depends(get_current_student)):
    """Return unique announcements for a course (from indexed chunks, chunk 0 only)."""
    sb = get_supabase()

    enroll = sb.table("enrollments").select("course_id").eq(
        "user_id", user["sub"]
    ).eq("course_id", course_id).execute()
    if not enroll.data:
        raise HTTPException(status_code=404, detail="Course not found")

    result = sb.table("index_chunks").select(
        "source_id, content, metadata"
    ).eq("course_id", course_id).eq("source_type", "announcement").execute()

    seen: dict = {}
    for row in result.data:
        sid = row["source_id"]
        chunk_num = (row.get("metadata") or {}).get("chunk", 0)
        if sid not in seen or chunk_num < (seen[sid].get("metadata") or {}).get("chunk", 999):
            seen[sid] = row

    announcements = []
    for row in seen.values():
        meta = row.get("metadata") or {}
        announcements.append({
            "id": row["source_id"],
            "title": meta.get("title", "Untitled"),
            "posted_at": meta.get("posted_at", ""),
            "content": row["content"],
        })

    announcements.sort(key=lambda a: a.get("posted_at") or "", reverse=True)
    return {"announcements": announcements}


@router.get("/courses/{course_id}/quizzes")
async def get_course_quizzes(course_id: str, user=Depends(get_current_student)):
    """
    Return quizzes for a course (from indexed chunks, source_type='quiz').
    Includes Canvas quiz-type exams, timed assessments, and graded surveys.
    is_exam=True items are term tests / final exams.
    """
    sb = get_supabase()

    enroll = sb.table("enrollments").select("course_id").eq(
        "user_id", user["sub"]
    ).eq("course_id", course_id).execute()
    if not enroll.data:
        raise HTTPException(status_code=404, detail="Course not found")

    result = sb.table("index_chunks").select(
        "source_id, content, metadata"
    ).eq("course_id", course_id).eq("source_type", "quiz").execute()

    # Group and deduplicate (keep chunk 0 or full_description)
    groups: dict = {}
    for row in result.data:
        sid = row["source_id"]
        groups.setdefault(sid, []).append(row)

    quizzes = []
    for sid, rows in groups.items():
        rows.sort(key=lambda r: (r.get("metadata") or {}).get("chunk", 0))
        meta = rows[0].get("metadata") or {}
        quizzes.append({
            "id":         sid,
            "title":      meta.get("title", "Untitled"),
            "due_at":     meta.get("due_at"),
            "is_exam":    meta.get("is_exam", False),
            "quiz_type":  meta.get("quiz_type", ""),
            "time_limit": meta.get("time_limit"),
            "points":     meta.get("points"),
            "url":        meta.get("url", ""),
            "description": meta.get("full_description") or rows[0]["content"],
        })

    quizzes.sort(key=lambda q: q.get("due_at") or "9999")
    return {"quizzes": quizzes}


@router.get("/courses/{course_id}/feedback")
async def get_submission_feedback(course_id: str, user=Depends(get_current_student)):
    """
    Return teacher feedback on the student's own submissions for a course.
    Only comments and rubric scores — never the student's own submission content.
    """
    sb = get_supabase()

    enroll = sb.table("enrollments").select("course_id").eq(
        "user_id", user["sub"]
    ).eq("course_id", course_id).execute()
    if not enroll.data:
        raise HTTPException(status_code=404, detail="Course not found")

    result = sb.table("index_chunks").select(
        "source_id, content, metadata"
    ).eq("course_id", course_id).eq("source_type", "submission_feedback").execute()

    feedback = []
    for row in result.data:
        meta = row.get("metadata") or {}
        feedback.append({
            "assignment_id": meta.get("assignment_id"),
            "submitted_at":  meta.get("submitted_at"),
            "score":         meta.get("score"),
            "grade":         meta.get("grade"),
            "feedback_text": row["content"],
        })

    feedback.sort(key=lambda f: f.get("submitted_at") or "", reverse=True)
    return {"feedback": feedback}


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
