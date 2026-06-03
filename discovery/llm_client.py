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
GROQ_MAX_INTERVAL = 3.0  # cap at 3s — don't let TPM calc sleep 20+ seconds

# ── Gemini limits (free tier) ──
GEMINI_TPM = 32000
GEMINI_MIN_INTERVAL = 1.0
GEMINI_MAX_INTERVAL = 3.0


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
    min_interval = min(GROQ_MAX_INTERVAL, max(GROQ_MIN_INTERVAL, (max_tokens / GROQ_TPM) * 60.0))
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_groq_call = time.time()


def _call_groq(prompt: str, json_mode: bool = False,
               max_tokens: int = 4096, temperature: float = 0.3,
               model: str = GROQ_MODEL) -> str | None:
    """Call Groq API using raw requests. Rotates keys on 429."""
    import requests
    global _groq_key_idx
    keys = _get_groq_keys()
    if not keys:
        return None

    # Groq requires the word 'json' in the prompt for json_object mode
    effective_prompt = prompt
    if json_mode and "json" not in prompt.lower():
        effective_prompt = prompt + "\n\nRespond in JSON format."

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": effective_prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    # Try each key on 429 before giving up
    for key_attempt in range(len(keys)):
        key = keys[(_groq_key_idx + key_attempt) % len(keys)]
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        for attempt in range(3):
            _rate_limit_groq(max_tokens)
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers, json=payload, timeout=60,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content and len(content) > 2:
                        _groq_key_idx = (_groq_key_idx + key_attempt) % len(keys)
                        return content.strip()
                elif resp.status_code == 429:
                    # This key is rate-limited — try next key
                    break
                elif resp.status_code in (401, 403):
                    break  # try next key
                elif resp.status_code == 400:
                    # Bad request — don't retry with same payload
                    err_body = resp.text[:200]
                    if "json" in err_body.lower():
                        # Remove json_mode and retry
                        payload.pop("response_format", None)
                        continue
                    return None
            except requests.exceptions.Timeout:
                continue
            except Exception:
                return None

    _groq_key_idx = (_groq_key_idx + 1) % max(1, len(keys))
    return None


# ── Gemini ────────────────────────────────────────────────────────────

_gemini_key_idx = 0


def _rate_limit_gemini(max_tokens: int = 4096):
    global _last_gemini_call
    now = time.time()
    elapsed = now - _last_gemini_call
    min_interval = min(GEMINI_MAX_INTERVAL, max(GEMINI_MIN_INTERVAL, (max_tokens / GEMINI_TPM) * 60.0))
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_gemini_call = time.time()


def _call_gemini(prompt: str, json_mode: bool = False,
                 max_tokens: int = 4096, temperature: float = 0.3,
                 model: str = GEMINI_MODEL) -> str | None:
    """Call Gemini API. Rotates keys on 429."""
    global _gemini_key_idx
    keys = _get_gemini_keys()
    if not keys:
        return None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None

    # Try each key on 429 before giving up
    for key_attempt in range(len(keys)):
        key = keys[(_gemini_key_idx + key_attempt) % len(keys)]

        for attempt in range(2):
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
                    _gemini_key_idx = (_gemini_key_idx + key_attempt) % len(keys)
                    return text.strip()
            except Exception as e:
                err = str(e)
                if "429" in err or "rate" in err.lower() or "quota" in err.lower():
                    # This key exhausted — try next key
                    break
                return None

    _gemini_key_idx = (_gemini_key_idx + 1) % max(1, len(keys))
    return None


# ── Cerebras ──────────────────────────────────────────────────────────

_cerebras_last_call = 0.0

CEREBRAS_MODEL = "gpt-oss-120b"
CEREBRAS_MIN_INTERVAL = 2.0  # 30 req/min free tier


def _get_cerebras_keys() -> list[str]:
    cfg = _load_config()
    key = cfg.get("cerebras_api_key", "")
    return [key] if key else []


