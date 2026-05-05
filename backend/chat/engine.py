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

async def _run_openai_compat(
    messages: list[dict],
    executor: ToolExecutor,
    provider,           # K2Provider or OpenRouterProvider instance
) -> AsyncIterator[str]:

    history = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    for round_num in range(MAX_TOOL_ROUNDS):
        is_last = round_num == MAX_TOOL_ROUNDS - 1

        # Non-streaming tool resolution rounds
        import openai as _openai_mod
        from openai import AsyncOpenAI

        # Access the underlying client
        client: AsyncOpenAI = provider._client
        model = provider._model

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
            # Add assistant message with tool_calls to history
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

    history = list(messages)

    for round_num in range(MAX_TOOL_ROUNDS):
        is_last = round_num == MAX_TOOL_ROUNDS - 1

        kwargs = dict(
            model=model,
            system=SYSTEM_PROMPT,
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
                system=SYSTEM_PROMPT,
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

    provider_name = (config.AI_PROVIDER or "k2").lower()

    if provider_name == "anthropic":
        async for chunk in _run_anthropic(messages, executor, provider):
            yield chunk
    else:
        async for chunk in _run_openai_compat(messages, executor, provider):
            yield chunk
