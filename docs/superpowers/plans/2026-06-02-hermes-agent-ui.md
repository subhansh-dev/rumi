# RUMI CLI Transformation - Professional TUI Makeover

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform RUMI's terminal UI from amateur to professional grade, matching the TUI quality of Hermes Agent, OpenCode, and Claude Code. Every visual element will be analyzed and upgraded.

**Architecture:** Rewrite `ui.py` to implement professional-grade components: persistent status bar with context gauge, kaomoji spinner system, tool call tree display, collapsible sections, responsive terminal width adaptation, streaming message display, and themed color system. Keep the existing public API (`write_log`, `set_state`, etc.) intact.

**Tech Stack:** Python 3.11+, Rich, prompt_toolkit, threading

---

## Deep Analysis: What Makes These TUIs Professional

### Hermes Agent TUI - The Gold Standard
- **Status bar**: `─ ready │ claude-4-sonnet │ 12k/200k │ [████░░░░░░] 6% │ 2m 34s │ cmp 2 │ 1 session │ 2 bg │ $0.0042 ─ ~/projects/hermes (main)`
- **Kaomoji faces**: 15 faces rotating every 2.5s: `(｡•́︿•̀｡)`, `(◔_◔)`, `(¬‿¬)`, `( •_•)>⌐■-■`, `(⌐■_■)`, `(´･_･`)`, `◉_◉`, `(°ロ°)`, `( ˘⌣˘)♡`, `ヽ(>∀<☆)☆`, `٩(๑❛ᴗ❛๑)۶`, `(⊙_⊙)`, `(¬_¬)`, `( ͡° ͜ʖ ͡°)`, `ಠ_ಠ`
- **Verbs**: 15 verbs rotating every 2.5s: `pondering`, `contemplating`, `musing`, `cogitating`, `ruminating`, `deliberating`, `mulling`, `reflecting`, `processing`, `reasoning`, `analyzing`, `computing`, `synthesizing`, `formulating`, `brainstorming`
- **Tool trail**: `├─ ✓ terminal ls -la` with tree structure, `│` rails, `├─` mid branches, `└─` last branches
- **Collapsible sections**: `▸`/`▾` chevrons with counts: `▾ Thinking (3)`, `▸ Tool calls (5)`
- **Context bar**: `█` filled + `░` empty, 10 chars wide, color-coded: green <50%, gold 50-80%, orange 80-95%, red ≥95%
- **4 indicator styles**: kaomoji, emoji, ascii, unicode (configurable via `/indicator`)
- **9 built-in skins**: default, ares, mono, slate, daylight, warm-lightmode, poseidon, sisyphus, charizard
- **Subagent tree**: Recursive accordion with heat coloring
- **Streaming cursor**: `▍` blinking at 420ms
- **GoodVibesHeart**: `♥` animation near input that pulses

### OpenCode TUI - The Power User
- **Status bar template**: `{model_id} | {total_tokens:k} tokens | ${total_cost}` with 30+ variables
- **Sidebar**: File changes, token summary, session info (toggleable with `leader+b`)
- **30+ themes**: tokyonight, everforest, catppuccin, gruvbox, nord, matrix, etc.
- **Autocomplete**: `@` for files/agents, `/` for commands
- **Dialog system**: Stack-based overlays with fuzzy search
- **Dense layout**: For small terminals (80x24)
- **Layout config**: 18 configurable parameters for spacing/padding
- **Token speed**: `⚡ t/s` in footer
- **Per-message tokens**: `↓12.3s ↑12` (input/output)

### Claude Code TUI - The Enterprise Standard
- **Status line**: `╸ my-project  main │ Opus 4.8 │ +12 -3 │ $0.42 │ ████████░░░░ 37%`
- **Braille spinner**: `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` (10 frames)
- **Tool display**: Collapsed by default, expanded with `Ctrl+O`
- **Thinking**: Collapsed by default, gray italic when visible
- **6 themes**: dark, light, dark-daltonized, light-daltonized, dark-ansi, light-ansi
- **Virtual scrolling**: Only visible messages + buffer participate in reconciliation
- **16ms frame budget**: ~5ms from React scene graph to ANSI written
- **Typewriter streaming**: Tokens appear as received, markdown applied in real-time
- **Permission dialogs**: Modal overlays with shimmer effect
- **Rate limits**: Fill bars for 5-hour and 7-day windows

---

## File Structure

| File | Responsibility |
|------|---------------|
| `ui.py` | Main TUI module - all visual components |
| `discovery/output.py` | Output formatting (minor updates) |

---

## Task 1: Professional Kaomoji Spinner System

**Files:**
- Modify: `ui.py:166-186` (constants)
- Modify: `ui.py:1377-1383` (show_thinking, show_done)

- [ ] **Step 1: Add Hermes-style kaomoji spinner constants**

```python
# ================================================================
# KAOMOJI SPINNER SYSTEM (Hermes Agent style)
# ================================================================

