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
    for k in ["groq_api_key", "groq_api_key2", "groq_api_key3"]:
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

    # Try each key, with 429 backoff retry on same key
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
                    headers=headers, json=payload, timeout=SLOW_TIMEOUT,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content and len(content) > 2:
                        _groq_key_idx = (_groq_key_idx + key_attempt) % len(keys)
                        return content.strip()
                elif resp.status_code == 429:
                    # Rate limited — backoff and retry SAME key
                    backoff = 10 * (attempt + 1)  # 10s, 20s, 30s
                    time.sleep(backoff)
                    continue  # retry same key, don't break to next
                elif resp.status_code in (401, 403):
                    break  # key is dead, try next key
                elif resp.status_code == 400:
                    err_body = resp.text[:200]
                    if "json" in err_body.lower():
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
                client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=SLOW_TIMEOUT * 1000))
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
    for k in ["cerebras_api_key", "cerebras_api_key2", "cerebras_api_key3", "cerebras_api_key4", "cerebras_api_key5", "cerebras_api_key6"]:
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
                headers=headers, json=payload, timeout=SLOW_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                choice = data.get("choices", [{}])[0].get("message", {})
                content = choice.get("content", "")
                reasoning = choice.get("reasoning", "")
                # gpt-oss-120b is a reasoning model: content=answer, reasoning=thinking
                # Always prefer content (the actual answer), even if short
                if content and content.strip():
                    _cerebras_key_idx = (_cerebras_key_idx + key_attempt) % len(keys)
                    return content.strip()
                # Only fall back to reasoning when content is truly empty
                if reasoning and len(reasoning) > 2:
                    _cerebras_key_idx = (_cerebras_key_idx + key_attempt) % len(keys)
                    return reasoning.strip()
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
                    headers=headers, json=payload, timeout=SLOW_TIMEOUT,
                )
                if resp2.status_code == 200:
                    data = resp2.json()
                    choice = data.get("choices", [{}])[0].get("message", {})
                    content = choice.get("content", "")
                    reasoning = choice.get("reasoning", "")
                    if content and content.strip():
                        return content.strip()
                    if reasoning and len(reasoning) > 2:
                        return reasoning.strip()
            else:
                print(f"    [LLM] Cerebras {resp.status_code}: {resp.text[:100]}", flush=True)
                return None
        except Exception:
            continue

    _cerebras_key_idx = (_cerebras_key_idx + 1) % max(1, len(keys))
    return None





# ── NVIDIA NIM (Nemotron, Kimi, GLM via NVIDIA) ─────────────────────
# To disable: set "nvidia_enabled": false in config/api_keys.json

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def _get_nvidia_config() -> dict:
    cfg = _load_config()
    if not cfg.get("nvidia_enabled", False):
        return {}
    key = cfg.get("nvidia_api_key", "")
    model = cfg.get("nvidia_model", "nvidia/llama-3.1-nemotron-ultra-253b-v1")
    if not key:
        return {}
    return {"key": key, "model": model}


