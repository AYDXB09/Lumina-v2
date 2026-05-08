"""
Canvas REST API client.

Scoped entirely to the student's own API token — Lumina never needs
admin credentials. Every call returns only what that student can see.

Methods added in this version
──────────────────────────────
• get_courses()          — now includes account_id for sub-account grouping
• get_assignments()      — includes rubric text + is_exam flag
• get_quizzes()          — Canvas quizzes (assignments that are quiz-type)
• get_course_meetings()  — calendar events → meeting frequency signal
• get_student_submissions() — student's own submissions + teacher comments
"""

import re
from html import unescape
from datetime import datetime, timezone, timedelta
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
        """
        Convert HTML to readable plain text, preserving paragraph and list structure.
        Preserves newlines so assignment descriptions remain readable in the UI.
        """
        if not html:
            return ""
        # Preserve line breaks
        clean = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        # Paragraph/block elements → double newline after closing tag
        clean = re.sub(r"</(p|h[1-6]|div|tr|td|blockquote|section|article)>",
                       "\n\n", clean, flags=re.IGNORECASE)
        # List items → bullet prefix, newline after
        clean = re.sub(r"<li[^>]*>", "• ", clean, flags=re.IGNORECASE)
        clean = re.sub(r"</li>", "\n", clean, flags=re.IGNORECASE)
        # Horizontal rules
        clean = re.sub(r"<hr[^>]*>", "\n\n---\n\n", clean, flags=re.IGNORECASE)
        # Strip all remaining tags
        clean = re.sub(r"<[^>]+>", "", clean)
        clean = unescape(clean)
        # Collapse spaces within a line (but preserve newlines)
        clean = re.sub(r"[^\S\n]+", " ", clean)
        clean = re.sub(r" *\n *", "\n", clean)
        # Max two consecutive newlines
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        return clean.strip()

    @staticmethod
    def _format_rubric(rubric: list) -> str:
        """
        Convert a Canvas rubric array to a human-readable text block.
        Included in the indexed assignment content so the AI can explain
        grading criteria to students.
        """
        if not rubric:
            return ""
        lines = ["Grading Rubric:"]
        for criterion in rubric:
            pts = criterion.get("points", "?")
            desc = criterion.get("description", "")
            long_desc = CanvasClient.strip_html(criterion.get("long_description") or "")
            ratings = criterion.get("ratings") or []
            line = f"• {desc} — {pts} pts"
            if long_desc:
                line += f"\n  {long_desc}"
            if ratings:
                rating_strs = [
                    f"{r.get('description','')} ({r.get('points','')} pts)"
                    for r in ratings
                ]
                line += f"\n  Levels: {' | '.join(rating_strs)}"
            lines.append(line)
        return "\n".join(lines)

    # ---------------------------------------------------------------- #
    # Canvas API calls                                                  #
    # ---------------------------------------------------------------- #

    async def get_self(self) -> dict:
        return await self._get("/users/self")

    async def get_profile(self) -> dict:
        """
        Returns /users/self/profile — includes calendar.ics (personal iCal URL).
        Used to auto-discover the Canvas iCal feed on first sync.
        """
        return await self._get("/users/self/profile")

    async def get_courses(self) -> list[dict]:
        """
        Returns active courses.
        account_id is stored so the frontend can group courses by sub-account —
        the most reliable Canvas-native signal for separating academic vs.
        extra-curricular courses (extra-curriculars are often under a separate
        sub-account in schools that configure Canvas properly).
        """
        data = await self._get("/courses", {"enrollment_state": "active", "per_page": 100})
        return [
            {
                "canvas_course_id": c["id"],
                "name": c.get("name", "Unnamed Course"),
                "course_code": c.get("course_code", ""),
                "canvas_data": {
                    "start_at":     c.get("start_at"),
                    "end_at":       c.get("end_at"),
                    "workflow_state": c.get("workflow_state"),
                    "account_id":   c.get("account_id"),      # sub-account signal
                    "course_format": c.get("course_format"),  # online/blended/on_campus
                    "public_description": c.get("public_description", ""),
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
        """
        Returns assignments with:
        • Full description (HTML stripped, paragraph-structured)
        • Rubric formatted as readable text — appended to description
          so the AI can explain grading criteria to students
        • is_exam flag: True when submission_type is 'none' or 'on_paper'
          (sit-in tests, paper exams, final exams)
        • submission_types — useful for understanding what students submit
        """
        data = await self._get(
            f"/courses/{course_id}/assignments",
            {"per_page": 100, "include[]": "rubric"},
        )
        result = []
        for a in data:
            if not isinstance(a, dict):
                continue

            description = self.strip_html(a.get("description") or "")
            rubric_text = CanvasClient._format_rubric(a.get("rubric") or [])
            if rubric_text:
                description = f"{description}\n\n{rubric_text}" if description else rubric_text

            submission_types = a.get("submission_types") or []
            is_exam = any(t in submission_types for t in ("none", "on_paper", "external_tool"))

            result.append({
                "id":               a["id"],
                "name":             a.get("name", ""),
                "description":      description,
                "due_at":           a.get("due_at"),
                "lock_at":          a.get("lock_at"),
                "points_possible":  a.get("points_possible"),
                "html_url":         a.get("html_url", ""),
                "submission_types": submission_types,
                "is_exam":          is_exam,
                "rubric":           a.get("rubric") or [],
            })
        return result

    async def get_quizzes(self, course_id: int) -> list[dict]:
        """
        Returns Canvas quizzes — these include:
        • Regular quizzes (quiz_type = "assignment")
        • Practice quizzes (quiz_type = "practice_quiz")
        • Graded surveys
        • Term / final exams are often created as quizzes with time_limit set

        is_exam heuristic: quiz_type == "assignment" AND (time_limit is set OR title
        contains exam/test/assessment keywords)
        """
        EXAM_KEYWORDS = ("exam", "test", "assessment", "midterm", "final",
                         "mock", "trial", "summative", "end of term", "end-of-term")
        data = await self._get(f"/courses/{course_id}/quizzes", {"per_page": 100})
        result = []
        for q in data:
            if not isinstance(q, dict):
                continue
            title_lower = (q.get("title") or "").lower()
            is_exam = (
                q.get("time_limit") is not None
                or any(kw in title_lower for kw in EXAM_KEYWORDS)
            )
            result.append({
                "id":              q["id"],
                "title":           q.get("title", ""),
                "description":     self.strip_html(q.get("description") or ""),
                "due_at":          q.get("due_at"),
                "quiz_type":       q.get("quiz_type", ""),
                "time_limit":      q.get("time_limit"),      # minutes, None = unlimited
                "points_possible": q.get("points_possible"),
                "html_url":        q.get("html_url", ""),
                "is_exam":         is_exam,
            })
        return result

    async def get_course_meetings(self, course_id: int) -> dict:
        """
        Fetch calendar events for a course over the next 12 weeks and estimate
        the weekly meeting frequency.  Used as an extracurricular signal:
          • ≥ 2 events/week  → regular scheduled class → likely CORE
          • < 1 event/week   → sporadic/no meetings     → likely EXTRA-CURRICULAR

        NOTE: For fully online schools that run live sessions via Zoom/Meet
        rather than Canvas calendar events, this count may be 0 even for core
        subjects.  Treat as a supplementary hint, not a hard rule.
        """
        now = datetime.now(timezone.utc)
        end = now + timedelta(weeks=12)
        try:
            events = await self._get("/calendar_events", {
                "context_codes[]": f"course_{course_id}",
                "type":            "event",
                "start_date":      now.date().isoformat(),
                "end_date":        end.date().isoformat(),
                "per_page":        100,
            })
            count = len(events) if isinstance(events, list) else 0
            weekly = round(count / 12, 2)
        except Exception:
            count = 0
            weekly = 0.0

        return {
            "event_count_12w": count,
            "weekly_meeting_frequency": weekly,
        }

    async def get_student_submissions(self, course_id: int) -> list[dict]:
        """
        Returns the student's own submissions for all assignments in a course,
        including teacher comments (feedback) and rubric scores.

        API: GET /courses/{id}/students/submissions?student_ids[]=self
             &include[]=submission_comments&include[]=rubric_assessment

        Only teacher/TA comments are included (filtered by author role).
        The student's own submission body is NOT indexed — only feedback.
        This keeps storage lean and privacy boundaries clear.
        """
        try:
            data = await self._get(
                f"/courses/{course_id}/students/submissions",
                {
                    "student_ids[]": "self",
                    "per_page": 100,
                    "include[]": ["submission_comments", "rubric_assessment"],
                },
            )
        except Exception:
            return []

        result = []
        for sub in data:
            if not isinstance(sub, dict):
                continue
            comments = sub.get("submission_comments") or []
            # Filter to teacher/TA comments only (author_id ≠ submission user_id)
            teacher_comments = [
                c.get("comment", "").strip()
                for c in comments
                if isinstance(c, dict)
                and c.get("comment", "").strip()
                and str(c.get("author_id", "")) != str(sub.get("user_id", ""))
            ]
            rubric_assessment = sub.get("rubric_assessment") or {}

            if teacher_comments or rubric_assessment:
                result.append({
                    "assignment_id":    str(sub.get("assignment_id", "")),
                    "submitted_at":     sub.get("submitted_at"),
                    "score":            sub.get("score"),
                    "grade":            sub.get("grade"),
                    "teacher_comments": teacher_comments,
                    "rubric_assessment": rubric_assessment,
                })
        return result

    async def get_announcements(self, course_ids: list[int]) -> list[dict]:
        context_codes = [f"course_{cid}" for cid in course_ids]
        qs = "&".join(f"context_codes[]={c}" for c in context_codes) + "&per_page=30"
        url = f"{self._base}/api/v1/announcements?{qs}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()

        return [
            {
                "title":        a.get("title", ""),
                "message":      self.strip_html(a.get("message", "")),
                "posted_at":    a.get("posted_at", ""),
                "context_code": a.get("context_code", ""),
            }
            for a in data
            if isinstance(a, dict)
        ]

    async def get_files(self, course_id: int) -> list[dict]:
        data = await self._get(f"/courses/{course_id}/files", {"per_page": 100})
        return [
            {
                "id":            f["id"],
                "display_name":  f.get("display_name", ""),
                "filename":      f.get("filename", ""),
                "content_type":  f.get("content-type", ""),
                "size":          f.get("size", 0),
                "url":           f.get("url", ""),
                "updated_at":    f.get("updated_at"),
            }
            for f in data
            if isinstance(f, dict)
        ]