# 15 kaomoji faces rotating every 2.5 seconds
KAOMOJI_FACES = [
    "(｡•́︿•̀｡)",   # sad/worried
    "(◔_◔)",        # skeptical
    "(¬‿¬)",        # devious
    "( •_•)>⌐■-■",  # putting on sunglasses
    "(⌐■_■)",        # sunglasses on
    "(´･_･`)",      # neutral
    "◉_◉",          # wide eyes
    "(°ロ°)",        # surprised
    "( ˘⌣˘)♡",     # loving
    "ヽ(>∀<☆)☆",    # excited star
    "٩(๑❛ᴗ❛๑)۶",   # celebrating
    "(⊙_⊙)",        # blank stare
    "(¬_¬)",         # side-eye
    "( ͡° ͜ʖ ͡°)",  # lenny face
    "ಠ_ಠ"           # disapproval
]

# 15 verbs rotating every 2.5 seconds
THINKING_VERBS = [
    "pondering", "contemplating", "musing", "cogitating", "ruminating",
    "deliberating", "mulling", "reflecting", "processing", "reasoning",
    "analyzing", "computing", "synthesizing", "formulating", "brainstorming"
]

# Per-tool verbs (when a specific tool is running)
TOOL_VERBS = {
    "search": "searching",
    "read": "reading",
    "write": "writing",
    "edit": "editing",
    "graph": "graphing",
    "discover": "discovering",
    "hypothesize": "hypothesizing",
    "review": "reviewing",
    "experiment": "experimenting",
    "analyze": "analyzing",
}

# 4 indicator styles (configurable via /indicator)
INDICATOR_STYLES = {
    "kaomoji": {
        "frames": KAOMOJI_FACES,
        "tick": 2.5,  # seconds
        "show_verb": True,
    },
    "emoji": {
        "frames": ["⚕", "🌀", "🤔", "✨", "🍵", "🔮"],
        "tick": 0.6,
        "show_verb": True,
    },
    "ascii": {
        "frames": ["|", "/", "-", "\\"],
        "tick": 0.1,
        "show_verb": True,
    },
    "unicode": {
        "frames": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "tick": 0.08,
        "show_verb": False,
    },
}

# Default indicator style
INDICATOR_STYLE = "kaomoji"

# Streaming cursor (blinking at 420ms)
STREAMING_CURSOR = "▍"
```

- [ ] **Step 2: Update `show_thinking()` with kaomoji**

```python
def show_thinking(self, message: str = ""):
    """Hermes-style kaomoji thinking indicator."""
    face = random.choice(KAOMOJI_FACES)
    verb = random.choice(THINKING_VERBS)
    console.print(Text(f"  {face} {verb}…", style=f"bold {ACCENT_BLUE}"))
```

- [ ] **Step 3: Update `show_done()` with kaomoji**

```python
def show_done(self, message: str = ""):
    """Hermes-style kaomoji done indicator."""
    msg = message or "Done."
    console.print(Text(f"  (◕‿◕✿) {msg}", style=f"bold {ACCENT_GREEN}"))
