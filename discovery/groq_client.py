"""Groq API client for discovery pipeline calls.

Free tier: 14,400 requests/day, 30 req/min, 12,000 TPM.
"""

import json
import time
import random
from pathlib import Path

API_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
_LAST_CALL = 0.0
_LAST_TOKENS = 0
_TPM_BUDGET = 11000
_KEY_INDEX = 0


def _get_keys() -> list[str]:
    cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    keys = [cfg.get("groq_api_key", "")]
    extra = cfg.get("groq_api_key2", "")
    if extra:
        keys.append(extra)
    return [k for k in keys if k]


def _rate_limit(max_tokens=4096):
    global _LAST_CALL, _LAST_TOKENS
    now = time.time()
    elapsed = now - _LAST_CALL
    tokens_burned = _LAST_TOKENS
    min_interval = max(2.0, (tokens_burned / _TPM_BUDGET) * 60.0)
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _LAST_CALL = time.time()
    _LAST_TOKENS = min(max_tokens, 4096) + 500


def _get_client():
    global _KEY_INDEX
    keys = _get_keys()
    if not keys:
        return None
    from groq import Groq
    key = keys[_KEY_INDEX % len(keys)]
    _KEY_INDEX += 1
    return Groq(api_key=key)


def call(prompt: str, json_mode: bool = False, model: str = DEFAULT_MODEL,
         temperature: float = 0.3, max_tokens: int = 4096) -> str | None:
    client = _get_client()
    if not client:
        return None

    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(3):
        _rate_limit(max_tokens)
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            if response.usage:
                global _LAST_TOKENS
                _LAST_TOKENS = (response.usage.prompt_tokens or 0) + (response.usage.completion_tokens or 0)
            return content
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower() or "too many" in err_str.lower():
                delay = (attempt + 1) * random.uniform(10, 20)
                time.sleep(delay)
                continue
            return None
    return None


def is_available() -> bool:
    return bool(_get_keys())