def _rate_limit_cerebras():
    global _cerebras_last_call
    now = time.time()
    elapsed = now - _cerebras_last_call
    if elapsed < CEREBRAS_MIN_INTERVAL:
        time.sleep(CEREBRAS_MIN_INTERVAL - elapsed)
    _cerebras_last_call = time.time()


def _call_cerebras(prompt: str, json_mode: bool = False,
                   max_tokens: int = 4096, temperature: float = 0.3,
                   model: str = CEREBRAS_MODEL) -> str | None:
    """Call Cerebras API. OpenAI-compatible endpoint, very fast."""
    import requests
    keys = _get_cerebras_keys()
    if not keys:
        return None

    key = keys[0]
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    effective_prompt = prompt
    if json_mode and "json" not in prompt.lower():
        effective_prompt = prompt + "\n\nRespond in JSON format."

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": effective_prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    _rate_limit_cerebras()
    try:
        resp = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers=headers, json=payload, timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            choice = data.get("choices", [{}])[0].get("message", {})
            content = choice.get("content", "")
            # Cerebras reasoning model may put response in 'reasoning' field
            if not content or len(content) < 3:
                content = choice.get("reasoning", "")
            if content and len(content) > 2:
                return content.strip()
        elif resp.status_code == 429:
            return None  # rate limited
        elif resp.status_code in (401, 403):
            return None  # auth error
        elif resp.status_code == 400:
            # json_mode might not be supported — retry without
            if json_mode:
                payload.pop("response_format", None)
                _rate_limit_cerebras()
                resp2 = requests.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers=headers, json=payload, timeout=30,
                )
                if resp2.status_code == 200:
                    data = resp2.json()
                    choice = data.get("choices", [{}])[0].get("message", {})
                    content = choice.get("content", "")
                    if not content or len(content) < 3:
                        content = choice.get("reasoning", "")
                    if content and len(content) > 2:
                        return content.strip()
            return None
    except Exception:
        return None
    return None


# ── Public API ────────────────────────────────────────────────────────

def call(prompt: str, json_mode: bool = False, max_tokens: int = 4096,
         temperature: float = 0.3, provider: str = "auto") -> str | None:
    """Call with auto-routing. Cerebras (fastest) → Groq → Gemini fallback."""
    if provider == "auto":
        # Cerebras first (fastest free provider), then Groq, then Gemini
        result = _call_cerebras(prompt, json_mode, max_tokens, temperature)
        if result:
            return result
        result = _call_groq(prompt, json_mode, max_tokens, temperature)
        if result:
            return result
        return _call_gemini(prompt, json_mode, max_tokens, temperature)
    if provider == "cerebras":
        return _call_cerebras(prompt, json_mode, max_tokens, temperature)
    if provider == "groq":
        result = _call_groq(prompt, json_mode, max_tokens, temperature)
        if result:
            return result
        # Groq failed — try Cerebras then Gemini
        result = _call_cerebras(prompt, json_mode, max_tokens, temperature)
        if result:
            return result
        return _call_gemini(prompt, json_mode, max_tokens, temperature)
    if provider == "gemini":
        return _call_gemini(prompt, json_mode, max_tokens, temperature)
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
    if provider == "cerebras":
        return bool(_get_cerebras_keys())
    return bool(_get_cerebras_keys()) or bool(_get_groq_keys()) or bool(_get_gemini_keys())


def get_status() -> dict:
    """Return provider availability status."""
    groq_keys = _get_groq_keys()
    gemini_keys = _get_gemini_keys()
    cerebras_keys = _get_cerebras_keys()
    primary = "cerebras" if cerebras_keys else "groq" if groq_keys else "gemini" if gemini_keys else "none"
    return {
        "cerebras": {"available": bool(cerebras_keys), "keys": len(cerebras_keys),
                     "model": CEREBRAS_MODEL},
        "groq": {"available": bool(groq_keys), "keys": len(groq_keys),
                 "model": GROQ_MODEL},
        "gemini": {"available": bool(gemini_keys), "keys": len(gemini_keys),
                   "model": GEMINI_MODEL},
        "primary": primary,
    }
