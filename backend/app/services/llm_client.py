"""Shared OpenRouter client.

OpenRouter speaks the OpenAI Chat Completions API, so we use the `openai`
SDK pointed at `openrouter_base_url` rather than a provider-specific SDK.
Every LLM call in this app goes through `call_structured`, which forces the
model into a single named function call and returns its parsed arguments —
so callers always get a dict matching their schema, never free text.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from openai import OpenAI

from app.config import get_settings

settings = get_settings()


@lru_cache
def get_client() -> OpenAI:
    """Cached OpenAI-SDK client bound to OpenRouter.

    HTTP-Referer / X-Title are OpenRouter's recommended attribution headers
    (they identify the app on openrouter.ai); both are optional, so we only
    send the ones that are actually configured.
    """
    default_headers: dict[str, str] = {}
    if settings.openrouter_site_url:
        default_headers["HTTP-Referer"] = settings.openrouter_site_url
    if settings.openrouter_app_name:
        default_headers["X-Title"] = settings.openrouter_app_name

    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        default_headers=default_headers or None,
    )


def call_structured(
    system_prompt: str,
    user_content: str,
    tool_name: str,
    tool_description: str,
    json_schema: dict[str, Any],
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """Run one structured completion and return the tool call's arguments.

    `tool_choice` pins the model to `tool_name`, so a response without that
    call means the provider broke the contract — we raise rather than fall
    back to parsing prose.
    """
    client = get_client()

    response = client.chat.completions.create(
        model=settings.openrouter_model,
        max_tokens=max_tokens,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_description,
                    "parameters": json_schema,
                },
            }
        ],
        tool_choice={"type": "function", "function": {"name": tool_name}},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )

    tool_calls = response.choices[0].message.tool_calls or []
    for call in tool_calls:
        if call.function.name == tool_name:
            return json.loads(call.function.arguments)

    raise RuntimeError(f"Model did not return a {tool_name} tool call")