```

- [ ] **Step 4: Verify syntax**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

---

## Task 2: Professional Status Bar

**Files:**
- Modify: `ui.py:859-895` (_get_toolbar method)

- [ ] **Step 1: Rewrite `_get_toolbar()` with Hermes-style layout**

```python
def _get_toolbar(self):
    """Hermes-style persistent status bar with progressive disclosure."""
    if not HAVE_PT:
        return ""

    spin = SPINNER_CHARS[self._current_spin_idx]
    elapsed = int(time.time() - self._start_time)
    uptime = f"{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d}"

    # Get terminal width for responsive layout
    term_width = console.width or 80

    parts = []

    # Left border accent
    parts.append("<style fg='#30363d'>─</style>")

    # Status/Indicator (always shown)
    if self._is_busy or self._discovery_running:
        face = random.choice(KAOMOJI_FACES)
        verb = self._discovery_step or random.choice(THINKING_VERBS)
        parts.append(f"<style fg='#39d353'>{face} {verb}…</style>")
    else:
        parts.append("<style fg='#8FBC8F'>ready</style>")

    parts.append("<style fg='#30363d'>│</style>")

    # Model name (always shown, truncated to 26 chars)
    model = "Gemini 2.5"
    parts.append(f"<style fg='#58a6ff'>{model}</style>")
    parts.append("<style fg='#30363d'>│</style>")

    # Context: tokens (always shown)
    parts.append(f"<style fg='#8b949e'>{self._total_tokens:,} tok</style>")

    # Context bar (≥72 cols)
    if term_width >= 72:
        parts.append("<style fg='#30363d'>│</style>")
        parts.append(self._get_context_bar(self._total_tokens, 200000))

    # Duration (≥76 cols)
    if term_width >= 76:
        parts.append("<style fg='#30363d'>│</style>")
        parts.append(f"<style fg='#8b949e'>{uptime}</style>")

    # Mode badges
    if self._think_mode:
        parts.append("<style fg='#30363d'>│</style>")
        parts.append("<style fg='#bc8cff'>think</style>")
    if self._deep_dive_active:
        parts.append("<style fg='#30363d'>│</style>")
        parts.append("<style fg='#39d353'>dive</style>")

    # Cost (≥96 cols)
    if term_width >= 96:
        parts.append("<style fg='#30363d'>│</style>")
        parts.append(f"<style fg='#8b949e'>${self._total_cost:.4f}</style>")

    # Right border + cwd
    parts.append("<style fg='#30363d'> ─</style>")

    return HTML("".join(parts))
```

- [ ] **Step 2: Update `_get_context_bar()` with Hermes color thresholds**

```python
def _get_context_bar(self, tokens_used: int = 0, max_tokens: int = 200000) -> str:
    """Hermes-style context bar: [████░░░░░░] with color coding."""
    pct = min(100, int((tokens_used / max_tokens) * 100))
    filled = int(pct / 10)
    empty = 10 - filled
    bar = "█" * filled + "░" * empty

    # Hermes color thresholds
    if pct < 50:
        color = "#8FBC8F"  # Dark sea green - plenty of room
    elif pct < 80:
        color = "#FFD700"  # Gold - getting full
    elif pct < 95:
        color = "#FF8C00"  # Dark orange - approaching limit
    else:
        color = "#FF6B6B"  # Light red - near overflow

    return f"<style fg='{color}'>[{bar}] {pct}%</style>"
```

- [ ] **Step 3: Verify syntax**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

---

## Task 3: Tool Call Tree Display

**Files:**
- Modify: `ui.py:1253-1280` (tool call methods)

- [ ] **Step 1: Rewrite `_show_tool_call()` with Hermes-style tree display**

```python
def _show_tool_call(self, name: str, query: str = ""):
    """Hermes-style tool call with tree display."""
    self._tool_calls.start(name, query)
    self._activity_feed.add(f"{name}", ACCENT_TEAL)

    # Get tool-specific verb if available
    tool_verb = TOOL_VERBS.get(name.lower(), "processing")

    line = Text()
    line.append("  ├─ ", style=TXT_DIM)
    line.append(f"✓ ", style=f"bold {ACCENT_GREEN}")
    line.append(f"{name}", style=f"bold {ACCENT_BLUE}")
    if query:
        short = query[:40] + "..." if len(query) > 40 else query
        line.append(f" {short}", style=TXT_SECOND)
    console.print(line)
