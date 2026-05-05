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
        "assignments":   [{ id, name, description, ... }],
        "announcements": [{ title, message, posted_at, ... }],
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

    # --- Assignments ---
    for a in content.get("assignments", []):
        chunks = _chunk_text(a["description"])
        for i, chunk in enumerate(chunks):
            rows.append({
                "course_id":   course_id,
                "source_type": "assignment",
                "source_id":   str(a["id"]),
                "content":     chunk,
                "metadata": {
                    "title":  a["name"],
                    "due_at": a.get("due_at"),
                    "url":    a.get("html_url", ""),
                    "chunk":  i,
                },
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

    if not rows:
        return 0

    # Embed in batches of 64
    BATCH = 64
    total = 0
    for batch_start in range(0, len(rows), BATCH):
        batch = rows[batch_start: batch_start + BATCH]
        texts = [r["content"] for r in batch]
        vectors = embed(texts)

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


async def index_student_material(
    user_id: str,
    course_id: str,
    filename: str,
    text: str,
    metadata: dict | None = None,
) -> int:
    """Index a student-uploaded document (PDF, notes)."""
    sb = get_supabase()
    chunks = _chunk_text(text)
    if not chunks:
        return 0

    vectors = embed(chunks)

    rows = [
        {
            "user_id":   user_id,
            "course_id": course_id,
            "filename":  filename,
            "content":   chunk,
            "embedding": vector,
            "metadata":  {**(metadata or {}), "chunk": i},
        }
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]

    # Remove old chunks for this file
    sb.table("student_materials").delete().eq(
        "user_id", user_id
    ).eq("filename", filename).execute()

    sb.table("student_materials").insert(rows).execute()
    return len(rows)
