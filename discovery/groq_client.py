"""Groq API client for discovery pipeline calls.

Free tier: 14,400 requests/day, 30 req/min.
"""

import json
import time
from pathlib import Path

API_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 2.0:
        time.sleep(2.0 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _get_client():
    cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    key = cfg.get("groq_api_key", "")
    if not key:
        return None
    from groq import Groq
    return Groq(api_key=key)


def call(prompt: str, json_mode: bool = False, model: str = DEFAULT_MODEL, temperature: float = 0.3, max_tokens: int = 16384) -> str | None:
    client = _get_client()
    if not client:
        return None

    _rate_limit()

    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
    except Exception as e:
        return None


def is_available() -> bool:
    cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    return bool(cfg.get("groq_api_key", ""))