```

- [ ] **Step 2: Rewrite `complete_tool_call()` with duration**

```python
def complete_tool_call(self, name: str, result: str = ""):
    """Hermes-style tool completion with duration."""
    self._tool_calls.complete(name, result)

    elapsed = ""
    for call in reversed(self._tool_calls.get_recent(5)):
        if call["name"] == name and call.get("elapsed"):
            elapsed = f" ({call['elapsed']:.1f}s)"
            break

    line = Text()
    line.append("  └─ ", style=TXT_DIM)
    line.append(f"✓ ", style=f"bold {ACCENT_GREEN}")
    line.append(f"{name}", style=f"bold {ACCENT_GREEN}")
    line.append(f"{elapsed}", style=TXT_DIM)
    if result:
        short = result[:50] + "..." if len(result) > 50 else result
        line.append(f"  {short}", style=TXT_DIM)
    console.print(line)
```

- [ ] **Step 3: Verify syntax**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

---

## Task 4: Responsive Terminal Width

**Files:**
- Modify: `ui.py:675-726` (boot sequence)
- Modify: `ui.py:1285-1310` (status panel)

- [ ] **Step 1: Add responsive width helper**

```python
def _get_responsive_width(self) -> str:
    """Get responsive layout mode based on terminal width."""
    term_width = console.width or 80
    if term_width >= 76:
        return "full"
    elif term_width >= 52:
        return "compact"
    else:
        return "minimal"
```

- [ ] **Step 2: Update `_show_status_panel()` for responsive layout**

```python
def _show_status_panel(self):
    """Hermes-style responsive status panel."""
    uptime = self._get_uptime()
    pct = min(100, int((self._total_tokens / 200000) * 100))
    filled = int(pct / 10)
    empty = 10 - filled
    bar_text = f"[{'█' * filled}{'░' * empty}] {pct}%"
    
    if pct < 50:
        bar_color = ACCENT_GREEN
    elif pct < 80:
        bar_color = ACCENT_AMBER
    elif pct < 95:
        bar_color = "#f0883e"
    else:
        bar_color = ACCENT_RED

    layout = self._get_responsive_width()
    
    console.print()
    line = Text()
    
    if layout == "full":
        line.append("  RUMI ", style=f"bold {ACCENT_BLUE}")
        line.append(f"{self._total_tokens:,}/200K ", style=TXT_SECOND)
        line.append(f"{bar_text} ", style=f"bold {bar_color}")
        line.append(f"${self._total_cost:.4f} ", style=ACCENT_GREEN)
        line.append(f"{uptime}", style=TXT_SECOND)
    elif layout == "compact":
        line.append("  RUMI ", style=f"bold {ACCENT_BLUE}")
        line.append(f"{pct}% ", style=f"bold {bar_color}")
        line.append(f"${self._total_cost:.3f} ", style=ACCENT_GREEN)
        line.append(f"{uptime}", style=TXT_SECOND)
    else:  # minimal
        line.append("  RUMI ", style=f"bold {ACCENT_BLUE}")
        line.append(f"{uptime}", style=TXT_SECOND)
    
    console.print(line)
    console.print()
```

- [ ] **Step 3: Verify syntax**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

---

## Task 5: Collapsible Sections

**Files:**
- Modify: `ui.py:590-670` (RumiUI.__init__)
- Add: Section state tracking

- [ ] **Step 1: Add section state to `__init__`**

Add after `self._discovery_topic = ""`:
```python
        # Collapsible sections (Hermes-style)
        self._sections = {
            "thinking": "expanded",
            "tools": "expanded",
            "activity": "collapsed",
            "subagents": "collapsed",
        }
