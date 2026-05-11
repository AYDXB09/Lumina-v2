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

def _clean_messages(messages: list[dict]) -> list[dict]:
    """Strip any extra fields (id, created_at, etc.) — only role + content allowed."""
    return [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") and m.get("content")]


async def _run_openai_compat(
    messages: list[dict],
    executor: ToolExecutor,
    provider,           # K2Provider or OpenRouterProvider instance
    system: str = SYSTEM_PROMPT,
) -> AsyncIterator[str]:

    history = [{"role": "system", "content": system}] + _clean_messages(messages)

    from openai import AsyncOpenAI
    client: AsyncOpenAI = provider._client
    model = provider._model

    # Skip tool loop when:
    # 1. Model doesn't support OpenAI-style function calling (e.g. DeepSeek, Llama)
    # 2. Course context is already injected in system prompt (course_id present)
    #    — avoids extra API calls for common questions
    MODELS_WITHOUT_TOOL_SUPPORT = ("deepseek", "llama")
    model_name = model.lower()
    context_preloaded = "## Assignments in selected course" in system
    tools_supported = (
        not any(m in model_name for m in MODELS_WITHOUT_TOOL_SUPPORT)
        and not context_preloaded
    )

    import time as _time
    import asyncio

    CONNECT_TIMEOUT = 30  # max seconds to wait for API to accept the request
    TOKEN_TIMEOUT   = 60  # max seconds between tokens once streaming starts

    if not tools_supported:
        # Direct stream — no tool loop overhead
        t_api = _time.monotonic()
        try:
            stream = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=history,
                    stream=True,
                    temperature=0.7,
                    max_tokens=4096,
                ),
                timeout=CONNECT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("API connect timeout after %ds (model=%s)", CONNECT_TIMEOUT, model)
            yield _sse("[DONE]")
            return
        except Exception as e:
            logger.error("API connect error (model=%s): %s", model, e)
            yield _sse("[DONE]")
            return

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

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(**kwargs),
                timeout=CONNECT_TIMEOUT,
            )
        except (asyncio.TimeoutError, Exception) as e:
            logger.error("Tool loop error round=%d (model=%s): %s", round_num, model, e)
            yield _sse("[DONE]")
            return
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

            try:
                stream = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        messages=history,
                        stream=True,
                        temperature=0.7,
                        max_tokens=4096,
                    ),
                    timeout=CONNECT_TIMEOUT,
                )
            except (asyncio.TimeoutError, Exception) as e:
                logger.error("Final stream connect error (model=%s): %s", model, e)
                yield _sse("[DONE]")
                return
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

async def _build_system_prompt(user_id: str, course_id: str | None) -> str:
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
    model_name = (
        config.NVIDIA_MODEL     if config.AI_PROVIDER == "nvidia"     else
        config.ANTHROPIC_MODEL  if config.AI_PROVIDER == "anthropic"  else
        config.OPENROUTER_MODEL if config.AI_PROVIDER == "openrouter" else
        config.GROQ_MODEL       if config.AI_PROVIDER == "groq"       else
        config.K2_MODEL
    )
    _no_tool_models = ("deepseek", "llama")
    has_tools = not any(m in model_name.lower() for m in _no_tool_models)
    tool_note = (
        "You have access to tools: get_assignments, get_announcements, search_course_content."
        if has_tools else
        "You do NOT have search or tool capabilities in this session. "
        "Answer only from the course context provided above. "
        "If the answer is not in the loaded context, say so honestly and suggest "
        "the student check Canvas directly or select a specific course for richer answers."
    )
    extra = (
        f"\n\n## System info\n"
        f"Today's date: {today}\n"
        f"Underlying AI model: {model_name}\n"
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
            window_end_date = (now + timedelta(days=90)).date().isoformat()
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

    except Exception as e:
        logger.warning("System prompt build error (non-fatal): %s", e)

    return SYSTEM_PROMPT + extra


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

    # Pre-inject course list — skips get_courses tool call on first turn
    t0 = _time.monotonic()
    system = await _build_system_prompt(user_id, course_id)
    logger.info("system_prompt_build=%.3fs prompt_chars=%d", _time.monotonic() - t0, len(system))

    provider_name = (config.AI_PROVIDER or "k2").lower()

    if provider_name == "anthropic":
        async for chunk in _run_anthropic(messages, executor, provider, system):
            yield chunk
    else:
        # k2, openrouter, nvidia, groq — all OpenAI-compatible
        async for chunk in _run_openai_compat(messages, executor, provider, system):
            yield chunk
