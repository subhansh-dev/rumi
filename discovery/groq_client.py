"""Groq API client for discovery pipeline calls.

Free tier: 14,400 requests/day, 30 req/min, 12,000 TPM.
"""

import json
import time
from pathlib import Path

API_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
_LAST_CALL = 0.0
_LAST_TOKENS = 0  # tokens spent last call (actual + max_tokens reservation)
_TPM_BUDGET = 10000  # Stay under 12K to be safe


def _rate_limit(max_tokens=1024):
    """Respect Groq free tier: 12K TPM. Wait enough for budget to refresh."""
    global _LAST_CALL, _LAST_TOKENS
    now = time.time()
    # The TPM limit charges max_tokens as if they're fully used
    # We need to wait until the budget refreshes
    elapsed = now - _LAST_CALL
    min_interval = max(4.0, (_LAST_TOKENS / _TPM_BUDGET) * 60.0)
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _LAST_CALL = time.time()
    # Actual cost = min(max_tokens, 4096) + prompt_estimate
    _LAST_TOKENS = min(max_tokens, 4096) + 500


def _get_client():
    cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    key = cfg.get("groq_api_key", "")
    if not key:
        return None
    from groq import Groq
    return Groq(api_key=key)


def call(prompt: str, json_mode: bool = False, model: str = DEFAULT_MODEL, temperature: float = 0.3, max_tokens: int = 4096) -> str | None:
    client = _get_client()
    if not client:
        return None

    _rate_limit(max_tokens)

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
