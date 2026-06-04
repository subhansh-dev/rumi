"""
discovery/llm_client.py — Unified LLM Client for RUMI

Cerebras→Groq→Gemini auto-fallback with key rotation.
Drop-in replacement for all LLM calls.

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

# ── Rate limiting with backoff ──
_last_groq_call = 0.0
_last_gemini_call = 0.0
_last_cerebras_call = 0.0
_groq_backoff_until = 0.0
_gemini_backoff_until = 0.0
_cerebras_backoff_until = 0.0

# ── Groq limits (free tier: 30 req/min) ──
GROQ_MIN_INTERVAL = 2.0  # 2s between calls to stay under limits

# ── Gemini limits (free tier: 15 req/min) ──
GEMINI_MIN_INTERVAL = 4.0  # 4s between calls for free tier

# ── Cerebras limits (free tier) ──
CEREBRAS_MIN_INTERVAL = 2.0


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
    global _last_groq_call, _groq_backoff_until
    now = time.time()
    # Check if we're in backoff period
    if now < _groq_backoff_until:
        time.sleep(_groq_backoff_until - now)
    elapsed = time.time() - _last_groq_call
    if elapsed < GROQ_MIN_INTERVAL:
        time.sleep(GROQ_MIN_INTERVAL - elapsed)
    _last_groq_call = time.time()


def _call_groq(prompt: str, json_mode: bool = False,
               max_tokens: int = 4096, temperature: float = 0.3,
               model: str = GROQ_MODEL) -> str | None:
    """Call Groq API using raw requests. Rotates keys on 429."""
    try:
        import requests
    except ImportError:
        return None
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
                    # This key is rate-limited — wait then try next key
                    time.sleep(5)
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
                else:
                    print(f"    [LLM] Groq {resp.status_code}: {resp.text[:100]}", flush=True)
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
    if elapsed < GEMINI_MIN_INTERVAL:
        time.sleep(GEMINI_MIN_INTERVAL - elapsed)
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
                    # This key exhausted — wait then try next key
                    time.sleep(5)
                    break
                elif "401" in err or "403" in err or "invalid" in err.lower():
                    break  # bad key, try next
                else:
                    print(f"    [LLM] Gemini error: {err[:100]}", flush=True)
                return None

    _gemini_key_idx = (_gemini_key_idx + 1) % max(1, len(keys))
    return None


# ── Cerebras ──────────────────────────────────────────────────────────

_cerebras_key_idx = 0
CEREBRAS_MODEL = "gpt-oss-120b"


def _get_cerebras_keys() -> list[str]:
    cfg = _load_config()
    keys = []
    for k in ["cerebras_api_key", "cerebras_api_key2"]:
        v = cfg.get(k, "")
        if v:
            keys.append(v)
    return keys


def _call_cerebras(prompt: str, json_mode: bool = False,
                   max_tokens: int = 4096, temperature: float = 0.3,
                   model: str = CEREBRAS_MODEL) -> str | None:
    """Call Cerebras API. No rate limiting, key rotation on 429."""
    try:
        import requests
    except ImportError:
        return None
    global _cerebras_key_idx
    keys = _get_cerebras_keys()
    if not keys:
        return None

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
        key = keys[(_cerebras_key_idx + key_attempt) % len(keys)]
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers=headers, json=payload, timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                choice = data.get("choices", [{}])[0].get("message", {})
                content = choice.get("content", "")
                if not content or len(content) < 3:
                    content = choice.get("reasoning", "")
                if content and len(content) > 2:
                    _cerebras_key_idx = (_cerebras_key_idx + key_attempt) % len(keys)
                    return content.strip()
            elif resp.status_code == 429:
                time.sleep(5)  # wait before rotating to next key
                continue  # rotate to next key
            elif resp.status_code in (401, 403):
                continue
            elif resp.status_code == 400 and json_mode:
                # json_mode not supported — retry without it
                payload.pop("response_format", None)
                resp2 = requests.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers=headers, json=payload, timeout=60,
                )
                if resp2.status_code == 200:
                    data = resp2.json()
                    choice = data.get("choices", [{}])[0].get("message", {})
                    content = choice.get("content", "")
                    if not content or len(content) < 3:
                        content = choice.get("reasoning", "")
                    if content and len(content) > 2:
                        return content.strip()
            else:
                print(f"    [LLM] Cerebras {resp.status_code}: {resp.text[:100]}", flush=True)
                return None
        except Exception:
            continue

    _cerebras_key_idx = (_cerebras_key_idx + 1) % max(1, len(keys))
    return None


# ── Public API ────────────────────────────────────────────────────────

# Provider cooldown — skip providers that recently failed
_cerebras_cooldown_until = 0.0
_groq_cooldown_until = 0.0
_gemini_cooldown_until = 0.0
COOLDOWN_SECONDS = 30  # skip a provider for 30s after it fails

def call(prompt: str, json_mode: bool = False, max_tokens: int = 4096,
         temperature: float = 0.3, provider: str = "auto") -> str | None:
    """Call with auto-routing. Cerebras (fastest) → Groq → Gemini fallback."""
    global _cerebras_cooldown_until, _groq_cooldown_until, _gemini_cooldown_until
    now = time.time()

    if provider == "auto":
        # Cerebras first (fastest free provider), then Groq, then Gemini
        for attempt in range(2):  # retry once if all in cooldown
            now = time.time()
            if now >= _cerebras_cooldown_until:
                result = _call_cerebras(prompt, json_mode, max_tokens, temperature)
                if result:
                    return result
                _cerebras_cooldown_until = time.time() + COOLDOWN_SECONDS
            if now >= _groq_cooldown_until:
                result = _call_groq(prompt, json_mode, max_tokens, temperature)
                if result:
                    return result
                _groq_cooldown_until = time.time() + COOLDOWN_SECONDS
            if now >= _gemini_cooldown_until:
                result = _call_gemini(prompt, json_mode, max_tokens, temperature)
                if result:
                    return result
                _gemini_cooldown_until = time.time() + COOLDOWN_SECONDS
            # All providers in cooldown — wait for the soonest one
            soonest = min(_cerebras_cooldown_until, _groq_cooldown_until, _gemini_cooldown_until)
            wait = max(0, soonest - time.time())
            if wait > 0 and wait < 60 and attempt == 0:
                print(f"    [LLM] All providers cooling down, waiting {wait:.0f}s...", flush=True)
                time.sleep(wait + 1)
                continue
            break
        return None
    if provider == "cerebras":
        result = _call_cerebras(prompt, json_mode, max_tokens, temperature)
        if result:
            return result
        _cerebras_cooldown_until = time.time() + COOLDOWN_SECONDS
        # Cerebras failed — try Groq then Gemini
        if now >= _groq_cooldown_until:
            result = _call_groq(prompt, json_mode, max_tokens, temperature)
            if result:
                return result
        if now >= _gemini_cooldown_until:
            return _call_gemini(prompt, json_mode, max_tokens, temperature)
        return None
    if provider == "groq":
        result = _call_groq(prompt, json_mode, max_tokens, temperature)
        if result:
            return result
        _groq_cooldown_until = time.time() + COOLDOWN_SECONDS
        # Groq failed — try Cerebras then Gemini
        if now < _cerebras_cooldown_until:
            pass  # skip cerebras
        else:
            result = _call_cerebras(prompt, json_mode, max_tokens, temperature)
            if result:
                return result
        if now < _gemini_cooldown_until:
            pass  # skip gemini
        else:
            return _call_gemini(prompt, json_mode, max_tokens, temperature)
        return None
    if provider == "gemini":
        result = _call_gemini(prompt, json_mode, max_tokens, temperature)
        if not result:
            _gemini_cooldown_until = time.time() + COOLDOWN_SECONDS
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
        result = _call_cerebras(prompt, False, min(max_tokens, 8192), temperature)
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
