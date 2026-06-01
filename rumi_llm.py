"""
rumi_llm.py — Drop-in LLM helper for all RUMI modules.

Replaces the per-file `from google import genai` + `_generate()` pattern
with a single Groq-first, Gemini-fallback implementation.

Usage (replaces per-file _generate):
    from rumi_llm import generate, generate_json, get_client

    text = generate("gemini-2.5-flash", "Explain X")
    text = generate("gemini-2.5-flash", "Explain X", system="You are a scientist")
"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "api_keys.json"

# ── Model mapping: Gemini model names → Groq equivalents ──
MODEL_MAP = {
    "gemini-2.5-flash": "llama-3.3-70b-versatile",
    "gemini-2.5-flash-lite": "llama-3.3-70b-versatile",
    "gemini-2.5-pro": "llama-3.3-70b-versatile",
}


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _get_groq_keys() -> list[str]:
    cfg = _load_config()
    return [cfg[k] for k in ["groq_api_key", "groq_api_key2"] if cfg.get(k)]


def _get_gemini_keys() -> list[str]:
    cfg = _load_config()
    return [cfg[k] for k in ["gemini_api_key", "gemini_api_key_fallback",
                              "gemini_api_key3", "gemini_api_key4"] if cfg.get(k)]


# ── Singleton clients ──
_groq_client = None
_groq_key_idx = 0
_gemini_client = None
_gemini_key_idx = 0


def _get_groq_client():
    global _groq_client, _groq_key_idx
    keys = _get_groq_keys()
    if not keys:
        return None
    try:
        from groq import Groq
        key = keys[_groq_key_idx % len(keys)]
        _groq_key_idx += 1
        _groq_client = Groq(api_key=key)
        return _groq_client
    except ImportError:
        return None


def _get_gemini_client():
    global _gemini_client, _gemini_key_idx
    keys = _get_gemini_keys()
    if not keys:
        return None
    try:
        from google import genai
        key = keys[_gemini_key_idx % len(keys)]
        _gemini_key_idx += 1
        _gemini_client = genai.Client(api_key=key)
        return _gemini_client
    except ImportError:
        return None


def generate(model_name: str, prompt: str, system: str = "",
             temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """
    Drop-in replacement for per-file _generate() functions.
    Tries Groq first (with model mapping), falls back to Gemini.
    """
    # ── Try Groq ──
    groq_model = MODEL_MAP.get(model_name, "llama-3.3-70b-versatile")
    client = _get_groq_client()
    if client:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = client.chat.completions.create(
                model=groq_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content
            if content and len(content) > 2:
                return content.strip()
        except Exception:
            pass

    # ── Fallback: Gemini ──
    client = _get_gemini_client()
    if client:
        try:
            from google.genai import types
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            resp = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=min(max_tokens, 65536),
                ),
            )
            if resp.text and len(resp.text) > 2:
                return resp.text.strip()
        except Exception:
            pass

    return ""


def generate_json(model_name: str, prompt: str, system: str = "",
                  temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """Generate with JSON response mode."""
    # ── Try Groq ──
    groq_model = MODEL_MAP.get(model_name, "llama-3.3-70b-versatile")
    client = _get_groq_client()
    if client:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = client.chat.completions.create(
                model=groq_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            if content and len(content) > 2:
                return content.strip()
        except Exception:
            pass

    # ── Fallback: Gemini ──
    client = _get_gemini_client()
    if client:
        try:
            from google.genai import types
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            resp = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=min(max_tokens, 65536),
                    response_mime_type="application/json",
                ),
            )
            if resp.text and len(resp.text) > 2:
                return resp.text.strip()
        except Exception:
            pass

    return ""


def get_client():
    """
    Return a genai.Client if available (for modules that need the raw client).
    Prefers Groq, returns None if neither is available.
    """
    return _get_groq_client() or _get_gemini_client()


def get_api_key() -> str:
    """Return first available API key (Gemini preferred for raw client compat)."""
    keys = _get_gemini_keys() or _get_groq_keys()
    return keys[0] if keys else ""


def is_available() -> bool:
    return bool(_get_groq_keys()) or bool(_get_gemini_keys())