def _call_nvidia(prompt: str, json_mode: bool = False,
                 max_tokens: int = 4096, temperature: float = 0.3) -> str | None:
    """Call NVIDIA NIM API. OpenAI-compatible endpoint."""
    try:
        import requests
    except ImportError:
        return None
    config = _get_nvidia_config()
    if not config:
        return None

    key = config["key"]
    model = config["model"]

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

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    for attempt in range(2):
        try:
            resp = requests.post(
                f"{NVIDIA_BASE_URL}/chat/completions",
                headers=headers, json=payload, timeout=NVIDIA_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and content.strip():
                    return content.strip()
            elif resp.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            elif resp.status_code == 400 and json_mode:
                payload.pop("response_format", None)
                resp2 = requests.post(
                    f"{NVIDIA_BASE_URL}/chat/completions",
                    headers=headers, json=payload, timeout=NVIDIA_TIMEOUT,
                )
                if resp2.status_code == 200:
                    data = resp2.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content and content.strip():
                        return content.strip()
                return None
            else:
                print(f"    [LLM] NVIDIA {resp.status_code}: {resp.text[:100]}", flush=True)
                return None
        except requests.exceptions.Timeout:
            continue
        except Exception:
            return None

    return None


# ── Xiaomi MiMo (via Anthropic-compatible proxy) ─────────────────────
# To disable: set "xiaomi_enabled": false in config/api_keys.json
# To remove:  delete xiaomi_api_key, xiaomi_model, xiaomi_enabled from config
#             and remove this section + _call_xiaomi from call() routing

XIAOMI_BASE_URL = "https://token-plan-sgp.xiaomimimo.com/anthropic"


# ── Kimi K2.6 (via NVIDIA NIM) — best for math reasoning ────────────
# Uses same NVIDIA endpoint but separate key/model
# To disable: set "kimi_enabled": false in config/api_keys.json

def _get_kimi_config() -> dict:
    cfg = _load_config()
    if not cfg.get("kimi_enabled", False):
        return {}
    key = cfg.get("kimi_api_key", "")
    model = cfg.get("kimi_model", "moonshotai/kimi-k2.6")
    if not key:
        return {}
    return {"key": key, "model": model}


def _call_kimi(prompt: str, json_mode: bool = False,
               max_tokens: int = 4096, temperature: float = 0.3) -> str | None:
    """Call Kimi K2.6 via NVIDIA NIM. Best for math/derivation tasks."""
    try:
        import requests
    except ImportError:
        return None
    config = _get_kimi_config()
    if not config:
        return None

    key = config["key"]
    model = config["model"]

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

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    for attempt in range(2):
        try:
            resp = requests.post(
                f"{NVIDIA_BASE_URL}/chat/completions",
                headers=headers, json=payload, timeout=NVIDIA_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and content.strip():
                    return content.strip()
            elif resp.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            elif resp.status_code == 400 and json_mode:
                payload.pop("response_format", None)
                resp2 = requests.post(
                    f"{NVIDIA_BASE_URL}/chat/completions",
                    headers=headers, json=payload, timeout=NVIDIA_TIMEOUT,
                )
                if resp2.status_code == 200:
                    data = resp2.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content and content.strip():
                        return content.strip()
                return None
            else:
                print(f"    [LLM] Kimi {resp.status_code}: {resp.text[:100]}", flush=True)
                return None
        except requests.exceptions.Timeout:
            continue
        except Exception:
            return None

    return None


# ── GLM 5.1 (via NVIDIA NIM) ─────────────────────────────────────────
# To disable: set "glm_enabled": false in config/api_keys.json

def _get_glm_config() -> dict:
    cfg = _load_config()
    if not cfg.get("glm_enabled", False):
        return {}
    key = cfg.get("glm_api_key", "")
    model = cfg.get("glm_model", "zhipu/glm-5.1")
    if not key:
        return {}
    return {"key": key, "model": model}


def _call_glm(prompt: str, json_mode: bool = False,
              max_tokens: int = 4096, temperature: float = 0.3) -> str | None:
    """Call GLM 5.1 via NVIDIA NIM."""
    try:
        import requests
    except ImportError:
        return None
    config = _get_glm_config()
    if not config:
        return None

    key = config["key"]
    model = config["model"]

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

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    for attempt in range(2):
        try:
            resp = requests.post(
                f"{NVIDIA_BASE_URL}/chat/completions",
                headers=headers, json=payload, timeout=NVIDIA_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and content.strip():
                    return content.strip()
            elif resp.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            else:
                print(f"    [LLM] GLM {resp.status_code}: {resp.text[:100]}", flush=True)
                return None
        except requests.exceptions.Timeout:
            continue
        except Exception:
            return None

    return None


# ── Fireworks AI (DeepSeek R1) — best for math reasoning ────────────
# TEMPORARY: $6 credits, will run out
# To disable: set "fireworks_enabled": false in config/api_keys.json

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"


def _get_fireworks_config() -> dict:
    cfg = _load_config()
    if not cfg.get("fireworks_enabled", False):
        return {}
    key = cfg.get("fireworks_api_key", "")
    model = cfg.get("fireworks_model", "accounts/fireworks/models/deepseek-r1")
    if not key:
        return {}
    return {"key": key, "model": model}


def _call_fireworks(prompt: str, json_mode: bool = False,
                    max_tokens: int = 4096, temperature: float = 0.3) -> str | None:
    """Call DeepSeek R1 via Fireworks AI. Best for math/derivation tasks."""
    try:
        import requests
    except ImportError:
        return None
    config = _get_fireworks_config()
    if not config:
        return None

    key = config["key"]
    model = config["model"]

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

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    for attempt in range(2):
        try:
            resp = requests.post(
                f"{FIREWORKS_BASE_URL}/chat/completions",
                headers=headers, json=payload, timeout=NVIDIA_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                choice = data.get("choices", [{}])[0].get("message", {})
                content = choice.get("content", "")
                # DeepSeek R1 may put reasoning in a separate field
                reasoning = choice.get("reasoning_content", "")
                if content and content.strip():
                    return content.strip()
                if reasoning and len(reasoning) > 10:
                    return reasoning.strip()
            elif resp.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            else:
                print(f"    [LLM] Fireworks {resp.status_code}: {resp.text[:100]}", flush=True)
                return None
        except requests.exceptions.Timeout:
            continue
        except Exception:
            return None

    return None


def _get_xiaomi_config() -> dict:
    cfg = _load_config()
    if not cfg.get("xiaomi_enabled", False):
        return {}
    key = cfg.get("xiaomi_api_key", "")
    model = cfg.get("xiaomi_model", "mimo-v2.5-pro")
    if not key:
        return {}
    return {"key": key, "model": model}


def _call_xiaomi(prompt: str, json_mode: bool = False,
                 max_tokens: int = 4096, temperature: float = 0.3) -> str | None:
    """Call Xiaomi MiMo via Anthropic-compatible endpoint."""
    try:
        import requests
    except ImportError:
        return None
    config = _get_xiaomi_config()
    if not config:
        return None

    key = config["key"]
    model = config["model"]

    effective_prompt = prompt
    if json_mode and "json" not in prompt.lower():
        effective_prompt = prompt + "\n\nRespond in JSON format."

    # Anthropic format: POST /v1/messages
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": effective_prompt}],
        "max_tokens": max_tokens,
    }

    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    for attempt in range(2):
        try:
            resp = requests.post(
                f"{XIAOMI_BASE_URL}/v1/messages",
                headers=headers, json=payload, timeout=NVIDIA_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Anthropic format: content is a list of blocks
                content_blocks = data.get("content", [])
                text_parts = []
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                result = "\n".join(text_parts).strip()
                if result:
                    return result
            elif resp.status_code == 429:
                time.sleep(5)
                continue
            else:
                print(f"    [LLM] Xiaomi {resp.status_code}: {resp.text[:100]}", flush=True)
                return None
        except requests.exceptions.Timeout:
            continue
        except Exception:
            return None

    return None


# ── Public API ────────────────────────────────────────────────────────

# Provider cooldown — skip providers that recently failed
_cerebras_cooldown_until = 0.0
_groq_cooldown_until = 0.0
_gemini_cooldown_until = 0.0
COOLDOWN_SECONDS = 15  # skip a provider for 15s after it fails (shorter = more resilient)
NVIDIA_TIMEOUT = 30    # NVIDIA API responds in 5-15s normally; 30s is generous
SLOW_TIMEOUT = 45      # For genuinely slow providers (Fireworks, Xiaomi)

def call(prompt: str, json_mode: bool = False, max_tokens: int = 4096,
         temperature: float = 0.3, provider: str = "auto") -> str | None:
    """Call with auto-routing. Cerebras (fastest) → Groq → Gemini fallback."""
    global _cerebras_cooldown_until, _groq_cooldown_until, _gemini_cooldown_until
    now = time.time()

    if provider == "auto":
        # Primary chain: Cerebras (0.8s) → Groq (0.4s) → Kimi/GLM/DeepSeek (NVIDIA NIM, slow) → Gemini
        # Cerebras and Groq are the fast providers — they should ALWAYS be tried first
        # Kimi, GLM, DeepSeek all go through NVIDIA NIM endpoint (~30-70s each) — fallback only
        MAX_CHAIN_ATTEMPTS = 2
        for chain_attempt in range(MAX_CHAIN_ATTEMPTS):
            # 1. Cerebras (6 keys, ~0.8s — fastest reliable)
            now = time.time()
            if now >= _cerebras_cooldown_until:
                result = _call_cerebras(prompt, json_mode, max_tokens, temperature)
                if result:
                    return result
                _cerebras_cooldown_until = time.time() + COOLDOWN_SECONDS
            # 2. Groq (3 keys, ~0.4s — fastest when available)
            if now >= _groq_cooldown_until:
                result = _call_groq(prompt, json_mode, max_tokens, temperature)
                if result:
                    return result
                _groq_cooldown_until = time.time() + COOLDOWN_SECONDS
            # 3. Gemini (3/4 keys, moderate speed)
            if now >= _gemini_cooldown_until:
                result = _call_gemini(prompt, json_mode, max_tokens, temperature)
                if result:
                    return result
                _gemini_cooldown_until = time.time() + COOLDOWN_SECONDS
            # --- NVIDIA NIM providers (slow, ~30-70s each) ---
            # 4. Kimi K2.6 (via NVIDIA NIM)
            if _get_kimi_config():
                result = _call_kimi(prompt, json_mode, max_tokens, temperature)
                if result:
                    return result
            # 5. GLM slot (Kimi K2.6 on 2nd NVIDIA NIM key)
            if _get_glm_config():
                result = _call_glm(prompt, json_mode, max_tokens, temperature)
                if result:
                    return result
            # 6. DeepSeek V4 Pro (via NVIDIA NIM)
            if _get_nvidia_config():
                result = _call_nvidia(prompt, json_mode, max_tokens, temperature)
                if result:
                    return result
            # All failed — wait for cooldown then retry chain
            if chain_attempt < MAX_CHAIN_ATTEMPTS - 1:
                soonest = min(_cerebras_cooldown_until, _groq_cooldown_until, _gemini_cooldown_until)
                wait = max(0, soonest - time.time())
                if wait > 0 and wait < 60:
                    print(f"    [LLM] All providers failed, retrying chain in {wait:.0f}s (attempt {chain_attempt + 1}/{MAX_CHAIN_ATTEMPTS})...", flush=True)
                    time.sleep(wait + 1)
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
    if provider == "nvidia":
        return _call_nvidia(prompt, json_mode, max_tokens, temperature)
    if provider == "kimi":
        return _call_kimi(prompt, json_mode, max_tokens, temperature)
    if provider == "glm":
        return _call_glm(prompt, json_mode, max_tokens, temperature)
    if provider == "fireworks":
        return _call_fireworks(prompt, json_mode, max_tokens, temperature)
    if provider == "xiaomi":
        return _call_xiaomi(prompt, json_mode, max_tokens, temperature)
    return None


def call_json(prompt: str, max_tokens: int = 8192,
              temperature: float = 0.3, provider: str = "auto") -> str | None:
    """Call with JSON response mode."""
    return call(prompt, json_mode=True, max_tokens=max_tokens,
                temperature=temperature, provider=provider)


def call_math(prompt: str, max_tokens: int = 8192,
              temperature: float = 0.3, json_mode: bool = False) -> str | None:
    """Call with math-optimized routing: DeepSeek V4 Pro → Kimi → Cerebras → general chain.

    Use for: Math Chain (Phase 6.5), Math Engine (Phase 9), derivation tasks.
    DeepSeek V4 Pro (NVIDIA) is strong at mathematical reasoning — primary for equations.
    """
    # Math-optimized chain: reasoning models first
    math_providers = [
        ("nvidia", _get_nvidia_config, _call_nvidia),   # DeepSeek V4 Pro (strong reasoning)
        ("kimi", _get_kimi_config, _call_kimi),         # Kimi K2.6 (good math)
        ("cerebras", None, _call_cerebras),             # Cerebras (fast fallback)
    ]

    for name, get_cfg, call_fn in math_providers:
        if get_cfg is None or get_cfg():
            result = call_fn(prompt, json_mode, max_tokens, temperature)
            if result:
                return result

    # Fallback to general chain (skip providers already tried)
    return call(prompt, json_mode=json_mode, max_tokens=max_tokens, temperature=temperature, provider="auto")


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
    if provider == "nvidia":
        return bool(_get_nvidia_config())
    if provider == "kimi":
        return bool(_get_kimi_config())
    if provider == "glm":
        return bool(_get_glm_config())
    if provider == "fireworks":
        return bool(_get_fireworks_config())
    if provider == "xiaomi":
        return bool(_get_xiaomi_config())
    return bool(_get_nvidia_config()) or bool(_get_kimi_config()) or bool(_get_glm_config()) or bool(_get_fireworks_config()) or bool(_get_xiaomi_config()) or bool(_get_cerebras_keys()) or bool(_get_groq_keys()) or bool(_get_gemini_keys())


def get_status() -> dict:
    """Return provider availability status."""
    groq_keys = _get_groq_keys()
    gemini_keys = _get_gemini_keys()
    cerebras_keys = _get_cerebras_keys()
    nvidia_config = _get_nvidia_config()
    kimi_config = _get_kimi_config()
    glm_config = _get_glm_config()
    fireworks_config = _get_fireworks_config()
    xiaomi_config = _get_xiaomi_config()
    primary = "nvidia" if nvidia_config else "kimi" if kimi_config else "glm" if glm_config else "fireworks" if fireworks_config else "xiaomi" if xiaomi_config else "cerebras" if cerebras_keys else "groq" if groq_keys else "gemini" if gemini_keys else "none"
    return {
        "nvidia": {"available": bool(nvidia_config), "model": nvidia_config.get("model", "N/A")} if nvidia_config else {"available": False},
        "kimi": {"available": bool(kimi_config), "model": kimi_config.get("model", "N/A")} if kimi_config else {"available": False},
        "glm": {"available": bool(glm_config), "model": glm_config.get("model", "N/A")} if glm_config else {"available": False},
        "fireworks": {"available": bool(fireworks_config), "model": fireworks_config.get("model", "N/A")} if fireworks_config else {"available": False},
        "xiaomi": {"available": bool(xiaomi_config), "model": xiaomi_config.get("model", "N/A")} if xiaomi_config else {"available": False},
        "cerebras": {"available": bool(cerebras_keys), "keys": len(cerebras_keys),
                     "model": CEREBRAS_MODEL},
        "groq": {"available": bool(groq_keys), "keys": len(groq_keys),
                 "model": GROQ_MODEL},
        "gemini": {"available": bool(gemini_keys), "keys": len(gemini_keys),
                   "model": GEMINI_MODEL},
        "primary": primary,
    }
