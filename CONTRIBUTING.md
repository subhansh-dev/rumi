# Contributing to RUMI

_Thank you for wanting to contribute to RUMI — the autonomous cognitive AI for scientific research._

RUMI is a complex system with 60+ brain modules, 15 Scientist AI modules, 40+ action tools, and a sophisticated cognitive architecture. This guide will help you navigate the codebase and make effective contributions.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Codebase Overview](#codebase-overview)
- [Contribution Types](#contribution-types)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Brain Module Pattern](#brain-module-pattern)
- [Action Tool Pattern](#action-tool-pattern)
- [Testing](#testing)
- [Security](#security)
- [Identity Files](#identity-files)
- [Pull Request Process](#pull-request-process)

---

## Quick Start

```bash
# Clone
git clone https://github.com/subhansh-dev/Rumi
cd Rumi

# Virtual environment
python -m venv rumi_env
rumi_env\Scripts\activate    # Windows
# source rumi_env/bin/activate  # Linux/macOS

# Install
pip install -e .
playwright install chromium

# Run
rumi
```

**Requirements:** Python 3.12+, ~4GB RAM, Gemini API key (get one at [aistudio.google.com](https://aistudio.google.com/app/apikey))

---

## Codebase Overview

```
rumi/
├── main.py              # Entry point — session management, tool registry, LLM integration
├── ui.py                # Terminal UI (Rich + prompt_toolkit)
├── brain/               # 88 files — cognitive systems (memory, reasoning, learning, consciousness)
├── scientist/           # 20 files — Scientist AI modules (discovery, hypothesis, experiments)
├── actions/             # 17 files — tool actions (browser, computer, file, code, search)
├── security/            # 7 files — permission manager, audit, rate limiting
├── skills/              # 15 files — skill engine (research, documents, planning, reflection)
├── agent/               # 4 files — task queue, executor, planner, error handler
├── agents/              # Agent persona definitions (engineering, testing, design, specialized)
├── config/              # Configuration files (api_keys, consent, target guard)
├── memory/              # Persistent file-based memory
├── core/prompt.txt      # System prompt
└── assets/              # Images, demos
```

### Key Architecture Decisions

- **Brain modules** follow a singleton pattern with `get_*()` factory functions
- **Thread safety** via `threading.RLock()` for all state access
- **Graceful degradation** — all imports wrapped in try/except, modules can fail independently
- **File-based state** — brain modules persist to JSON files in `brain/` directory
- **Tool registry** — functions registered via `@register_tool("name")` decorator
- **Gemini Live API** — real-time audio/text streaming for voice interaction

---

## Contribution Types

### 1. New Scientist AI Modules

The most valuable contributions extend RUMI's scientific research capabilities:

- **Discovery pipeline stages**: New stages in the idea → experiment → paper lifecycle
- **Domain-specific modules**: Physics, biology, chemistry, neuroscience research tools
- **Data analysis integrations**: Connect to scientific databases, APIs, or computation frameworks
- **Visualization**: Scientific charting, knowledge graph visualization, experiment dashboards
- **Literature tools**: Citation management, systematic review automation, meta-analysis

### 2. New Brain Modules

Each brain module follows the standard singleton pattern (see below):

- **Memory systems**: New memory types (e.g., semantic memory, spatial memory)
- **Reasoning strategies**: Additional reasoning frameworks
- **Learning algorithms**: New learning paradigms
- **Consciousness metrics**: Enhanced phi computation, awareness tracking

### 3. New Action Tools

Tools are registered via `@register_tool("tool_name")` decorator in `main.py`:

- **Research tools**: Scientific database queries, experiment runners, paper analyzers
- **System tools**: Additional computer control or automation capabilities
- **Integration tools**: Connect to external APIs, services, or hardware

### 4. Improvements to Existing Systems

- **Optimization**: Performance improvements to brain modules or actions
- **Bug fixes**: Error handling, edge cases, race conditions
- **Documentation**: Better docstrings, type hints, README updates
- **Testing**: Unit tests, integration tests, regression tests

---

## Development Workflow

### Step 1 — Choose an Issue

Check [open issues](https://github.com/subhansh-dev/Rumi/issues) or propose a new one. For significant changes, open an issue first to discuss.

### Step 2 — Fork & Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### Step 3 — Make Changes

Follow the code patterns below. Keep changes focused on one concern.

### Step 4 — Test

```bash
# Verify RUMI starts
python rumi_launcher.py

# Check that your module loads without errors
python -c "from brain.your_module import get_your_module; m = get_your_module(); print(m.get_stats())"
```

### Step 5 — Commit

```bash
git add -A
git commit -m "module: brief description of change"
```

Commit message format:
- `brain: add associative memory spreading activation`
- `scientist: fix novelty checker API timeout`
- `actions: add paper_search tool`
- `security: update permission manager risk levels`
- `docs: update CONTRIBUTING.md`

### Step 6 — Push & PR

```bash
git push origin feature/your-feature
# Open a Pull Request on GitHub
```

---

## Code Standards

### Python

- **Target**: Python 3.12+ — use modern syntax (match/case, type hints, walrus operator)
- **Formatting**: Follow existing patterns — ruff will catch issues (line-length 100)
- **Type hints**: Use type annotations for all function signatures
- **Docstrings**: Optional but helpful for public APIs

### Style Rules

1. **One job per function** — if a function does two distinct things, split it
2. **Graceful degradation** — wrap external dependencies in try/except with informative fallbacks
3. **No hardcoded secrets** — API keys go in `config/api_keys.json`, never in source
4. **Thread safety** — use `threading.RLock()` for all state access in brain modules
5. **Error handling** — catch specific exceptions, not bare `except:`
6. **Logging over printing** — use print() for startup messages, return errors in tool results
7. **State persistence** — brain module state files go in the `brain/` directory

### Import Conventions

```python
# Standard library
import asyncio
import json
import threading
from pathlib import Path
from datetime import datetime

# Third-party — always wrapped in try/except for graceful degradation
try:
    import numpy as np
except ImportError:
    np = None

# Local — use relative imports within packages
from .neural_memory import get_neural_memory
```

---

## Brain Module Pattern

Every brain module follows this standard pattern:

```python
"""
module.py — Brief description of what this module does.
"""
import json
import threading
from pathlib import Path

# Module state file (persists between sessions)
STATE_FILE = Path(__file__).resolve().parent / "module_state.json"

class YourModule:
    """Description of what this module contributes to RUMI's cognition."""

    def __init__(self):
        self._lock = threading.RLock()
        self._data = {}
        self._load()

    def _load(self):
        """Load state from JSON file."""
        try:
            with self._lock:
                self._data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            self._data = self._default_state()

    def _save(self):
        """Persist state to JSON file."""
        try:
            with self._lock:
                STATE_FILE.write_text(
                    json.dumps(self._data, indent=2, default=str),
                    encoding="utf-8"
                )
        except Exception as e:
            print(f"[YourModule] Save error: {e}")

    def _default_state(self) -> dict:
        """Return default state structure."""
        return {}

    def get_stats(self) -> dict:
        """Return module statistics for diagnostics."""
        with self._lock:
            return {"status": "ok", "data_size": len(self._data)}

# Singleton pattern — all brain modules use this
_instance = None

def get_your_module():
    """Factory function — returns singleton instance."""
    global _instance
    if _instance is None:
        _instance = YourModule()
    return _instance
```

### Key Points

- **Singleton**: `get_your_module()` is the only way to access the module
- **Thread-safe**: All state access goes through `self._lock`
- **Persistent**: State is loaded on init and saved on meaningful changes
- **Graceful**: Falls back to defaults if state file is corrupted
- **Self-contained**: Module manages its own state file

---

## Action Tool Pattern

Tools are registered in `main.py` with declarations and implementations:

### 1. Import in main.py

```python
my_tool, _ = _safe_action_import("actions.my_tool", "my_tool")
```

### 2. Add tool declaration

```python
TOOL_DECLARATIONS.append({
    "name": "my_tool",
    "description": "What this tool does",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "What action to perform"},
        },
        "required": ["action"]
    }
})
```

### 3. Register handler

```python
@register_tool("my_tool")
def handle_my_tool(**kwargs):
    return my_tool(**kwargs)
```

### 4. Implement in actions/

```python
def my_tool(action: str = "default", **kwargs) -> str:
    """Tool description."""
    try:
        if action == "default":
            return "Result"
        return f"Unknown action: {action}"
    except Exception as e:
        return f"[TOOL_ERROR] {e}"
```

---

## Testing

### Manual Testing

```bash
# Start RUMI and test your change
rumi

# Test specific module independently
python -c "
from brain.your_module import get_your_module
m = get_your_module()
print(m.get_stats())
"
```

### Adding Tests

If your contribution adds new functionality, include test commands or scripts:

```python
# Example test for a brain module
def test_module():
    from brain.your_module import get_your_module
    m = get_your_module()
    stats = m.get_stats()
    assert stats["status"] == "ok"
    print(f"Test passed: {stats}")
```

---

## Security

- **Never commit API keys, tokens, or secrets**
- **Never expose user data** in logs or error messages
- **All destructive operations** require user confirmation
- **Use `send2trash` instead of `os.remove`** for file deletion
- **Rate limit** external API calls to avoid abuse
- **Validate all user input** before processing

### Security Checklist for New Tools

- [ ] Does this tool access external systems/APIs? → Add rate limiting
- [ ] Does this tool modify system state? → Require user confirmation
- [ ] Does this tool access user data? → Log access, never expose
- [ ] Does this tool execute arbitrary code? → Sandbox execution
- [ ] Does this tool make network requests? → Validate targets, block metadata endpoints

---

## Identity Files

When contributing changes that affect RUMI's behavior, update the relevant identity file:

| File | Purpose | Update When |
|------|---------|-------------|
| `RUMI.md` | Core identity & persona | Adding new capabilities, changing core behavior |
| `SOUL.md` | Behavioral directives & red lines | Adding ethical guidelines, changing protocols |
| `USER.md` | User identity & preferences | Rarely — user-specific details |
| `TOOLS.md` | Capabilities reference | Adding/removing tools or modules |
| `HEARTBEAT.md` | Periodic operations config | Changing proactive behavior patterns |

---

## Pull Request Process

1. **Ensure your branch is up to date** with `main`
2. **Run a quick smoke test**: `python rumi_launcher.py` should start without errors
3. **Keep PRs focused** — one feature/fix per PR
4. **Describe your changes** clearly in the PR description
5. **Link related issues** in the PR description
6. **Be responsive to review feedback** — reviewers may ask for clarification or changes

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation update
- [ ] Refactor
- [ ] Performance improvement

## Testing
Describe how you tested your changes.

## Related Issues
Closes #...
```

---

## Questions?

- Open an [issue](https://github.com/subhansh-dev/Rumi/issues)
- Reach out to the creator

---

_Last updated: 2026-05-25_
