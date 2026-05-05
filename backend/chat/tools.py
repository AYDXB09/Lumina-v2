"""
LLM tool definitions and dispatcher for the chat endpoint.

Tools the AI can call:
  get_courses              — list the student's enrolled courses
  get_assignments          — fetch assignments for a course
  get_announcements        — fetch announcements across all courses
  search_course_content    — semantic RAG search over indexed course material
"""

import json
import logging
from canvas.client import CanvasClient
from auth.canvas import get_canvas_token
from rag.search import search, format_context
from config import config

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# OpenAI-compatible tool definitions                                  #
# ------------------------------------------------------------------ #

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_courses",
            "description": "List all active Canvas courses the student is enrolled in. Returns course IDs, names, and codes.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_assignments",
            "description": "Fetch all assignments for a specific course, including names, due dates, point values, and descriptions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "canvas_course_id": {
                        "type": "integer",
                        "description": "The Canvas course ID (from get_courses).",
                    }
                },
                "required": ["canvas_course_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_announcements",
            "description": "Fetch recent teacher announcements across all the student's courses.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_course_content",
            "description": (
                "Semantic search over indexed course materials (lecture notes, pages, assignment descriptions). "
                "Use this when the student asks a conceptual question about course content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                    "canvas_course_id": {
                        "type": "integer",
                        "description": "Narrow search to a specific course (optional).",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# ------------------------------------------------------------------ #
# Tool executor                                                       #
# ------------------------------------------------------------------ #

class ToolExecutor:
    """Stateful executor — holds user context for the lifetime of one chat turn."""

    def __init__(self, user_id: str, school_id: str, course_id: str | None = None):
        self._user_id   = user_id
        self._school_id = school_id
        self._course_id = course_id  # Supabase course UUID if chat is course-scoped
        self._token: str | None = None
        self._courses: list[dict] = []   # cache from get_courses

    async def _get_client(self) -> CanvasClient:
        if not self._token:
            self._token = await get_canvas_token(self._user_id)
        return CanvasClient(config.CANVAS_BASE_URL, self._token)

    async def execute(self, name: str, args: dict) -> str:
        try:
            if name == "get_courses":
                return await self._get_courses()
            elif name == "get_assignments":
                return await self._get_assignments(args.get("canvas_course_id"))
            elif name == "get_announcements":
                return await self._get_announcements()
            elif name == "search_course_content":
                return await self._search(args.get("query", ""), args.get("canvas_course_id"))
            else:
                return json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return json.dumps({"error": f"Tool failed: {str(e)}"})

    async def _get_courses(self) -> str:
        """Read from Supabase (already synced) — fast, no Canvas round trip."""
        from db.client import get_supabase
        sb = get_supabase()
        result = sb.table("enrollments").select(
            "courses(canvas_course_id, name, course_code)"
        ).eq("user_id", self._user_id).execute()

        courses = [
            {
                "canvas_course_id": int(r["courses"]["canvas_course_id"]),
                "name": r["courses"]["name"],
                "course_code": r["courses"]["course_code"],
            }
            for r in result.data if r.get("courses")
        ]
        self._courses = courses
        return json.dumps({"courses": courses})

    async def _get_assignments(self, canvas_course_id: int | None) -> str:
        """
        Check Supabase index_chunks first (fast).
        Fall back to live Canvas call only if not indexed yet.
        """
        if not canvas_course_id:
            return json.dumps({"error": "canvas_course_id required"})

        from db.client import get_supabase
        sb = get_supabase()

        # Find the Supabase course row
        course_row = sb.table("courses").select("id, name").eq(
            "canvas_course_id", str(canvas_course_id)
        ).maybe_single().execute()

        if course_row.data:
            # Pull assignment chunks from index_chunks (already stored)
            chunks = sb.table("index_chunks").select(
                "source_id, metadata, content"
            ).eq("course_id", course_row.data["id"]).eq(
                "source_type", "assignment"
            ).execute()

            if chunks.data:
                # Deduplicate by source_id, return one entry per assignment
                seen = {}
                for c in chunks.data:
                    sid = c["source_id"]
                    if sid not in seen:
                        seen[sid] = {
                            "id": sid,
                            "name": c["metadata"].get("title", ""),
                            "due_at": c["metadata"].get("due_at"),
                            "url": c["metadata"].get("url", ""),
                            "description_preview": c["content"][:200],
                        }
                assignments = list(seen.values())
                return json.dumps({
                    "assignments": assignments,
                    "canvas_course_id": canvas_course_id,
                    "course_name": course_row.data["name"],
                    "source": "cached",
                })

        # Not indexed yet — fall back to live Canvas call
        client = await self._get_client()
        assignments = await client.get_assignments(canvas_course_id)
        return json.dumps({"assignments": assignments, "canvas_course_id": canvas_course_id, "source": "live"})

    async def _get_announcements(self) -> str:
        """Read announcements from index_chunks (fast)."""
        from db.client import get_supabase
        sb = get_supabase()

        # Get all course IDs for this user
        enrollments = sb.table("enrollments").select(
            "course_id"
        ).eq("user_id", self._user_id).execute()

        course_ids = [e["course_id"] for e in enrollments.data]
        if not course_ids:
            return json.dumps({"announcements": [], "message": "No courses found."})

        chunks = sb.table("index_chunks").select(
            "metadata, content"
        ).in_("course_id", course_ids).eq(
            "source_type", "announcement"
        ).order("created_at", desc=True).limit(20).execute()

        if chunks.data:
            announcements = [
                {
                    "title": c["metadata"].get("title", ""),
                    "message": c["content"],
                    "posted_at": c["metadata"].get("posted_at", ""),
                }
                for c in chunks.data
            ]
            return json.dumps({"announcements": announcements, "source": "cached"})

        # Fall back to live Canvas if not indexed
        if not self._courses:
            await self._get_courses()
        course_ids_int = [int(c["canvas_course_id"]) for c in self._courses if c.get("canvas_course_id")]
        if not course_ids_int:
            return json.dumps({"announcements": [], "message": "No active courses found."})
        client = await self._get_client()
        announcements = await client.get_announcements(course_ids_int)
        return json.dumps({"announcements": announcements, "source": "live"})

    async def _search(self, query: str, canvas_course_id: int | None) -> str:
        if not query:
            return json.dumps({"results": [], "message": "Empty query."})

        # Resolve Supabase course_id from canvas_course_id if provided
        target_course_id = self._course_id

        if canvas_course_id and not target_course_id:
            from db.client import get_supabase
            sb = get_supabase()
            row = sb.table("courses").select("id").eq(
                "canvas_course_id", str(canvas_course_id)
            ).maybe_single().execute()
            if row.data:
                target_course_id = row.data["id"]

        if not target_course_id:
            return json.dumps({"results": [], "message": "No course selected for search."})

        results = await search(query, target_course_id, self._user_id)
        if not results:
            return json.dumps({"results": [], "message": "No relevant content found. The course may not be indexed yet."})

        return json.dumps({"results": results, "context": format_context(results)})
