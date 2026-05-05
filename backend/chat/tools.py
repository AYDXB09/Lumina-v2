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
        client = await self._get_client()
        courses = await client.get_courses()
        self._courses = courses
        return json.dumps({"courses": courses})

    async def _get_assignments(self, canvas_course_id: int | None) -> str:
        if not canvas_course_id:
            return json.dumps({"error": "canvas_course_id required"})
        client = await self._get_client()
        assignments = await client.get_assignments(canvas_course_id)
        return json.dumps({"assignments": assignments, "canvas_course_id": canvas_course_id})

    async def _get_announcements(self) -> str:
        client = await self._get_client()
        # Use cached course IDs or fetch fresh
        if not self._courses:
            self._courses = await client.get_courses()
        course_ids = [int(c["canvas_course_id"]) for c in self._courses if c.get("canvas_course_id")]
        if not course_ids:
            return json.dumps({"announcements": [], "message": "No active courses found."})
        announcements = await client.get_announcements(course_ids)
        return json.dumps({"announcements": announcements})

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