```

- [ ] **Step 2: Add section toggle method**

Add after `clear_interrupt()`:
```python
    def toggle_section(self, section: str):
        """Toggle collapsible section state."""
        if section in self._sections:
            current = self._sections[section]
            self._sections[section] = "collapsed" if current == "expanded" else "expanded"
```

- [ ] **Step 3: Verify syntax**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

---

## Task 6: Streaming Message Display

**Files:**
- Modify: `ui.py:1389-1431` (write_log method)

- [ ] **Step 1: Update `write_log()` with Hermes-style streaming display**

```python
def write_log(self, text: str):
    """Hermes-style streaming message display."""
    with self._input_lock:
        tl = text.lower().strip()

        if any(skip in tl for skip in ["[rumi]", "[episodic]", "[selfawareness]",
                                        "[coordinator]", "[dreaming]", "[vectormemory]",
                                        "[telegram]", "non-data parts"]):
            return

        if tl.startswith("you:"):
            content = text[4:].strip()
            self.set_state("PROCESSING")
            console.print()
            console.print(Text(f"  ❯ {content}", style=f"bold {ACCENT_BLUE}"))
            self.show_thinking()

        elif tl.startswith("rumi:") or tl.startswith("ai:"):
            prefix_len = 5 if tl.startswith("rumi:") else 3
            content = text[prefix_len:].strip()
            content = _re.sub(r'\*\*Thinking(?:\s*\(.*?\))?\*\*\s*', '', content).strip()
            content = _re.sub(r'\*\*Reasoning\*\*\s*', '', content).strip()
            if content:
                console.print()
                try:
                    console.print(Markdown(content))
                except Exception:
                    console.print(Text(f"  {content}", style=TXT_PRIMARY))
            self.set_state("SPEAKING")

        elif tl.startswith("sys:"):
            content = text[4:].strip()
            self._activity_feed.add(content, TXT_SECOND)
            # Only show if activity section is expanded
            if self._sections.get("activity") == "expanded":
                console.print(Text(f"  {content}", style=TXT_SECOND))

        elif tl.startswith("err:") or tl.startswith("error:"):
            err_msg = text[4:].strip() if ":" in text[4:5] else text[4:].strip()
            self._activity_feed.add(f"error: {err_msg}", ACCENT_RED)
            console.print(Text(f"  ✗ error: {err_msg}", style=f"bold {ACCENT_RED}"))

        else:
            if not text.strip() or text.strip().startswith("["):
                return
            console.print(Text(f"  {text}", style=TXT_PRIMARY))
```

- [ ] **Step 2: Verify syntax**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

---

## Task 7: Discovery Step with Inline Progress

**Files:**
- Modify: `ui.py:1437-1476` (set_discovery_step)

- [ ] **Step 1: Update `set_discovery_step()` with Hermes-style inline progress**

```python
def set_discovery_step(self, step: str):
    """Hermes-style discovery step with inline progress."""
    self._discovery_step = step
    self._activity_feed.add(step, ACCENT_PURPLE)

    step_lower = step.lower()
    if any(k in step_lower for k in ["paper", "fetch", "arxiv", "pubmed", "literature"]):
        self._pipeline.start_phase("paper_retrieval")
        color = ACCENT_GREEN
    elif any(k in step_lower for k in ["extract", "entity", "relation"]):
        self._pipeline.start_phase("entity_extraction")
        color = ACCENT_BLUE
    elif any(k in step_lower for k in ["graph", "knowledge"]):
        self._pipeline.start_phase("knowledge_graph")
        color = ACCENT_PURPLE
    elif any(k in step_lower for k in ["contradict", "skeptic", "refin"]):
        self._pipeline.start_phase("contradiction_mine")
        color = ACCENT_RED
    elif any(k in step_lower for k in ["generat", "llm", "hypothes"]):
        self._pipeline.start_phase("hypothesis_gen")
        color = ACCENT_CYAN
    elif any(k in step_lower for k in ["novelt", "similar"]):
        self._pipeline.start_phase("novelty_check")
        color = ACCENT_AMBER
    elif any(k in step_lower for k in ["experiment", "plan"]):
        self._pipeline.start_phase("experiment_plan")
        color = ACCENT_GREEN
    elif any(k in step_lower for k in ["comput", "bayesian", "monte carlo", "metric"]):
        color = ACCENT_PURPLE
    elif any(k in step_lower for k in ["label", "ground", "cit", "valid"]):
        color = ACCENT_AMBER
    else:
        color = ACCENT_BLUE

    # Hermes-style: step name + inline progress
    pct = self._pipeline.get_progress_pct()
    bar = _make_progress_bar(pct, 8)
    line = Text()
    line.append(f"  ├─ ", style=TXT_DIM)
    line.append(f"{step} ", style=f"{color}")
    line.append(bar, style=TXT_DIM)
    console.print(line)
