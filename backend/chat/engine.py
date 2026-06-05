"""
Chat engine — runs the tool-call loop then streams the final response.

Supports K2, OpenRouter (OpenAI-compatible tool_calls) and Anthropic
(native tool_use blocks). Provider is picked by AI_PROVIDER env var.

Yields SSE-formatted strings:
  data: {"type": "tool_call", "name": "...", "args": {...}}
  data: {"type": "content", "text": "..."}
  data: [DONE]
"""

import json
import logging
from typing import AsyncIterator

from config import config
from chat.tools import ToolExecutor, TOOL_DEFINITIONS
from chat.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6


async def _aiter_with_timeout(aiter, timeout_secs: float):
    """Wrap an async iterator so each next() call times out independently."""
    import asyncio
    while True:
        try:
            chunk = await asyncio.wait_for(aiter.__anext__(), timeout=timeout_secs)
            yield chunk
        except StopAsyncIteration:
            return


def _sse(payload: dict | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return f"data: {json.dumps(payload)}\n\n"


# ------------------------------------------------------------------ #
# OpenAI-compatible engine (K2 + OpenRouter)                         #
# ------------------------------------------------------------------ #

def _clean_messages(messages: list[dict], max_messages: int = 4) -> list[dict]:
    """Strip extra fields and cap history to avoid token limit errors.
    Keeps the last max_messages turns (always includes the latest user message).
    """
    cleaned = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") and m.get("content")]
    if len(cleaned) > max_messages:
        cleaned = cleaned[-max_messages:]
    return cleaned


async def _run_openai_compat(
    messages: list[dict],
    executor: ToolExecutor,
    provider,           # K2Provider or OpenRouterProvider instance
    system: str = SYSTEM_PROMPT,
    course_id: str | None = None,
) -> AsyncIterator[str]:

    history = [{"role": "system", "content": system}] + _clean_messages(messages)

    from openai import AsyncOpenAI
    client: AsyncOpenAI = provider._client
    model = provider._model

    # Skip tool loop when:
    # 1. Model doesn't support OpenAI-style function calling (e.g. DeepSeek, Llama)
    # 2. Course context is already injected in system prompt (course_id present)
    #    — avoids extra API calls for common questions
    MODELS_WITHOUT_TOOL_SUPPORT = ("deepseek", "llama", "k2")
    model_name = model.lower()
    # Disable tool loop when:
    # 1. Model doesn't support OpenAI function calling (DeepSeek, Llama)
    # 2. A course is selected — context pre-injected into system prompt
    #    (avoids slow non-streaming tool rounds; RAG available via search tool
    #    only when no course is focused)
    # 3. Assignments/quizzes already present in system prompt (legacy check)
    context_preloaded = (
        bool(course_id)
        or "## Assignments in selected course" in system
        or "## Quizzes & Exams in selected course" in system
    )
    tools_supported = (
        not any(m in model_name for m in MODELS_WITHOUT_TOOL_SUPPORT)
        and not context_preloaded
    )

    import time as _time
    import asyncio

    TOKEN_TIMEOUT = 60  # max seconds between tokens once streaming starts

    if not tools_supported:
        # Direct stream — no tool loop overhead
        t_api = _time.monotonic()
        stream = await client.chat.completions.create(
            model=model,
            messages=history,
            stream=True,
            temperature=0.7,
            max_tokens=4096,
        )

        first_token = True
        try:
            async for chunk in _aiter_with_timeout(stream.__aiter__(), TOKEN_TIMEOUT):
                delta = chunk.choices[0].delta.content
                if delta:
                    if first_token:
                        logger.info("ttft=%.3fs model=%s", _time.monotonic() - t_api, model)
                        first_token = False
                    yield _sse({"type": "content", "text": delta})
        except asyncio.TimeoutError:
            logger.error("Stream stalled — no token for %ds (model=%s)", TOKEN_TIMEOUT, model)
        except Exception as e:
            logger.error("Stream error mid-response: %s", e)
        yield _sse("[DONE]")
        return

    # Tool-capable models: run the tool-call loop
    for round_num in range(MAX_TOOL_ROUNDS):
        is_last = round_num == MAX_TOOL_ROUNDS - 1

        kwargs = dict(
            model=model,
            messages=history,
            stream=False,
            temperature=0.7,
            max_tokens=4096,
        )
        if not is_last:
            kwargs["tools"] = TOOL_DEFINITIONS
            kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        if message.tool_calls:
            history.append(message.model_dump(exclude_none=True))

            for tc in message.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)

                yield _sse({"type": "tool_call", "name": name, "args": args})

                result = await executor.execute(name, args)
                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            # Final response — stream it
            history.append({"role": "assistant", "content": message.content})

            stream = await client.chat.completions.create(
                model=model,
                messages=history,
                stream=True,
                temperature=0.7,
                max_tokens=4096,
            )
            try:
                async for chunk in _aiter_with_timeout(stream.__aiter__(), TOKEN_TIMEOUT):
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield _sse({"type": "content", "text": delta})
            except asyncio.TimeoutError:
                logger.error("Stream stalled mid-response (model=%s)", model)
            except Exception as e:
                logger.error("Final stream error (model=%s): %s", model, e)

            yield _sse("[DONE]")
            return

    yield _sse({"type": "content", "text": "I was unable to complete this request. Please try again."})
    yield _sse("[DONE]")


