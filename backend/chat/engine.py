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
    # 1. Model doesn't support OpenAI-style function calling (e.g. DeepSeek)
    # 2. Course context is already injected in system prompt (course_id present)
    #    — avoids tripling NVIDIA API calls for common questions
    MODELS_WITHOUT_TOOL_SUPPORT = ("deepseek",)
    model_name = model.lower()
    context_preloaded = "## Assignments in selected course" in system
    tools_supported = (
        not any(m in model_name for m in MODELS_WITHOUT_TOOL_SUPPORT)
        and not context_preloaded
    )

    if not tools_supported:
        # Direct stream — no tool loop overhead
        stream = await client.chat.completions.create(
            model=model,
            messages=history,
            stream=True,
            temperature=0.7,
            max_tokens=4096,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield _sse({"type": "content", "text": delta})
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
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield _sse({"type": "content", "text": delta})

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
    - Current date (so AI filters assignments correctly)
    - Enrolled courses
    - Upcoming assignments for the selected course (avoids tool calls for common queries)
    """
    from datetime import datetime, timezone
    from db.client import get_supabase

    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    model_name = config.NVIDIA_MODEL if config.AI_PROVIDER == "nvidia" else \
                 config.ANTHROPIC_MODEL if config.AI_PROVIDER == "anthropic" else \
                 config.OPENROUTER_MODEL if config.AI_PROVIDER == "openrouter" else \
                 config.K2_MODEL
    extra = f"\n\n## System info\nToday's date: {today}\nUnderlying AI model: {model_name}\nOnly mention assignments due AFTER today as 'upcoming'.\n"

    try:
        sb = get_supabase()

        # Inject enrolled courses
        result = sb.table("enrollments").select(
            "courses(id, canvas_course_id, name, course_code)"
        ).eq("user_id", user_id).execute()

        courses = [r["courses"] for r in result.data if r.get("courses")]
        if courses:
            course_lines = "\n".join(
                f"- {c['name']} (canvas_course_id: {c['canvas_course_id']})"
                for c in courses
            )
            extra += f"\n## Student's enrolled courses\n{course_lines}\n"

        # If a specific course is selected, inject its upcoming assignments
        if course_id:
            chunks = sb.table("index_chunks").select(
                "source_id, metadata, content"
            ).eq("course_id", course_id).eq("source_type", "assignment").execute()

            if chunks.data:
                seen = {}
                for c in chunks.data:
                    sid = c["source_id"]
                    if sid not in seen:
                        due = c["metadata"].get("due_at", "No due date")
                        seen[sid] = f"- {c['metadata'].get('title', 'Untitled')} — due: {due}"
                assignment_lines = "\n".join(seen.values())
                extra += f"\n## Assignments in selected course\n{assignment_lines}\n"
                extra += "\nUse this data to answer assignment questions directly without calling tools.\n"

    except Exception:
        pass

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
    from providers.ai import get_ai_provider
    provider = get_ai_provider()
    executor = ToolExecutor(user_id, school_id, course_id)

    # Pre-inject course list — skips get_courses tool call on first turn
    system = await _build_system_prompt(user_id, course_id)

    provider_name = (config.AI_PROVIDER or "k2").lower()

    if provider_name == "anthropic":
        async for chunk in _run_anthropic(messages, executor, provider, system):
            yield chunk
    else:
        async for chunk in _run_openai_compat(messages, executor, provider, system):
            yield chunk
