from __future__ import annotations

import json

from openai import OpenAI

from engram.config import Settings


def complete_json(settings: Settings, system: str, user: str) -> dict | None:
    key = (settings.openai_api_key or "").strip()
    if not key:
        return None
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def complete_text(settings: Settings, system: str, user: str) -> str | None:
    key = (settings.openai_api_key or "").strip()
    if not key:
        return None
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = (response.choices[0].message.content or "").strip()
        return content or None
    except Exception:
        return None