# ------------------------------------------------------------------ #
# Anthropic engine                                                    #
# ------------------------------------------------------------------ #

async def _run_anthropic(
    messages: list[dict],
    executor: ToolExecutor,
    provider,            # AnthropicProvider instance
    system: str = SYSTEM_PROMPT,
) -> AsyncIterator[str]:
    import anthropic

    client: anthropic.AsyncAnthropic = provider._client
    model = provider._model

    # Convert OpenAI tool definitions → Anthropic format
    anthropic_tools = [
        {
            "name": t["function"]["name"],
            "description": t["function"]["description"],
            "input_schema": t["function"]["parameters"],
        }
        for t in TOOL_DEFINITIONS
    ]

    history = _clean_messages(messages)

    for round_num in range(MAX_TOOL_ROUNDS):
        is_last = round_num == MAX_TOOL_ROUNDS - 1

        kwargs = dict(
            model=model,
            system=system,
            messages=history,
            max_tokens=4096,
        )
        if not is_last:
            kwargs["tools"] = anthropic_tools

        response = await client.messages.create(**kwargs)

        # Check for tool_use blocks
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if tool_uses and not is_last:
            # Add assistant turn
            history.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tu in tool_uses:
                yield _sse({"type": "tool_call", "name": tu.name, "args": tu.input})
                result = await executor.execute(tu.name, tu.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result,
                })

            history.append({"role": "user", "content": tool_results})
        else:
            # Stream final text response
            history.append({"role": "assistant", "content": response.content})

            async with client.messages.stream(
                model=model,
                system=system,
                messages=history,
                max_tokens=4096,
            ) as stream:
                async for text in stream.text_stream:
                    yield _sse({"type": "content", "text": text})

            yield _sse("[DONE]")
            return

    yield _sse({"type": "content", "text": "I was unable to complete this request. Please try again."})
    yield _sse("[DONE]")


# ------------------------------------------------------------------ #
# Public entry point                                                  #
# ------------------------------------------------------------------ #

