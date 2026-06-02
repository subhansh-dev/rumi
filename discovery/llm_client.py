"""
discovery/llm_client.py — Unified LLM Client for RUMI

Groq-first, Gemini-fallback. Drop-in replacement for all LLM calls.
Free tier: Groq (14,400 req/day, 30 req/min) + Gemini (1,500 req/day).

Usage:
    from discovery.llm_client import call, call_json, is_available

    text = call("Explain phosphine detection on Venus")
    data = call_json("Generate hypotheses about X", max_tokens=8192)
"""

import json
import time
import random
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"

# ── Defaults ──
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_THINKING_MODEL = "gemini-2.5-flash"  # for complex reasoning

# ── Rate limiting state ──
_last_groq_call = 0.0
_last_gemini_call = 0.0
_groq_tokens_used = 0
_gemini_tokens_used = 0

# ── Groq limits (free tier: 30 req/min, 12000 TPM) ──
GROQ_TPM = 12000
GROQ_MIN_INTERVAL = 0.5  # 30 req/min = 1 per 2s, but 0.5s gives headroom

# ── Gemini limits (free tier) ──
GEMINI_TPM = 32000
GEMINI_MIN_INTERVAL = 1.0


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _get_groq_keys() -> list[str]:
    cfg = _load_config()
    keys = []
    for k in ["groq_api_key", "groq_api_key2"]:
        v = cfg.get(k, "")
        if v:
            keys.append(v)
    return keys


def _get_gemini_keys() -> list[str]:
    cfg = _load_config()
    keys = []
    for k in ["gemini_api_key", "gemini_api_key_fallback", "gemini_api_key3",
              "gemini_api_key4"]:
        v = cfg.get(k, "")
        if v:
            keys.append(v)
    return keys


# ── Groq ──────────────────────────────────────────────────────────────

_groq_key_idx = 0


def _rate_limit_groq(max_tokens: int = 4096):
    global _last_groq_call
    now = time.time()
    elapsed = now - _last_groq_call
    min_interval = max(GROQ_MIN_INTERVAL, (max_tokens / GROQ_TPM) * 60.0)
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_groq_call = time.time()


def _call_groq(prompt: str, json_mode: bool = False,
               max_tokens: int = 4096, temperature: float = 0.3,
               model: str = GROQ_MODEL) -> str | None:
    global _groq_key_idx
    keys = _get_groq_keys()
    if not keys:
        return None

    try:
        from groq import Groq
    except ImportError:
        return None

    key = keys[_groq_key_idx % len(keys)]
    _groq_key_idx += 1
    client = Groq(api_key=key)

    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=30,  # 30 second timeout to prevent hangs
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(3):
        _rate_limit_groq(max_tokens)
        try:
            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content or ""
            if content and len(content) > 2:
                return content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower():
                time.sleep((attempt + 1) * random.uniform(8, 15))
                continue
            # Auth errors (401, 403) — don't retry, fail immediately
            if "401" in err or "403" in err or "unauthorized" in err.lower() or "forbidden" in err.lower():
                return None
            return None
    return None


# ── Gemini ────────────────────────────────────────────────────────────

_gemini_key_idx = 0


def _rate_limit_gemini(max_tokens: int = 4096):
    global _last_gemini_call
    now = time.time()
    elapsed = now - _last_gemini_call
    min_interval = max(GEMINI_MIN_INTERVAL, (max_tokens / GEMINI_TPM) * 60.0)
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_gemini_call = time.time()


def _call_gemini(prompt: str, json_mode: bool = False,
                 max_tokens: int = 4096, temperature: float = 0.3,
                 model: str = GEMINI_MODEL) -> str | None:
    global _gemini_key_idx
    keys = _get_gemini_keys()
    if not keys:
        return None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None

    key = keys[_gemini_key_idx % len(keys)]
    _gemini_key_idx += 1

    for attempt in range(3):
        _rate_limit_gemini(max_tokens)
        try:
            client = genai.Client(api_key=key)
            kwargs = dict(
                temperature=temperature,
                max_output_tokens=min(max_tokens, 65536),
            )
            if json_mode:
                kwargs["response_mime_type"] = "application/json"
            resp = client.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(**kwargs),
            )
            text = resp.text
            if text and len(text) > 2:
                return text.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower() or "quota" in err.lower():
                time.sleep((attempt + 1) * random.uniform(10, 20))
                continue
            return None
    return None


# ── Public API ────────────────────────────────────────────────────────

def call(prompt: str, json_mode: bool = False, max_tokens: int = 4096,
         temperature: float = 0.3, provider: str = "auto") -> str | None:
    """
    Call an LLM. Provider order: Groq -> Gemini (auto mode).
    Set provider='groq' or 'gemini' to force a specific backend.
    """
    import sys as _sys
    if provider == "groq":
        result = _call_groq(prompt, json_mode, max_tokens, temperature)
        if result is None:
            print(f"    [LLM DEBUG] Groq returned None (json_mode={json_mode}, tokens={max_tokens})", file=_sys.stderr, flush=True)
        return result
    if provider == "gemini":
        result = _call_gemini(prompt, json_mode, max_tokens, temperature)
        if result is None:
            print(f"    [LLM DEBUG] Gemini returned None (json_mode={json_mode}, tokens={max_tokens})", file=_sys.stderr, flush=True)
        return result

    # Auto: try Groq first, fallback to Gemini
    result = _call_groq(prompt, json_mode, max_tokens, temperature)
    if result:
        return result

    result = _call_gemini(prompt, json_mode, max_tokens, temperature)
    if result:
        return result

    return None


def call_json(prompt: str, max_tokens: int = 8192,
              temperature: float = 0.3, provider: str = "auto") -> str | None:
    """Call with JSON response mode."""
    return call(prompt, json_mode=True, max_tokens=max_tokens,
                temperature=temperature, provider=provider)


def call_thinking(prompt: str, max_tokens: int = 32768,
                  temperature: float = 0.7, provider: str = "auto") -> str | None:
    """Call with higher token limit for complex reasoning tasks."""
    # For thinking tasks, prefer Gemini's larger context if available
    if provider == "auto":
        result = _call_gemini(prompt, False, max_tokens, temperature,
                              model=GEMINI_THINKING_MODEL)
        if result:
            return result
        return _call_groq(prompt, False, max_tokens, temperature)
    return call(prompt, False, max_tokens, temperature, provider)


def is_available(provider: str = "auto") -> bool:
    """Check if any LLM provider is configured."""
    if provider == "groq":
        return bool(_get_groq_keys())
    if provider == "gemini":
        return bool(_get_gemini_keys())
    return bool(_get_groq_keys()) or bool(_get_gemini_keys())


def get_status() -> dict:
    """Return provider availability status."""
    groq_keys = _get_groq_keys()
    gemini_keys = _get_gemini_keys()
    return {
        "groq": {"available": bool(groq_keys), "keys": len(groq_keys),
                 "model": GROQ_MODEL},
        "gemini": {"available": bool(gemini_keys), "keys": len(gemini_keys),
                   "model": GEMINI_MODEL},
        "primary": "groq" if groq_keys else "gemini" if gemini_keys else "none",
    }
