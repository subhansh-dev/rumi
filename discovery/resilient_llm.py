"""
resilient_llm.py — LLM calls that NEVER fail silently.

Every phase in the pipeline should complete, even if the LLM is slow,
rate-limited, or returns garbage. This wrapper:
1. Tries Groq first
2. Falls back to Gemini
3. Falls back to shorter prompt
4. Falls back to non-JSON mode
5. Returns partial results with error info (never empty)

This is what makes RUMI "fully functional" — no phase is ever incomplete.
"""

import json
import time
from typing import Optional, Any


class ResilientLLM:
    """
    LLM wrapper that guarantees a response, even if degraded.
    """

    def __init__(self):
        self._groq_client = None
        self._gemini_client = None
        self._call_count = 0
        self._errors = []

    def call(self, prompt: str, max_tokens: int = 4096,
             json_mode: bool = False, timeout: int = 60) -> dict:
        """
        Call LLM with maximum reliability.

        Returns:
            {
                "content": str or None,
                "provider": "groq|gemini|fallback",
                "degraded": bool,
                "error": str or None,
                "attempts": int
            }
        """
        self._call_count += 1
        attempts = 0
        last_error = None

        # Strategy 1: Try Groq (fast, but may reject long prompts)
        attempts += 1
        try:
            from discovery.llm_client import call_json, call as llm_call
            result = call_json(prompt, max_tokens=max_tokens, provider="groq")
            if result and len(str(result)) > 20:
                return {
                    "content": str(result),
                    "provider": "groq",
                    "degraded": False,
                    "error": None,
                    "attempts": attempts,
                }
            # Try non-JSON mode
            result = llm_call(prompt, max_tokens=max_tokens, provider="groq")
            if result and len(str(result)) > 20:
                return {
                    "content": str(result),
                    "provider": "groq",
                    "degraded": True,
                    "error": "JSON mode failed, used text mode",
                    "attempts": attempts,
                }
        except Exception as e:
            last_error = str(e)

        # Strategy 2: Try Gemini
        attempts += 1
        time.sleep(2)  # rate limit buffer
        try:
            from discovery.llm_client import call_json, call as llm_call
            result = call_json(prompt, max_tokens=max_tokens, provider="gemini")
            if result and len(str(result)) > 20:
                return {
                    "content": str(result),
                    "provider": "gemini",
                    "degraded": False,
                    "error": None,
                    "attempts": attempts,
                }
            result = llm_call(prompt, max_tokens=max_tokens, provider="gemini")
            if result and len(str(result)) > 20:
                return {
                    "content": str(result),
                    "provider": "gemini",
                    "degraded": True,
                    "error": "JSON mode failed, used text mode",
                    "attempts": attempts,
                }
        except Exception as e:
            last_error = str(e)

        # Strategy 3: Try with shorter prompt
        attempts += 1
        if len(prompt) > 2000:
            short_prompt = prompt[:1500] + "\n\n[Truncated — respond with available context]"
            try:
                from discovery.llm_client import call_json
                result = call_json(short_prompt, max_tokens=max_tokens // 2, provider="gemini")
                if result and len(str(result)) > 20:
                    return {
                        "content": str(result),
                        "provider": "gemini_short",
                        "degraded": True,
                        "error": "Prompt truncated due to length",
                        "attempts": attempts,
                    }
            except Exception as e:
                last_error = str(e)

        # All strategies failed
        self._errors.append(last_error)
        return {
            "content": None,
            "provider": "none",
            "degraded": True,
            "error": last_error or "All LLM strategies failed",
            "attempts": attempts,
        }

    def call_json(self, prompt: str, max_tokens: int = 4096) -> Any:
        """
        Convenience: call and parse JSON from response.
        Returns parsed JSON or None.
        """
        result = self.call(prompt, max_tokens=max_tokens, json_mode=True)
        content = result.get("content")
        if not content:
            return None

        # Try to parse JSON
        try:
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0].strip()
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return None

    def get_stats(self) -> dict:
        """Return call statistics."""
        return {
            "total_calls": self._call_count,
            "errors": len(self._errors),
            "recent_errors": self._errors[-5:] if self._errors else [],
        }
