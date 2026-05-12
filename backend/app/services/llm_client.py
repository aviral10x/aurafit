from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import is_secret_configured, settings
from app.services.cost_ledger import capture_response_usage


def openrouter_configured() -> bool:
    return is_secret_configured(settings.openrouter_api_key)


def get_openrouter_client() -> OpenAI:
    headers = {
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name,
    }
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        default_headers=headers,
    )


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


def parse_json_response(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character not in "[{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
            return parsed
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("No JSON object or array found in LLM response", cleaned, 0)


def openrouter_chat_text(
    messages: list[dict[str, Any]],
    *,
    model: str,
    max_tokens: int,
    temperature: float = 0.2,
    operation: str = "llm.chat",
) -> str:
    response = get_openrouter_client().chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    capture_response_usage(
        response,
        operation=operation,
        provider="openrouter",
        model=model,
        details={"max_tokens": max_tokens, "temperature": temperature},
    )
    return content_to_text(response.choices[0].message.content)
