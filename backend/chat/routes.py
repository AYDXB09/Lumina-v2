"""
Chat routes — SSE streaming chat.

POST /api/chat/stream    — stream a chat response (SSE)
GET  /api/chat/sessions  — list chat sessions for a course
POST /api/chat/sessions  — create a new session
GET  /api/chat/sessions/{id}/messages — load message history
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth.middleware import get_current_student
from chat.engine import run_chat
from db.client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


# ------------------------------------------------------------------ #
# Request models                                                      #
# ------------------------------------------------------------------ #

class ChatRequest(BaseModel):
    messages: list[dict]          # [{ role: "user"|"assistant", content: "..." }]
    session_id: str | None = None
    course_id: str | None = None  # Supabase course UUID (optional scoping)


class NewSessionRequest(BaseModel):
    course_id: str | None = None
    title: str = "New conversation"


# ------------------------------------------------------------------ #
# Streaming chat                                                      #
# ------------------------------------------------------------------ #

@router.post("/stream")
async def chat_stream(body: ChatRequest, user=Depends(get_current_student)):
    """
    SSE streaming endpoint.
    Runs the tool-call loop then streams the final AI response.

    Events:
      data: {"type": "tool_call", "name": "...", "args": {...}}
      data: {"type": "content",   "text": "..."}
      data: [DONE]
    """
    if not body.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    sb = get_supabase()
    session_id = body.session_id

    # Auto-create session if not provided
    if not session_id:
        first_user_msg = next((m["content"] for m in body.messages if m["role"] == "user"), "Chat")
        title = first_user_msg[:60] + ("…" if len(first_user_msg) > 60 else "")
        result = sb.table("chat_sessions").insert({
            "user_id":   user["sub"],
            "course_id": body.course_id,
            "title":     title,
        }).execute()
        session_id = result.data[0]["id"]

    async def event_stream():
        # First event: tell the frontend which session_id to use
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

        full_response = []
        stream_start = time.monotonic()
        try:
            # Heartbeat approach: producer task feeds a queue; consumer yields
            # chunks or ": heartbeat\n\n" every 5s of silence.
            # Using a queue (not asyncio.wait_for on __anext__) avoids
            # coroutine cancellation corrupting the async generator state.
            HEARTBEAT_INTERVAL = 5.0
            _DONE = object()
            queue: asyncio.Queue = asyncio.Queue()

            async def _producer():
                try:
                    async for chunk in run_chat(
                        messages=body.messages,
                        user_id=user["sub"],
                        school_id=user["school"],
                        course_id=body.course_id,
                    ):
                        await queue.put(("chunk", chunk))
                except Exception as exc:
                    await queue.put(("error", exc))
                finally:
                    await queue.put(("done", _DONE))

            producer_task = asyncio.create_task(_producer())
            try:
                while True:
                    try:
                        kind, value = await asyncio.wait_for(
                            queue.get(), timeout=HEARTBEAT_INTERVAL
                        )
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue

                    if kind == "done":
                        break
                    if kind == "error":
                        raise value

                    chunk = value
                    yield chunk
                    try:
                        payload = chunk.replace("data: ", "", 1).strip()
                        if payload and payload != "[DONE]":
                            parsed = json.loads(payload)
                            if parsed.get("type") == "content":
                                full_response.append(parsed["text"])
                    except Exception:
                        pass
            finally:
                producer_task.cancel()

        except Exception as e:
            logger.error("Chat stream error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
            return

        response_ms = int((time.monotonic() - stream_start) * 1000)

        # Persist messages to DB after stream completes
        try:
            # Persist the last user message
            last_user = next(
                (m for m in reversed(body.messages) if m["role"] == "user"), None
            )
            if last_user:
                sb.table("chat_messages").insert({
                    "session_id": session_id,
                    "role":       "user",
                    "content":    last_user["content"],
                }).execute()

            # Persist assistant response — store response_ms in thinking JSONB
            # so the timer badge can be restored when history is reloaded
            if full_response:
                sb.table("chat_messages").insert({
                    "session_id": session_id,
                    "role":       "assistant",
                    "content":    "".join(full_response),
                    "thinking":   {"response_ms": response_ms},
                }).execute()

            # Update session updated_at
            sb.table("chat_sessions").update({
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", session_id).execute()
        except Exception as e:
            logger.warning("Failed to persist chat messages: %s", e)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "Connection":       "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-Id":     session_id or "",
        },
    )


# ------------------------------------------------------------------ #
# Session management                                                  #
# ------------------------------------------------------------------ #

@router.get("/sessions")
async def list_sessions(course_id: str | None = None, user=Depends(get_current_student)):
    sb = get_supabase()
    query = sb.table("chat_sessions").select(
        "id, title, course_id, created_at, updated_at"
    ).eq("user_id", user["sub"]).order("updated_at", desc=True)

    if course_id:
        query = query.eq("course_id", course_id)

    result = query.limit(50).execute()
    return {"sessions": result.data}


@router.post("/sessions")
async def create_session(body: NewSessionRequest, user=Depends(get_current_student)):
    sb = get_supabase()
    result = sb.table("chat_sessions").insert({
        "user_id":   user["sub"],
        "course_id": body.course_id,
        "title":     body.title,
    }).execute()
    return result.data[0]


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, user=Depends(get_current_student)):
    sb = get_supabase()

    # Verify ownership
    session = sb.table("chat_sessions").select("id").eq(
        "id", session_id
    ).eq("user_id", user["sub"]).maybe_single().execute()

    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = sb.table("chat_messages").select(
        "id, role, content, thinking, created_at"
    ).eq("session_id", session_id).order("created_at").execute()

    return {"messages": messages.data}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user=Depends(get_current_student)):
    sb = get_supabase()
    # Verify ownership before deleting
    session = sb.table("chat_sessions").select("id").eq(
        "id", session_id
    ).eq("user_id", user["sub"]).maybe_single().execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")
    sb.table("chat_messages").delete().eq("session_id", session_id).execute()
    sb.table("chat_sessions").delete().eq("id", session_id).execute()
    return {"ok": True}
