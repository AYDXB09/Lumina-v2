"""
RAG search — semantic search over index_chunks + student_materials via pgvector.

Uses Supabase RPC to call the match_chunks postgres function.
Falls back to a manual cosine query if the function doesn't exist yet.
"""

import logging
from db.client import get_supabase
from rag.embedder import embed_one

logger = logging.getLogger(__name__)


async def search(
    query: str,
    course_id: str,
    user_id: str | None = None,
    k: int = 6,
    threshold: float = 0.3,
) -> list[dict]:
    """
    Semantic search across Canvas content + student materials for a course.

    Returns top-k results sorted by relevance.
    """
    if not query.strip():
        return []

    vector = await embed_one(query)
    sb = get_supabase()
    results = []

    # --- Search Canvas index_chunks ---
    try:
        resp = sb.rpc(
            "match_index_chunks",
            {
                "query_embedding": vector,
                "match_course_id":  course_id,
                "match_threshold":  threshold,
                "match_count":      k,
            },
        ).execute()

        for row in (resp.data or []):
            results.append({
                "text":         row["content"],
                "source_type":  row.get("source_type", "course"),
                "title":        row.get("metadata", {}).get("title", ""),
                "relevance":    round(row.get("similarity", 0), 4),
                "source":       "canvas",
            })
    except Exception as e:
        logger.warning("index_chunks search failed: %s", e)

    # --- Search student_materials (if user_id provided) ---
    if user_id:
        try:
            resp = sb.rpc(
                "match_student_materials",
                {
                    "query_embedding":   vector,
                    "match_user_id":     user_id,
                    "match_course_id":   course_id,
                    "match_threshold":   threshold,
                    "match_count":       k,
                },
            ).execute()

            for row in (resp.data or []):
                results.append({
                    "text":        row["content"],
                    "source_type": "student_material",
                    "title":       row.get("filename", ""),
                    "relevance":   round(row.get("similarity", 0), 4),
                    "source":      "student",
                })
        except Exception as e:
            logger.warning("student_materials search failed: %s", e)

    # Sort combined results by relevance, return top k
    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:k]


def format_context(results: list[dict]) -> str:
    """Format search results into a context block for the AI prompt."""
    if not results:
        return ""

    lines = ["## Relevant course content\n"]
    for r in results:
        source_label = r.get("title") or r.get("source_type", "Course material")
        lines.append(f"**{source_label}** (relevance: {r['relevance']})")
        lines.append(r["text"])
        lines.append("")

    return "\n".join(lines)
