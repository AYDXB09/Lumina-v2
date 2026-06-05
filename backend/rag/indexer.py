"""
RAG Indexer — chunks Canvas content, embeds it, stores in index_chunks (pgvector).

Replaces ChromaDB from the old version.
One row per chunk, with source_type + source_id for provenance.
"""

import logging
from db.client import get_supabase
from rag.embedder import embed

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500    # characters
CHUNK_OVERLAP = 100


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping character chunks."""
    if not text or len(text) <= CHUNK_SIZE:
        return [text] if text.strip() else []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


async def index_course_content(course_id: str, content: dict) -> int:
    """
    Index all Canvas content for a course into pgvector.

    content = {
        "pages":         [{ title, content, url, canvas_id }],
        "assignments":   [{ id, name, description, is_exam, ... }],
        "quizzes":       [{ id, title, description, is_exam, time_limit, ... }],
        "announcements": [{ title, message, posted_at, ... }],
        "submissions":   [{ assignment_id, teacher_comments, rubric_assessment, ... }],
    }

    Returns total chunks stored.
    """
    sb = get_supabase()
    rows = []

    # --- Pages ---
    for page in content.get("pages", []):
        chunks = _chunk_text(page["content"])
        for i, chunk in enumerate(chunks):
            rows.append({
                "course_id":   course_id,
                "source_type": "page",
                "source_id":   str(page["canvas_id"]),
                "content":     chunk,
                "metadata": {
                    "title": page["title"],
                    "url":   page.get("url", ""),
                    "chunk": i,
                },
            })

    # --- Assignments (with rubric text baked into description) ---
    for a in content.get("assignments", []):
        full_text = a["description"] or ""
        chunks = _chunk_text(full_text)
        for i, chunk in enumerate(chunks):
            meta = {
                "title":    a["name"],
                "due_at":   a.get("due_at"),
                "lock_at":  a.get("lock_at"),
                "url":      a.get("html_url", ""),
                "is_exam":  a.get("is_exam", False),
                "points":   a.get("points_possible"),
                "chunk":    i,
            }
            # Store the full description in chunk 0 for O(1) display retrieval
            if i == 0:
                meta["full_description"] = full_text
            rows.append({
                "course_id":   course_id,
                "source_type": "assignment",
                "source_id":   str(a["id"]),
                "content":     chunk,
                "metadata":    meta,
            })

    # --- Quizzes / Canvas Exams ---
    for q in content.get("quizzes", []):
        text = q.get("description") or q.get("title", "")
        if not text.strip():
            continue
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            meta = {
                "title":      q["title"],
                "due_at":     q.get("due_at"),
                "quiz_type":  q.get("quiz_type", ""),
                "time_limit": q.get("time_limit"),   # minutes
                "is_exam":    q.get("is_exam", False),
                "points":     q.get("points_possible"),
                "url":        q.get("html_url", ""),
                "chunk":      i,
            }
            if i == 0:
                meta["full_description"] = text
            rows.append({
                "course_id":   course_id,
                "source_type": "quiz",
                "source_id":   f"quiz_{q['id']}",
                "content":     chunk,
                "metadata":    meta,
            })

    # --- Announcements ---
    for ann in content.get("announcements", []):
        text = f"{ann['title']}\n{ann['message']}".strip()
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            rows.append({
                "course_id":   course_id,
                "source_type": "announcement",
                "source_id":   ann.get("context_code", ""),
                "content":     chunk,
                "metadata": {
                    "title":     ann["title"],
                    "posted_at": ann.get("posted_at", ""),
                    "chunk":     i,
                },
            })

    # --- Submission feedback (teacher comments on student's own work) ---
    for sub in content.get("submissions", []):
        comments = sub.get("teacher_comments") or []
        rubric   = sub.get("rubric_assessment") or {}

        if not comments and not rubric:
            continue

        # Build readable feedback text
        lines = []
        if comments:
            lines.append("Teacher feedback:")
            lines.extend(f"• {c}" for c in comments)
        if rubric:
            lines.append("\nRubric scores:")
            for criterion_id, score_data in rubric.items():
                if isinstance(score_data, dict):
                    pts    = score_data.get("points", "")
                    rating = score_data.get("comments", "")
                    lines.append(f"• {criterion_id}: {pts} pts {('— ' + rating) if rating else ''}")

        feedback_text = "\n".join(lines).strip()
        if not feedback_text:
            continue

        rows.append({
            "course_id":   course_id,
            "source_type": "submission_feedback",
            "source_id":   f"feedback_{sub['assignment_id']}",
            "content":     feedback_text,
            "metadata": {
                "assignment_id": sub["assignment_id"],
                "submitted_at":  sub.get("submitted_at"),
                "score":         sub.get("score"),
                "grade":         sub.get("grade"),
                "chunk":         0,
            },
        })

    if not rows:
        return 0

    # Embed in batches of 64
    BATCH = 64
    total = 0
    for batch_start in range(0, len(rows), BATCH):
        batch = rows[batch_start: batch_start + BATCH]
        texts = [r["content"] for r in batch]
        vectors = await embed(texts)

        for row, vector in zip(batch, vectors):
            row["embedding"] = vector

        # Delete existing chunks for these source_ids before upserting
        source_ids = list({r["source_id"] for r in batch})
        source_types = list({r["source_type"] for r in batch})
        sb.table("index_chunks").delete().eq(
            "course_id", course_id
        ).in_("source_type", source_types).in_("source_id", source_ids).execute()

        sb.table("index_chunks").insert(batch).execute()
        total += len(batch)

    logger.info("Indexed %d chunks for course %s", total, course_id)
    return total


def _build_tag_prefix(metadata: dict) -> str:
    """
    Build a short tag prefix to prepend to chunks before embedding.

    Prepending tags like "Subject: Mathematics | Grade: 8 | Type: exam_paper"
    lets the embedder capture this context in the vector, improving semantic
    retrieval when a query is subject- or grade-specific.

    Returns empty string if no relevant tags are present.
    """
    parts = []
    subjects = metadata.get("subjects") or []
    if subjects:
        parts.append("Subject: " + ", ".join(str(s) for s in subjects))

    grades = metadata.get("grade_levels") or []
    if grades:
        parts.append("Grade: " + ", ".join(str(g) for g in grades))

    doc_type = metadata.get("doc_type")
    if doc_type:
        parts.append("Type: " + doc_type.replace("_", " "))

    return (" | ".join(parts) + "\n\n") if parts else ""


async def index_student_material(
    user_id: str,
    course_id: str,
    filename: str,
    text: str,
    metadata: dict | None = None,
) -> int:
    """
    Index a student-uploaded document (PDF, notes) into pgvector.

    Tags in metadata (subjects, grade_levels, doc_type) are prepended to the
    text of each chunk before embedding so they influence retrieval similarity.
    """
    sb = get_supabase()
    meta = metadata or {}
    chunks = _chunk_text(text)
    if not chunks:
        return 0

    # Build a tag prefix from auto-detected or user-supplied metadata
    tag_prefix = _build_tag_prefix(meta)

    # Embed with prefix (improves semantic retrieval for tagged content)
    embed_texts = [tag_prefix + chunk for chunk in chunks] if tag_prefix else chunks
    vectors = await embed(embed_texts)

    rows = [
        {
            "user_id":   user_id,
            "course_id": course_id,
            "filename":  filename,
            "content":   chunk,           # store original chunk (no prefix) for display
            "embedding": vector,
            "metadata":  {**meta, "chunk": i},
        }
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]

    # Remove old chunks for this file
    sb.table("student_materials").delete().eq(
        "user_id", user_id
    ).eq("filename", filename).execute()

    sb.table("student_materials").insert(rows).execute()
    logger.info(
        "Indexed %d chunks for user=%s file=%s tag_prefix=%r",
        len(rows), user_id, filename, tag_prefix[:60] if tag_prefix else "",
    )
    return len(rows)