async def _build_system_prompt(user_id: str, course_id: str | None, user_query: str | None = None) -> str:
    """
    Build a rich system prompt by injecting:
    - Current date
    - Enrolled courses
    - Upcoming assignments + quizzes for the selected course
    - Calendar events from cache (never fetches live — avoids blocking the hot path)

    All Supabase queries run in a thread pool and are launched in parallel with
    asyncio.gather to minimise latency before the first AI token.
    """
    import asyncio
    from datetime import datetime, timezone, timedelta
    from db.client import get_supabase

    now   = datetime.now(timezone.utc)
    today = now.strftime("%A, %B %d, %Y")
    from providers.ai import get_active_config as _get_active_config
    _, model_name = _get_active_config()
    _no_tool_models = ("deepseek", "llama")
    has_tools = not any(m in model_name.lower() for m in _no_tool_models)
    tool_note = (
        "You have access to tools: get_assignments, get_announcements, search_course_content."
        if has_tools else
        "You do not have live search tools in this session. "
        "Use the course context provided above when available, and supplement with your training knowledge. "
        "Never refuse to help — always provide the best answer you can."
    )
    extra = (
        f"\n\n## System info\n"
        f"Today's date: {today}\n"
        f"Only mention assignments due AFTER today as 'upcoming'.\n"
        f"{tool_note}\n"
    )

    try:
        sb = get_supabase()

        # ------------------------------------------------------------------
        # Run independent DB reads in parallel (all sync → thread pool)
        # ------------------------------------------------------------------
        def _fetch_enrollments():
            return sb.table("enrollments").select(
                "courses(id, canvas_course_id, name, course_code)"
            ).eq("user_id", user_id).execute()

        def _fetch_chunks():
            # Limit rows fetched — we only need metadata, not embeddings
            return sb.table("index_chunks").select(
                "source_id, metadata, source_type"
            ).eq("course_id", course_id).in_(
                "source_type", ["assignment", "quiz"]
            ).limit(200).execute()

        def _fetch_cal_data():
            # Fetch calendar sources + cached events in two quick calls
            user_row = sb.table("users").select("calendar_sources").eq(
                "id", user_id
            ).single().execute()
            cal_sources = (user_row.data or {}).get("calendar_sources") or []
            if not cal_sources:
                return []
            cal_result = sb.table("calendar_cache").select(
                "source_id, events, label"
            ).eq("user_id", user_id).execute()
            return cal_result.data or []

        # Launch in parallel
        gather_tasks = [asyncio.to_thread(_fetch_enrollments)]
        if course_id:
            gather_tasks.append(asyncio.to_thread(_fetch_chunks))
        else:
            gather_tasks.append(asyncio.sleep(0))          # no-op placeholder
        gather_tasks.append(asyncio.to_thread(_fetch_cal_data))

        results = await asyncio.gather(*gather_tasks, return_exceptions=True)
        enroll_result, chunks_result, cal_rows = results

        # ------------------------------------------------------------------
        # Process enrollments
        # ------------------------------------------------------------------
        if not isinstance(enroll_result, Exception):
            courses = [r["courses"] for r in enroll_result.data if r.get("courses")]
            if courses:
                course_lines = "\n".join(
                    f"- {c['name']} (canvas_course_id: {c['canvas_course_id']})"
                    for c in courses
                )
                extra += f"\n## Student's enrolled courses\n{course_lines}\n"
                # Make the currently selected course explicit
                if course_id:
                    active = next((c for c in courses if str(c.get("id")) == str(course_id)), None)
                    if active:
                        extra += f"\n**Currently active course: {active['name']}** — answer questions in this context unless the student specifies otherwise.\n"

        # ------------------------------------------------------------------
        # Process assignments / quizzes for selected course
        # ------------------------------------------------------------------
        if course_id and not isinstance(chunks_result, Exception) and chunks_result and chunks_result.data:
            assignments_seen: dict = {}
            exams_seen: dict       = {}
            for c in chunks_result.data:
                sid  = c["source_id"]
                meta = c.get("metadata") or {}
                due   = meta.get("due_at", "No due date")
                title = meta.get("title", "Untitled")
                if c["source_type"] == "assignment":
                    if sid not in assignments_seen:
                        tag = " [EXAM]" if meta.get("is_exam") else ""
                        assignments_seen[sid] = f"- {title}{tag} — due: {due}"
                elif c["source_type"] == "quiz":
                    if sid not in exams_seen:
                        tag   = " [EXAM]" if meta.get("is_exam") else " [QUIZ]"
                        timed = f", {meta['time_limit']} min" if meta.get("time_limit") else ""
                        exams_seen[sid] = f"- {title}{tag} — due: {due}{timed}"

            if assignments_seen:
                extra += "\n## Assignments in selected course\n" + "\n".join(assignments_seen.values()) + "\n"
            if exams_seen:
                extra += "\n## Quizzes & Exams in selected course\n" + "\n".join(exams_seen.values()) + "\n"
            if assignments_seen or exams_seen:
                extra += "\nUse this data to answer assignment and exam questions directly without calling tools.\n"

        # ------------------------------------------------------------------
        # Process calendar (cache only — never fetch live here)
        # If cache is empty the AI will still work; calendar syncs separately.
        # ------------------------------------------------------------------
        if not isinstance(cal_rows, Exception) and cal_rows:
            window_end_date = (now + timedelta(days=15)).date().isoformat()
            now_date        = now.date().isoformat()
            all_events = []
            for row in cal_rows:
                cal_label = row.get("label", "Calendar")
                for e in (row.get("events") or []):
                    start_str = e.get("start", "")
                    end_str   = e.get("end", "")
                    if not start_str:
                        continue
                    start_date = start_str[:10]
                    end_date   = end_str[:10] if end_str else start_date
                    if (start_date <= window_end_date) and (end_date >= now_date):
                        e_copy = dict(e)
                        e_copy["_cal"] = cal_label
                        all_events.append(e_copy)

            if all_events:
                all_events.sort(key=lambda e: e.get("start", ""))
                cal_lines = []
                for e in all_events[:40]:   # cap at 40 — enough context, smaller prompt
                    try:
                        start = datetime.fromisoformat(e["start"])
                        end   = datetime.fromisoformat(e["end"])
                        is_multiday = end.date() > start.date()
                        is_all_day  = e.get("all_day", False)
                        if is_multiday:
                            date_str = f"{start.strftime('%a %d %b')}–{end.strftime('%a %d %b')}"
                        else:
                            date_str = start.strftime("%a %d %b")
                        time_str = "all day" if is_all_day else f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
                        loc      = f" @ {e['location']}" if e.get("location") else ""
                        src_tag  = f" [{e['_cal']}]"     if e.get("_cal")      else ""
                        cal_lines.append(f"- {date_str}  {time_str}  {e.get('title','')}{loc}{src_tag}")
                    except Exception:
                        pass
                if cal_lines:
                    extra += "\n## Student's calendar (next 90 days)\n" + "\n".join(cal_lines) + "\n"
                    extra += (
                        "\nIMPORTANT: Multi-day events block ALL days in the range shown."
                        " Do NOT ask the student for their schedule — it is fully loaded above.\n"
                    )

        # ------------------------------------------------------------------
        # Subject-specific prompt injection — economics, maths, physics, etc.
        # Dispatcher lazy-imports only the matching subject module.
        # engine.py never needs to change when new subjects are added.
        # ------------------------------------------------------------------
        if course_id and not isinstance(enroll_result, Exception):
            selected_course = next(
                (r["courses"] for r in enroll_result.data
                 if r.get("courses") and str(r["courses"].get("id")) == str(course_id)),
                None,
            )
            if selected_course:
                from chat.subject_prompts import inject_subject_prompt
                extra = inject_subject_prompt(selected_course.get("name"), extra)

        # ------------------------------------------------------------------
        # Proactive RAG injection — search course content for the user's query
        # and inject top results. Gives the AI actual course material without
        # needing tool calls (which are disabled for Groq/Llama models).
        # Capped at 3 chunks to stay within token budget.
        # ------------------------------------------------------------------
        if course_id and user_query:
            try:
                from rag.search import search as rag_search, format_context
                rag_results = await rag_search(user_query, course_id, user_id, k=3, threshold=0.25)
                if rag_results:
                    extra += "\n" + format_context(rag_results)
            except Exception as e:
                logger.debug("RAG injection skipped: %s", e)

    except Exception as e:
        logger.warning("System prompt build error (non-fatal): %s", e)

    return SYSTEM_PROMPT.replace("{model_name}", model_name) + extra


async def run_chat(
    messages: list[dict],
    user_id: str,
    school_id: str,
    course_id: str | None = None,
) -> AsyncIterator[str]:
    """
    Run the tool-call loop and stream the final response.
    Picks the right engine based on AI_PROVIDER.
    """
    import time as _time
    from providers.ai import get_ai_provider
    provider = get_ai_provider()
    executor = ToolExecutor(user_id, school_id, course_id)

    # Pre-inject course list + proactive RAG for user's query
    t0 = _time.monotonic()
    last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), None)
    system = await _build_system_prompt(user_id, course_id, user_query=last_user_msg)
    logger.info("system_prompt_build=%.3fs prompt_chars=%d", _time.monotonic() - t0, len(system))

    provider_name = (config.AI_PROVIDER or "k2").lower()

    if provider_name == "anthropic":
        async for chunk in _run_anthropic(messages, executor, provider, system):
            yield chunk
    else:
        # k2, openrouter, nvidia, groq — all OpenAI-compatible
        async for chunk in _run_openai_compat(messages, executor, provider, system, course_id):
            yield chunk