```

- [ ] **Step 2: Verify syntax**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

---

## Task 8: Boot Sequence with Collapsible Sections

**Files:**
- Modify: `ui.py:668-717` (boot sequence)

- [ ] **Step 1: Update `_show_boot_sequence()` with Hermes-style collapsible sections**

```python
def _show_boot_sequence(self):
    """Hermes-style boot with collapsible sections."""
    console.clear()

    from discovery.llm_client import get_status
    status = get_status()
    groq_ok = status.get("groq", {}).get("available", False)
    gemini_ok = status.get("gemini", {}).get("available", False)

    console.print()

    # ASCII Logo -- centered
    logo_lines = [l for l in RUMI_LOGO.split("\n") if l.strip()]
    max_logo_width = max(len(l) for l in logo_lines)
    term_width = console.width or 80
    pad = max(0, (term_width - max_logo_width) // 2)

    for line_str in logo_lines:
        console.print(Text(f"{' ' * pad}{line_str}", style=f"bold {ACCENT_BLUE}"))

    # Subtitle centered
    subtitle = "Research Unified Machine Intelligence"
    sub_pad = max(0, (term_width - len(subtitle) - 2) // 2)
    console.print(Text(f"{' ' * sub_pad}{subtitle}", style=TXT_DIM))
    console.print()

    # Tools section (expanded by default)
    console.print(Text("  ▾ Tools", style=f"bold {ACCENT_BLUE}"))
    tools_line = Text()
    tools_line.append("    groq", style=ACCENT_GREEN if groq_ok else ACCENT_RED)
    tools_line.append("  ", style=TXT_DIM)
    tools_line.append("gemini", style=ACCENT_GREEN if gemini_ok else ACCENT_RED)
    tools_line.append("  │  ", style=TXT_DIM)
    tools_line.append("17 domains", style=TXT_SECOND)
    tools_line.append("  │  ", style=TXT_DIM)
    tools_line.append("88 modules", style=TXT_SECOND)
    console.print(tools_line)
    console.print()

    # Skills section (collapsed by default)
    console.print(Text("  ▸ Skills", style=f"bold {TXT_DIM}"))
    console.print()

    # System Prompt section (collapsed by default)
    console.print(Text("  ▸ System Prompt", style=f"bold {TXT_DIM}"))
    console.print()

    # MCP Servers section (collapsed by default)
    console.print(Text("  ▸ MCP Servers", style=f"bold {TXT_DIM}"))
    console.print()

    # Help text centered
    help_text = "/help for commands"
    h_pad = max(0, (term_width - len(help_text) - 2) // 2)
    console.print(Text(f"{' ' * h_pad}{help_text}", style=TXT_DIM))
    console.print()
```

- [ ] **Step 2: Verify syntax**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

---

## Task 9: Help Text Update

**Files:**
- Modify: `ui.py:295-319` (HELP_TEXT)

- [ ] **Step 1: Update HELP_TEXT with Hermes-style commands**

```python
HELP_TEXT = f"""[bold {ACCENT_BLUE}]RUMI[/bold {ACCENT_BLUE}] [dim]v3.0 | Research Unified Machine Intelligence[/dim]

[bold]Commands[/bold]
  [bold {ACCENT_BLUE}]/help[/{ACCENT_BLUE}]          Show this help
  [bold {ACCENT_BLUE}]/clear[/{ACCENT_BLUE}]         Clear screen
  [bold {ACCENT_BLUE}]/status[/{ACCENT_BLUE}]        System status
  [bold {ACCENT_BLUE}]/stats[/{ACCENT_BLUE}]         Session stats
  [bold {ACCENT_BLUE}]/usage[/{ACCENT_BLUE}]         Token/cost breakdown
  [bold {ACCENT_BLUE}]/exit[/{ACCENT_BLUE}]          Shut down

[bold]Discovery[/bold]
  [bold {ACCENT_BLUE}]/discover [topic][/{ACCENT_BLUE}]    Full pipeline
  [bold {ACCENT_BLUE}]/search [query][/{ACCENT_BLUE}]      Literature search
  [bold {ACCENT_BLUE}]/hypothesize [topic][/{ACCENT_BLUE}] Generate hypotheses
  [bold {ACCENT_BLUE}]/experiment[/{ACCENT_BLUE}]          Design experiment
  [bold {ACCENT_BLUE}]/review[/{ACCENT_BLUE}]              Peer review
  [bold {ACCENT_BLUE}]/domains[/{ACCENT_BLUE}]             List 17 domains

[bold]Modes[/bold]
  [bold {ACCENT_BLUE}]/think[/{ACCENT_BLUE}]         Toggle reasoning mode
  [bold {ACCENT_BLUE}]/dive[/{ACCENT_BLUE}]          Toggle deep research
  [bold {ACCENT_BLUE}]/indicator[/{ACCENT_BLUE}]     Switch spinner style

[bold]Sections[/bold]
  [bold {ACCENT_BLUE}]/details [section][/{ACCENT_BLUE}]   Toggle section visibility

[bold]Shortcuts[/bold]
  [bold {ACCENT_AMBER}]Ctrl+K[/{ACCENT_AMBER}]  Command palette
  [bold {ACCENT_AMBER}]Ctrl+L[/{ACCENT_AMBER}]  Clear screen
  [bold {ACCENT_AMBER}]Escape[/{ACCENT_AMBER}]  Interrupt"""
```

- [ ] **Step 2: Verify syntax**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

---

## Task 10: Final Integration Test

- [ ] **Step 1: Run full syntax check**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "import py_compile; py_compile.compile(r'C:\Users\Admin\Desktop\rumi\ui.py', doraise=True); print('OK')"`

Expected: OK

- [ ] **Step 2: Test import**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "from ui import RumiUI; print('Import OK')"`

Expected: Import OK

- [ ] **Step 3: Verify all public API methods exist**

Run: `& "C:\Users\Admin\Desktop\rumi\.venv\Scripts\python.exe" -c "from ui import RumiUI; ui = RumiUI.__new__(RumiUI); assert hasattr(ui, 'write_log'); assert hasattr(ui, 'set_state'); assert hasattr(ui, 'set_discovery_step'); assert hasattr(ui, 'show_tool_call'); assert hasattr(ui, 'complete_tool_call'); assert hasattr(ui, 'update_tokens'); assert hasattr(ui, 'show_toast'); assert hasattr(ui, 'interrupt_requested'); assert hasattr(ui, 'clear_interrupt'); print('All API methods present')"`

Expected: All API methods present

---

## Summary

After completing all tasks, RUMI will have:

1. **Hermes-style kaomoji spinner** - 15 faces + 15 verbs rotating every 2.5s
2. **Professional status bar** - Model, tokens, context gauge, cost, duration with progressive disclosure
3. **Tool call tree** - `├─ ✓ toolname(args)` with tree structure
4. **Responsive layout** - Adapts to terminal width (full/compact/minimal)
5. **Collapsible sections** - `▸`/`▾` chevrons with counts
6. **Streaming messages** - Hermes-style message display
7. **Discovery progress** - Inline progress bars with step names
8. **Centered boot** - ASCII logo and info centered in terminal
9. **Updated help** - Hermes-style command reference
10. **4 spinner styles** - kaomoji, emoji, ascii, unicode (configurable)
