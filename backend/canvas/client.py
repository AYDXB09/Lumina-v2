"""
Canvas REST API client.

Takes the student's own Canvas API token — every call is scoped to
exactly what that student can see in Canvas. No admin token involved.
"""

import re
from html import unescape
import httpx


class CanvasClient:

    def __init__(self, canvas_url: str, api_token: str):
        self._base = canvas_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_token}"}

    # ---------------------------------------------------------------- #
    # Internal helpers                                                  #
    # ---------------------------------------------------------------- #

    async def _get(self, path: str, params: dict | None = None) -> list | dict:
        """GET with automatic pagination (follows Link: rel=next headers)."""
        url = f"{self._base}/api/v1{path}"
        results = []

        async with httpx.AsyncClient(timeout=20.0) as client:
            while url:
                resp = await client.get(url, headers=self._headers, params=params)
                resp.raise_for_status()
                data = resp.json()

                if isinstance(data, list):
                    results.extend(data)
                else:
                    return data  # single object response

                # Follow pagination
                link = resp.headers.get("Link", "")
                next_url = None
                for part in link.split(","):
                    if 'rel="next"' in part:
                        m = re.search(r"<(.+?)>", part)
                        if m:
                            next_url = m.group(1)
                            break
                url = next_url
                params = None  # params already in paginated URL

        return results

    @staticmethod
    def strip_html(html: str) -> str:
        if not html:
            return ""
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = unescape(clean)
        return re.sub(r"\s+", " ", clean).strip()

    # ---------------------------------------------------------------- #
    # Canvas API calls                                                  #
    # ---------------------------------------------------------------- #

    async def get_self(self) -> dict:
        return await self._get("/users/self")

    async def get_courses(self) -> list[dict]:
        data = await self._get("/courses", {"enrollment_state": "active", "per_page": 100})
        return [
            {
                "canvas_course_id": c["id"],
                "name": c.get("name", "Unnamed Course"),
                "course_code": c.get("course_code", ""),
                "canvas_data": {
                    "start_at": c.get("start_at"),
                    "end_at": c.get("end_at"),
                    "workflow_state": c.get("workflow_state"),
                },
            }
            for c in data
            if isinstance(c, dict) and "id" in c
        ]

    async def get_modules(self, course_id: int) -> list[dict]:
        return await self._get(f"/courses/{course_id}/modules", {"per_page": 100, "include[]": "items"})

    async def get_page(self, course_id: int, page_url: str) -> dict:
        return await self._get(f"/courses/{course_id}/pages/{page_url}")

    async def get_assignments(self, course_id: int) -> list[dict]:
        data = await self._get(f"/courses/{course_id}/assignments", {"per_page": 100})
        return [
            {
                "id": a["id"],
                "name": a.get("name", ""),
                "description": self.strip_html(a.get("description") or ""),
                "due_at": a.get("due_at"),
                "points_possible": a.get("points_possible"),
                "html_url": a.get("html_url", ""),
            }
            for a in data
            if isinstance(a, dict)
        ]

    async def get_announcements(self, course_ids: list[int]) -> list[dict]:
        context_codes = [f"course_{cid}" for cid in course_ids]
        params = {"per_page": 30}
        for code in context_codes:
            params.setdefault("context_codes[]", code)

        # Build query string manually for repeated param
        qs = "&".join(f"context_codes[]={c}" for c in context_codes) + "&per_page=30"
        url = f"{self._base}/api/v1/announcements?{qs}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()

        return [
            {
                "title": a.get("title", ""),
                "message": self.strip_html(a.get("message", "")),
                "posted_at": a.get("posted_at", ""),
                "context_code": a.get("context_code", ""),
            }
            for a in data
            if isinstance(a, dict)
        ]

    async def get_files(self, course_id: int) -> list[dict]:
        data = await self._get(f"/courses/{course_id}/files", {"per_page": 100})
        return [
            {
                "id": f["id"],
                "display_name": f.get("display_name", ""),
                "filename": f.get("filename", ""),
                "content_type": f.get("content-type", ""),
                "size": f.get("size", 0),
                "url": f.get("url", ""),
                "updated_at": f.get("updated_at"),
            }
            for f in data
            if isinstance(f, dict)
        ]
