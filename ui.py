"""
ui.py -- RUMI Terminal UI (v10.0 Hermes Agent Style)
Works with or without rich/prompt_toolkit — falls back to ANSI codes.
"""
import sys as _sys
_sys.stderr.write(f"[RUMI-UI] Python {_sys.version.split()[0]} @ {_sys.executable}\n")
_sys.stderr.flush()

import sys
import os
import json
import time
import random
import platform
import threading
import re as _re
from pathlib import Path
from datetime import datetime
from collections import deque

# -- Terminal setup --
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
        STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(handle, mode.value)
    except Exception:
        pass

# -- Rich import (optional) --
HAVE_RICH = False
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    from rich.rule import Rule
    from rich.table import Table
    from rich.box import ROUNDED, MINIMAL, SIMPLE, HEAVY, DOUBLE, HORIZONTALS
    from rich.style import Style
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.layout import Layout
    from rich.columns import Columns
    from rich.align import Align
    from rich.padding import Padding
    from rich.theme import Theme
    HAVE_RICH = True
except ImportError:
    pass

# -- prompt_toolkit import (optional) --
HAVE_PT = False
try:
    from prompt_toolkit import prompt as _pt_prompt
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style as PtStyle
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.formatted_text import HTML
    HAVE_PT = True
except ImportError:
    HAVE_PT = False
    KeyBindings = None
    HTML = None

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
API_FILE = CONFIG_DIR / "api_keys.json"

# ================================================================
# ANSI HELPERS (work without rich)
# ================================================================

def _ansi(color_hex: str) -> str:
    """Convert #RRGGBB to ANSI 24-bit escape sequence."""
    if not color_hex or not color_hex.startswith("#"):
        return ""
    r = int(color_hex[1:3], 16)
    g = int(color_hex[3:5], 16)
    b = int(color_hex[5:7], 16)
    return f"\033[38;2;{r};{g};{b}m"

def _ansi_bg(color_hex: str) -> str:
    """Convert #RRGGBB to ANSI bg escape sequence."""
    if not color_hex or not color_hex.startswith("#"):
        return ""
    r = int(color_hex[1:3], 16)
    g = int(color_hex[3:5], 16)
    b = int(color_hex[5:7], 16)
    return f"\033[48;2;{r};{g};{b}m"

_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"
_CLEAR_LINE = "\033[2K"
_CUR_UP = "\033[A"

def _aprint(text: str, color: str = "", bold: bool = False):
    """Print with ANSI color (works without rich)."""
    parts = []
    if bold:
        parts.append(_BOLD)
    if color and color.startswith("#"):
        parts.append(_ansi(color))
    parts.append(text)
    parts.append(_RESET)
    sys.stdout.write("".join(parts) + "\n")
    sys.stdout.flush()

# ================================================================
# PREMIUM AI RESEARCH OS THEME
# Pure black, soft white, electric blue/cyan, no grey
# ================================================================

# Background
BG_DEEP    = "#000000"
BG_SECOND  = "#0a0a0a"
BG_PANEL   = "#111111"
BG_ELEMENT = "#1a1a1a"
BG_HOVER   = "#222222"
BG_INPUT   = "#000000"

# Text hierarchy — NO GREY, all visible
TXT_BRIGHT  = "#FFFFFF"
TXT_PRIMARY = "#EAEAEA"
TXT_SECOND  = "#CCCCCC"
TXT_MUTED   = "#AAAAAA"
TXT_DIM     = "#888888"

# Accent palette — electric blue/cyan
ACCENT_CYAN    = "#00E5FF"
ACCENT_BLUE    = "#2979FF"
ACCENT_GREEN   = "#00E676"
ACCENT_AMBER   = "#FFD600"
ACCENT_RED     = "#FF1744"
ACCENT_PURPLE  = "#B388FF"
ACCENT_TEAL    = "#00E5FF"
ACCENT_PINK    = "#FF80AB"

# Semantic aliases
C_BLUE   = ACCENT_BLUE
C_GREEN  = ACCENT_GREEN
C_AMBER  = ACCENT_AMBER
C_RED    = ACCENT_RED
C_PURPLE = ACCENT_PURPLE
C_TEAL   = ACCENT_TEAL
C_PINK   = ACCENT_PINK
C_DIM    = TXT_MUTED
C_WHITE  = TXT_PRIMARY
C_BOLD   = TXT_BRIGHT

# Borders
BORDER_SUBTLE  = "#333333"
BORDER_NORMAL  = "#555555"
BORDER_ACTIVE  = "#2979FF"

# Status bar
SB_BG = "#000000"
SB_FG = "#CCCCCC"

# ================================================================
# CONSOLE (rich or ANSI fallback)
# ================================================================

if HAVE_RICH:
    _dark_theme = Theme({
        "black": BG_DEEP,
        "white": TXT_PRIMARY,
        "cyan": ACCENT_CYAN,
        "green": ACCENT_GREEN,
        "yellow": ACCENT_AMBER,
        "blue": ACCENT_BLUE,
        "magenta": ACCENT_PURPLE,
        "red": ACCENT_RED,
        "dim": TXT_MUTED,
    })

    # Force UTF-8 stdout for Rich on Windows
    if sys.platform == "win32":
        import io as _io
        if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding != 'utf-8':
            sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer') and sys.stderr.encoding != 'utf-8':
            sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    console = Console(
        force_terminal=True,
        color_system="truecolor",
        theme=_dark_theme,
        no_color=False,
    )

    _console_lock = threading.Lock()
    _orig_console_print = console.print

    def _thread_safe_print(*args, **kwargs):
        with _console_lock:
            _orig_console_print(*args, **kwargs)

    console.print = _thread_safe_print
else:
    # ANSI fallback console
    class _AnsiConsole:
        """Minimal console using ANSI escape codes."""
        def __init__(self):
            self.width = 80
            try:
                import shutil
                self.width = shutil.get_terminal_size().columns
            except Exception:
                pass

        def print(self, *args, **kwargs):
            for arg in args:
                if isinstance(arg, str):
                    sys.stdout.write(arg + "\n")
                elif hasattr(arg, '__str__'):
                    sys.stdout.write(str(arg) + "\n")
            sys.stdout.flush()

        def clear(self):
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    console = _AnsiConsole()

    # Stub out Rich classes when not available
    class Text:
        def __init__(self, text="", style=""):
            self._parts = [(text, style)]
        def append(self, text, style=""):
            self._parts.append((text, style))
            return self
        def __str__(self):
            out = []
            for text, style in self._parts:
                color = ""
                bold = False
                if style:
                    s = str(style)
                    if "bold" in s:
                        bold = True
                    # Extract hex color from style string
                    for part in s.split():
                        if part.startswith("#"):
                            color = part
                            break
                    if not color and s.startswith("#"):
                        color = s
                if bold:
                    out.append(_BOLD)
                if color and color.startswith("#"):
                    out.append(_ansi(color))
                out.append(text)
                out.append(_RESET)
            return "".join(out)
        @property
        def plain(self):
            return "".join(t for t, _ in self._parts)

    class Markdown:
        def __init__(self, text="", **kw):
            self._text = text
        def __str__(self):
            return self._text

    def _md(text):
        return Markdown(text)

    _console_lock = threading.Lock()

# ================================================================
# HERMES AGENT CONSTANTS
# ================================================================

# Prompt symbols
PROMPT_SYMBOL = "> "
PROMPT_BUSY   = "> "
PROMPT_READY  = "> "

# Clean ASCII indicators (no kaomoji)
THINKING_VERBS = [
    "searching literature", "extracting entities", "building knowledge graph",
    "mining contradictions", "generating hypotheses", "reviewing claims",
    "designing experiments", "checking novelty", "synthesizing results",
    "analyzing patterns", "computing metrics", "formulating theories",
]

# Per-tool verbs
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
    "papers": "fetching",
    "contradictions": "mining",
    "enrich": "enriching",
}

# Single indicator style — clean ASCII
INDICATOR_STYLES = {
    "ascii": {
        "frames": ["|", "/", "-", "\\"],
        "tick": 0.1,
        "show_verb": True,
    },
}

INDICATOR_STYLE = "ascii"

# Streaming cursor
STREAMING_CURSOR = "_"

# Kaomoji faces (ported from Hermes Agent)
FACES = [
    '(｡•́︿•̀｡)',
    '(◔_◔)',
    '(¬‿¬)',
    '( •_•)>⌐■-■',
    '(⌐■_■)',
    '(´･_･`)',
    '◉_◉',
    '(°ロ°)',
    '( ˘⌣˘)♡',
    'ヽ(>∀<☆)☆',
    '٩(๑❛ᴗ❛๑)۶',
    '(⊙_⊙)',
    '(¬_¬)',
    '( ͡° ͜ʖ ͡°)',
    'ಠ_ಠ',
]

# Role display system (Hermes Agent style)
ROLES = {
    "user":      {"glyph": "❯", "color": ACCENT_BLUE,   "label": "USER"},
    "assistant": {"glyph": "●", "color": ACCENT_CYAN,   "label": "RUMI"},
    "tool":      {"glyph": "⚡", "color": ACCENT_AMBER,  "label": "TOOL"},
    "system":    {"glyph": "·", "color": TXT_MUTED,      "label": "SYS"},
}

# Thinking verbs (Hermes Agent style)
THINKING_VERBS_HERMES = [
    "pondering", "contemplating", "musing", "cogitating",
    "ruminating", "deliberating", "mulling", "reflecting",
    "processing", "reasoning", "analyzing", "computing",
    "synthesizing", "formulating", "brainstorming",
]

# Legacy compatibility
SPINNER_CHARS = "|/-\\"
THINKING_MESSAGES = THINKING_VERBS

# Status badges
BADGE_ONLINE    = "[READY]"
BADGE_THINKING  = "[THINKING]"
BADGE_RESEARCH  = "[RESEARCHING]"
BADGE_DISCOVER  = "[DISCOVERING]"
BADGE_MEMORY    = "[MEMORY]"
BADGE_DREAM     = "[DREAM]"
BADGE_IDLE      = "[IDLE]"

# ================================================================
# ASCII LOGO
# ================================================================

RUMI_LOGO = r"""
  ██████╗ ██╗   ██╗███╗   ███╗██╗
  ██╔══██╗██║   ██║████╗ ████║██║
  ██████╔╝██║   ██║██╔████╔██║██║
  ██╔══██╗██║   ██║██║╚██╔╝██║██║
  ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║
  ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝
"""

# ================================================================
# PERSONALITY SYSTEM
# ================================================================

PERSONALITIES = {
    "cutesy": {
        "label": "Cutesy / UwU",
        "desc": "Playful, cute scientist",
        "soul_file": "SOUL_cutesy.md",
        "rumi_file": "RUMI_cutesy.md",
    },
    "professional": {
        "label": "Professional / Sharp",
        "desc": "Direct, analytical scientist",
        "soul_file": "SOUL_professional.md",
        "rumi_file": "RUMI_professional.md",
    },
}


def _set_personality(choice: str):
    p = PERSONALITIES.get(choice)
    if not p:
        return False
    for dest, src_key in [("SOUL.md", "soul_file"), ("RUMI.md", "rumi_file")]:
        src = BASE_DIR / p[src_key]
        dst = BASE_DIR / dest
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    cfg = BASE_DIR / "config" / "api_keys.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            data["personality"] = choice
            cfg.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception:
            pass
    return True


# ================================================================
# UTILITY FUNCTIONS
# ================================================================

def _detect_os() -> str:
    s = platform.system().lower()
    return "mac" if s == "darwin" else "windows" if s == "windows" else "linux"


def _load_user_name() -> str:
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("user_name", "OPERATOR").upper()
    except Exception:
        return "OPERATOR"


def _api_keys_exist() -> bool:
    if not API_FILE.exists():
        return False
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        has_gemini = bool(data.get("gemini_api_key"))
        has_groq = bool(data.get("groq_api_key"))
        has_os = bool(data.get("os_system"))
        return has_gemini and has_groq and has_os
    except Exception:
        return False


def _make_progress_bar(pct: int, width: int = 10) -> str:
    """Progress bar: [████░░░░░░] 40%"""
    filled = int(pct / 100 * width)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {pct}%"


def _make_status_badge(text: str, color: str) -> Text:
    badge = Text()
    badge.append(f" {text} ", style=f"bold {color}")
    return badge


# ================================================================
# HELP TEXT
# ================================================================

HELP_TEXT = f"""**RUMI** v3.1 — Research Unified Machine Intelligence

**Commands**
  /help            Show this help
  /clear           Clear screen
  /status          System status
  /stats           Session stats
  /exit            Shut down

**Discovery**
  /discover <topic>      Full pipeline
  /search <query>        Literature search
  /hypothesize [topic]   Generate hypotheses
  /experiment            Design experiment
  /review                Peer review
  /domains               List 17 domains

**New in v2.1**
  /simulate <hypothesis>  Monte Carlo simulation
  /debate <hypothesis>    Multi-agent debate
  /continuous [N]         Autonomous research loop
  /transfer <domain>:<mech> to <domain>  Cross-domain transfer
  /curiosity              Research frontier
  /evolve                 Theory evolution
  /consistency            Math consistency check

**Modes**
  /think           Toggle reasoning mode
  /dive            Toggle deep research

**Shortcuts**
  Ctrl+K  Command palette
  Ctrl+L  Clear screen
  Escape  Interrupt"""

# ================================================================
# SLASH COMMANDS
# ================================================================

SLASH_COMMANDS = [
    "/help", "/clear", "/think", "/dive",
    "/status", "/stats", "/model", "/exit",
    "/science", "/discover", "/search", "/enrich", "/hypothesize",
    "/experiment", "/generate", "/contradictions",
    "/papers", "/review", "/graph", "/dashboard", "/discoveries",
    "/notebook", "/domains", "/domain",
    "/personality", "/reason", "/theorize", "/grounded",
    "/timeline",
    "/simulate", "/debate", "/continuous", "/transfer",
    "/curiosity", "/evolve", "/consistency",
]


# ================================================================
# SESSION TIMELINE
# ================================================================

class SessionTimeline:
    def __init__(self):
        self._events: list[dict] = []
        self._lock = threading.Lock()

    def add(self, event_type: str, description: str, detail: str = ""):
        with self._lock:
            self._events.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": event_type,
                "desc": description,
                "detail": detail,
            })

    def get_events(self, last_n: int = 20) -> list[dict]:
        with self._lock:
            return list(self._events[-last_n:])

    def clear(self):
        with self._lock:
            self._events.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._events)


# ================================================================
# ACTIVITY FEED
# ================================================================

class ActivityFeed:
    def __init__(self, max_items: int = 50):
        self._items: deque = deque(maxlen=max_items)
        self._lock = threading.Lock()

    def add(self, message: str, color: str = TXT_SECOND):
        with self._lock:
            self._items.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "msg": message,
                "color": color,
            })

    def get_recent(self, n: int = 10) -> list[dict]:
        with self._lock:
            return list(self._items)[-n:]

    def clear(self):
        with self._lock:
            self._items.clear()


# ================================================================
# DISCOVERY PIPELINE TRACKER
# ================================================================

class PipelineTracker:
    PHASES = [
        ("literature_search",  "Literature Search"),
        ("paper_retrieval",    "Paper Retrieval"),
        ("entity_extraction",  "Entity Extraction"),
        ("knowledge_graph",    "Knowledge Graph"),
        ("contradiction_mine", "Contradiction Mining"),
        ("hypothesis_gen",     "Hypothesis Generation"),
        ("skeptic_review",     "Skeptic Review"),
        ("experiment_plan",    "Experiment Planning"),
        ("novelty_check",      "Novelty Check"),
        ("report_gen",         "Report Generation"),
    ]

    def __init__(self):
        self._phases: dict[str, str] = {}
        self._current: str = ""
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            for pid, _ in self.PHASES:
                self._phases[pid] = "pending"
            self._current = ""

    def start_phase(self, phase_id: str):
        with self._lock:
            found = False
            for pid, _ in self.PHASES:
                if pid == phase_id:
                    found = True
                    self._phases[pid] = "running"
                    self._current = pid
                elif not found and self._phases.get(pid) == "running":
                    self._phases[pid] = "done"
            if not found:
                self._phases[phase_id] = "running"
                self._current = phase_id

    def complete_phase(self, phase_id: str):
        with self._lock:
            self._phases[phase_id] = "done"
            if self._current == phase_id:
                self._current = ""

    def error_phase(self, phase_id: str):
        with self._lock:
            self._phases[phase_id] = "error"

    def all_done(self) -> bool:
        with self._lock:
            return all(v in ("done", "error") for v in self._phases.values())

    def get_display(self) -> list[tuple[str, str, str]]:
        with self._lock:
            result = []
            for pid, label in self.PHASES:
                status = self._phases.get(pid, "pending")
                if status == "done":
                    result.append((label, "done", ACCENT_GREEN))
                elif status == "running":
                    result.append((label, "running", ACCENT_BLUE))
                elif status == "error":
                    result.append((label, "error", ACCENT_RED))
                else:
                    result.append((label, "pending", TXT_DIM))
            return result

    def get_progress_pct(self) -> int:
        with self._lock:
            done = sum(1 for v in self._phases.values() if v == "done")
            return int(done / len(self.PHASES) * 100) if self.PHASES else 0


# ================================================================
# TOOL CALL TRACKER
# ================================================================

class ToolCallTracker:
    def __init__(self):
        self._calls: deque = deque(maxlen=50)
        self._lock = threading.Lock()

    def start(self, tool_name: str, query: str = ""):
        with self._lock:
            self._calls.append({
                "name": tool_name,
                "query": query,
                "status": "running",
                "start": time.time(),
                "result": "",
            })

    def complete(self, tool_name: str, result: str = ""):
        with self._lock:
            for call in reversed(self._calls):
                if call["name"] == tool_name and call["status"] == "running":
                    call["status"] = "done"
                    call["result"] = result
                    call["elapsed"] = time.time() - call["start"]
                    break

    def error(self, tool_name: str, error: str = ""):
        with self._lock:
            for call in reversed(self._calls):
                if call["name"] == tool_name and call["status"] == "running":
                    call["status"] = "error"
                    call["result"] = error
                    call["elapsed"] = time.time() - call["start"]
                    break

    def get_recent(self, n: int = 10) -> list[dict]:
        with self._lock:
            return list(self._calls)[-n:]


# ================================================================
# KNOWLEDGE GRAPH METRICS
# ================================================================

class GraphMetrics:
    def __init__(self):
        self.nodes = 0
        self.edges = 0
        self.clusters = 0
        self.contradictions = 0
        self.novelty_candidates = 0
        self.papers = 0
        self.entities = 0
        self.relationships = 0
        self._lock = threading.Lock()

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "nodes": self.nodes,
                "edges": self.edges,
                "clusters": self.clusters,
                "contradictions": self.contradictions,
                "novelty_candidates": self.novelty_candidates,
                "papers": self.papers,
                "entities": self.entities,
                "relationships": self.relationships,
            }


# ================================================================
# COMMAND PALETTE
# ================================================================

COMMAND_PALETTE_ITEMS = [
    ("discover", "Run Discovery Pipeline", "/discover "),
    ("grounded", "Grounded Discovery", "/grounded "),
    ("search",   "Search Papers", "/search "),
    ("hypothesize", "Generate Hypotheses", "/hypothesize "),
    ("experiment", "Design Experiment", "/experiment"),
    ("review",   "Peer Review", "/review"),
    ("graph",    "Knowledge Graph Stats", "/graph"),
    ("science",  "Scientist Modules", "/science"),
    ("domains",  "List Domains", "/domains"),
    ("status",   "System Status", "/status"),
    ("timeline", "Session Timeline", "/timeline"),
    ("clear",    "Clear Screen", "/clear"),
    ("think",    "Toggle Think Mode", "/think"),
    ("dive",     "Toggle Deep Dive", "/dive"),
    ("dashboard", "Open Dashboard", "/dashboard"),
    ("enrich",   "Enrich Knowledge Graph", "/enrich"),
    ("contradictions", "Find Contradictions", "/contradictions"),
    ("generate", "Generate Molecules/Materials", "/generate "),
]


# ================================================================
# PREMIUM RUMI UI
# ================================================================

class RumiUI:
    """Premium AI operating system terminal UI for RUMI Scientist AI."""

    def __init__(self, face_path=None, size=None):
        self.W = None
        self.H = None

        # State
        self.speaking = False
        self._think_mode = False
        self._deep_dive_active = False
        self._rumi_state = "READY"
        self.status_text = "READY"
        self._start_time = time.time()
        self._personality = "professional"
        self._discovery_running = False
        self._discovery_step = ""
        self._discovery_topic = ""

        # Callbacks
        self.on_text_command = None
        self.on_discovery_command = None
        self.on_think_mode_toggle = None
        self.on_deep_dive_toggle = None
        self.on_idle_scan = None

        # Threading
        self._running = True
        self._input_lock = threading.Lock()

        # Interrupt
        self._interrupt_requested = threading.Event()
        self._is_busy = False

        # Idle Scan
        self._last_input_time = time.time()
        self._last_idle_scan_time = 0.0
        self._idle_thread = threading.Thread(target=self._idle_monitor, daemon=True)
        self._idle_thread.start()
        self._message_queue_count = 0
        self._current_spin_idx = 0
        self._current_word_idx = 0

        # Input history
        self._pt_history = InMemoryHistory() if HAVE_PT else None
        self._message_count = 0

        # Session tracking
        self._timeline = SessionTimeline()
        self._pipeline = PipelineTracker()
        self._tool_calls = ToolCallTracker()
        self._graph_metrics = GraphMetrics()
        self._activity_feed = ActivityFeed()

        # Token tracking
        self._total_tokens = 0
        self._total_cost = 0.0
        self._last_latency = 0.0

        # Status bar updater
        self._status_thread = threading.Thread(target=self._status_updater, daemon=True)
        self._status_thread.start()

        # Face ticker state
        self._face_idx = 0
        self._face_tick = 0.25  # seconds between face changes

        # Thinking content buffer
        self._thinking_content = []
        self._thinking_active = False
        self._tool_trail = []  # [{name, query, status, elapsed, result}]

        # Animated Startup
        self._show_boot_sequence()

        # Check API keys
        self._api_key_ready = _api_keys_exist()
        if not self._api_key_ready:
            self._show_setup_ui()

        # Start input reader
        self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self._input_thread.start()

        # Start heartbeat
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

        # Timeline entry
        self._timeline.add("system", "RUMI initialized", "Model: Gemini 2.5 Flash")

    # ----------------------------------------------------------------
    # BOOT SEQUENCE (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_boot_sequence(self):
        """Clean boot with ASCII logo and role preview."""
        console.clear()

        from discovery.llm_client import get_status
        status = get_status()
        groq_ok = status.get("groq", {}).get("available", False)
        gemini_ok = status.get("gemini", {}).get("available", False)
        groq_keys = status.get("groq", {}).get("keys", 0)
        gemini_keys = status.get("gemini", {}).get("keys", 0)

        # ASCII Logo in cyan
        console.print()
        console.print(Text(RUMI_LOGO, style=f"bold {ACCENT_CYAN}"))
        console.print(Text("  Research Unified Machine Intelligence", style=ACCENT_BLUE))
        console.print()

        # Provider status — one line
        line = Text()
        line.append("  ●", style=ACCENT_GREEN if groq_ok else ACCENT_RED)
        line.append(f" Groq ({groq_keys})", style=TXT_PRIMARY)
        line.append("  ", style=TXT_SECOND)
        line.append("●", style=ACCENT_GREEN if gemini_ok else ACCENT_RED)
        line.append(f" Gemini ({gemini_keys})", style=TXT_PRIMARY)
        line.append("  │  ", style=TXT_SECOND)
        line.append("17 domains", style=TXT_SECOND)
        line.append("  │  ", style=TXT_SECOND)
        line.append("48 modules", style=TXT_SECOND)
        console.print(line)
        console.print()

        # Role preview
        for role_name, role in ROLES.items():
            line = Text()
            line.append(f"  {role['glyph']} ", style=f"bold {role['color']}")
            line.append(f"[{role['label']}]", style=f"bold {role['color']}")
            line.append(f" — {role_name} messages", style=TXT_SECOND)
            console.print(line)
        console.print()

    # ----------------------------------------------------------------
    # HEADER PANEL (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_header_panel(self):
        """Minimal header — just uptime and tokens."""
        uptime = self._get_uptime()
        line = Text()
        line.append("RUMI", style=f"bold {ACCENT_CYAN}")
        line.append(f"  {uptime}", style=TXT_SECOND)
        line.append(f"  {self._total_tokens:,} tok", style=TXT_SECOND)
        if self._get_mode_str() != "normal":
            line.append(f"  {self._get_mode_str()}", style=ACCENT_PURPLE)
        console.print(line)

    def _get_uptime(self) -> str:
        elapsed = int(time.time() - self._start_time)
        return f"{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d}"

    def _get_mode_str(self) -> str:
        modes = []
        if self._think_mode:
            modes.append("think")
        if self._deep_dive_active:
            modes.append("dive")
        return " ".join(modes) if modes else "normal"

    # ----------------------------------------------------------------
    # ACTIVITY FEED (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_activity_feed(self):
        """Compact event stream."""
        events = self._activity_feed.get_recent(6)
        if not events:
            return

        for ev in events:
            line = Text()
            line.append(f"  {ev['time']} ", style=TXT_SECOND)
            line.append(ev["msg"], style=ev["color"])
            console.print(line)

    # ----------------------------------------------------------------
    # DISCOVERY DASHBOARD (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_discovery_dashboard(self, topic: str = ""):
        """Discovery checklist."""
        pct = self._pipeline.get_progress_pct()
        bar = _make_progress_bar(pct, 10)

        console.print()
        console.print(Text(f"[DISCOVERY] {topic[:60]}", style=ACCENT_CYAN))
        line = Text()
        line.append(f"  {bar} ", style=TXT_SECOND)
        line.append(f"{self._graph_metrics.papers} papers", style=TXT_SECOND)
        line.append(f"  {self._graph_metrics.entities} entities", style=TXT_SECOND)
        line.append(f"  {self._graph_metrics.edges} edges", style=TXT_SECOND)
        console.print(line)

    # ----------------------------------------------------------------
    # THINKING ANIMATION (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_thinking_animation(self, message: str = ""):
        """Tree-style thinking indicator."""
        verb = message or "thinking"
        console.print(Text(f"  ├─ {verb}…", style=ACCENT_CYAN))

    # ----------------------------------------------------------------
    # INPUT BOX (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_input_box(self):
        """Minimal — no input hint."""
        pass

    # ----------------------------------------------------------------
    # PANELS (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_panel(self, title: str, content: str, color: str = BORDER_NORMAL):
        """Minimal panel."""
        console.print(Text(f"{title}: {content}", style=TXT_SECOND))

    def _show_dream_panel(self):
        """No dream panel noise."""
        pass

    def _show_sidebar(self):
        """No sidebar noise."""
        pass

    # ----------------------------------------------------------------
    # STATUS UPDATER
    # ----------------------------------------------------------------
    def _status_updater(self):
        """Status updater with spinner rotation and face ticker."""
        verb_idx = 0
        indicator = INDICATOR_STYLES[INDICATOR_STYLE]
        tick = indicator["tick"]

        while self._running:
            self._current_spin_idx = (self._current_spin_idx + 1) % len(SPINNER_CHARS)
            verb_idx = (verb_idx + 1) % len(THINKING_VERBS)
            # Rotate face when busy
            if self._is_busy or self._discovery_running:
                self._face_idx = (self._face_idx + 1) % len(FACES)
            time.sleep(tick)

    # ----------------------------------------------------------------
    # CONTEXT BAR (Hermes Agent style)
    # ----------------------------------------------------------------
    def _get_context_bar(self, tokens_used: int = 0, max_tokens: int = 200000) -> str:
        """Context bar: [████░░░░░░] 40%"""
        pct = min(100, int((tokens_used / max_tokens) * 100))
        filled = int(pct / 10)
        empty = 10 - filled
        bar = "█" * filled + "░" * empty

        # Color thresholds
        if pct < 50:
            color = "#00E676"  # Green - plenty of room
        elif pct < 80:
            color = "#FFD600"  # Amber - getting full
        elif pct < 95:
            color = "#FF9100"  # Orange - approaching limit
        else:
            color = "#FF1744"  # Red - near overflow

        return f"<style fg='{color}'>[{bar}] {pct}%</style>"

    # ----------------------------------------------------------------
    # TOOLBAR (Hermes Agent style)
    # ----------------------------------------------------------------
    def _get_toolbar(self):
        """Live-updating status bar — called by prompt_toolkit on every keypress."""
        elapsed = int(time.time() - self._start_time)
        uptime = f"{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d}"

        parts = []

        # Face ticker (animated when busy)
        if self._is_busy or self._discovery_running:
            face = FACES[self._face_idx % len(FACES)]
            verb = self._discovery_step or THINKING_VERBS_HERMES[self._face_idx % len(THINKING_VERBS_HERMES)]
            parts.append(f"{face} {verb}…")
        else:
            parts.append("● ready")

        parts.append(" │ ")

        # Model
        parts.append("Gemini 2.5")

        # Context bar — always show
        pct = min(100, int((self._total_tokens / 200000) * 100))
        filled = int(pct / 10)
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        parts.append(" │ ")
        parts.append(f"[{bar}] {pct}%")

        # Tokens
        parts.append(" │ ")
        parts.append(f"{self._total_tokens:,} tok")

        # Cost (if > 0)
        if self._total_cost > 0:
            parts.append(" │ ")
            parts.append(f"${self._total_cost:.4f}")

        # Uptime — always show
        parts.append(" │ ")
        parts.append(uptime)

        # Mode badges
        if self._think_mode:
            parts.append(" │ think")
        if self._deep_dive_active:
            parts.append(" │ dive")

        # Tool trail count (if active)
        if self._tool_trail:
            active_tools = sum(1 for t in self._tool_trail if t["status"] == "running")
            if active_tools > 0:
                parts.append(f" │ ⚡{active_tools}")

        result = "".join(parts)

        if HAVE_PT:
            return HTML(self._toolbar_to_html(result))
        return result

    def _toolbar_to_html(self, text: str) -> str:
        """HTML toolbar with subtle border and color-coded sections."""
        html = text
        # Status face/text
        if "● ready" in html:
            html = html.replace("● ready",
                "<style bg='#1a1a1a' fg='#00E676'> ● ready </style>")
        else:
            # busy face/verb — cyan highlight
            _busy_match = _re.search(r'([^\s]+)\s(\S+)…', html)
            if _busy_match:
                html = html.replace(_busy_match.group(),
                    f"<style bg='#0d1b2a' fg='#00BCD4'>{_busy_match.group()}</style>")
        # Model
        html = html.replace("Gemini 2.5",
            "<style bg='#1a1a1a' fg='#2979FF'>Gemini 2.5</style>")
        # Context bar — color by percentage
        ctx_match = _re.search(r'\[([█░]+)\]\s*(\d+)%', html)
        if ctx_match:
            pct = int(ctx_match.group(2))
            if pct < 50:
                color = '#00E676'
            elif pct < 80:
                color = '#FFD600'
            elif pct < 95:
                color = '#FF9100'
            else:
                color = '#FF1744'
            html = html.replace(ctx_match.group(),
                f"<style bg='#1a1a1a' fg='{color}'>{ctx_match.group()}</style>")
        # Tokens
        tok_match = _re.search(r'(\d[\d,]* tok)', html)
        if tok_match:
            html = html.replace(tok_match.group(),
                f"<style bg='#1a1a1a' fg='#EAEAEA'>{tok_match.group()}</style>")
        # Cost
        cost_match = _re.search(r'\$[\d.]+', html)
        if cost_match:
            html = html.replace(cost_match.group(),
                f"<style bg='#1a1a1a' fg='#FFD600'>{cost_match.group()}</style>")
        # Uptime — dim gray
        time_match = _re.search(r'(\d{2}:\d{2}:\d{2})', html)
        if time_match:
            html = html.replace(time_match.group(),
                f"<style bg='#1a1a1a' fg='#666666'>{time_match.group()}</style>")
        # Separators — subtle
        html = html.replace("│",
            "<style bg='#1a1a1a' fg='#333333'> │ </style>")
        return html

    def _get_context_bar_text(self, tokens_used: int = 0, max_tokens: int = 200000) -> str:
        """Context bar as plain text: [████░░░░░░] 40%"""
        pct = min(100, int((tokens_used / max_tokens) * 100))
        filled = int(pct / 10)
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {pct}%"

    def interrupt_requested(self):
        return self._interrupt_requested.is_set()

    def clear_interrupt(self):
        self._interrupt_requested.clear()

    # ----------------------------------------------------------------
    # IDLE MONITOR
    # ----------------------------------------------------------------
    def _idle_monitor(self):
        while self._running:
            idle_time = time.time() - self._last_input_time
            time_since_last_scan = time.time() - self._last_idle_scan_time
            if idle_time > 30 and time_since_last_scan > 3600:
                self._last_idle_scan_time = time.time()
                if self.on_idle_scan:
                    self.on_idle_scan()
            time.sleep(10)

    # ----------------------------------------------------------------
    # INPUT LOOP
    # ----------------------------------------------------------------
    def _input_loop(self):
        pt_style = PtStyle([
            ('prompt', f'bold {ACCENT_BLUE}'),
        ]) if HAVE_PT else None

        kb = KeyBindings() if HAVE_PT else None
        if kb:
            @kb.add('escape')
            def _(event):
                self._interrupt_requested.set()

            @kb.add('c-c')
            def _(event):
                self._interrupt_requested.set()
                event.app.exit(exception=KeyboardInterrupt)

            @kb.add('c-k')
            def _(event):
                self._show_command_palette()

            @kb.add('c-l')
            def _(event):
                self._handle_command("/clear")

            @kb.add('c-r')
            def _(event):
                self._handle_command("/search ")

            @kb.add('c-d')
            def _(event):
                self._handle_command("/discover ")

            @kb.add('c-g')
            def _(event):
                self._handle_command("/graph")

        _pt_failed = False  # Track if prompt_toolkit failed once
        while self._running:
            try:
                # Print status bar before prompt when no prompt_toolkit
                if not HAVE_PT or _pt_failed:
                    self._print_status_bar()

                if HAVE_PT and not _pt_failed and self._pt_history is not None:
                    from prompt_toolkit.completion import WordCompleter
                    _completer = WordCompleter(SLASH_COMMANDS, ignore_case=True)
                    value = _pt_prompt(
                        PROMPT_SYMBOL + " ",
                        history=self._pt_history,
                        style=pt_style,
                        completer=_completer,
                        complete_while_typing=True,
                        bottom_toolbar=self._get_toolbar,
                        key_bindings=kb,
                    )
                else:
                    value = input(PROMPT_SYMBOL + " ")

                value = value.strip()
                if not value:
                    continue

                if value.startswith("/"):
                    self._handle_command(value)
                    continue

                if self.on_text_command:
                    self._last_input_time = time.time()
                    self._message_count += 1
                    self._timeline.add("user", f"Query: {value[:60]}...")
                    self._activity_feed.add(f"User query: {value[:40]}", ACCENT_BLUE)
                    # Echo user message with role glyph
                    role = ROLES["user"]
                    console.print()
                    line = Text()
                    line.append(f"  {role['glyph']} ", style=f"bold {role['color']}")
                    line.append(f"[{role['label']}] ", style=f"bold {role['color']}")
                    line.append(value, style=role["color"])
                    console.print(line)
                    self.show_thinking()
                    threading.Thread(target=self.on_text_command, args=(value,), daemon=True).start()

            except (EOFError, KeyboardInterrupt):
                console.print()
                self._handle_command("/exit")
                break
            except Exception:
                # prompt_toolkit can't render in this terminal — fall back to input()
                _pt_failed = True
                continue

    # ----------------------------------------------------------------
    # COMMAND PALETTE (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_command_palette(self):
        """Command palette."""
        console.print()
        console.print(Text("  [COMMANDS]", style=f"bold {ACCENT_CYAN}"))
        console.print()
        for i, (key, label, cmd) in enumerate(COMMAND_PALETTE_ITEMS):
            line = Text()
            line.append(f"  {i+1:2d} ", style=TXT_SECOND)
            line.append(f"{label}", style=TXT_PRIMARY)
            line.append(f"  {cmd}", style=ACCENT_BLUE)
            console.print(line)
        console.print()
        console.print(Text(f"  Type number or command directly", style=TXT_SECOND))
        console.print()

    # ----------------------------------------------------------------
    # COMMAND HANDLER
    # ----------------------------------------------------------------
    def _handle_command(self, cmd: str):
        self._last_input_time = time.time()
        cmd = cmd.lower().strip()

        if cmd == "/help":
            console.print()
            console.print(Markdown(HELP_TEXT))
            console.print()

        elif cmd == "/clear":
            console.clear()
            self._show_boot_sequence()

        elif cmd == "/think":
            self._think_mode = not self._think_mode
            state = "ON" if self._think_mode else "OFF"
            color = ACCENT_GREEN if self._think_mode else TXT_MUTED
            badge = _make_status_badge(f"THINK {state}", color)
            console.print(Text("  ", style=""), end="")
            console.print(badge)
            if self.on_think_mode_toggle:
                threading.Thread(target=self.on_think_mode_toggle, args=(self._think_mode,), daemon=True).start()
            self._timeline.add("mode", f"Think mode: {state}")

        elif cmd == "/dive":
            self._deep_dive_active = not self._deep_dive_active
            state = "ON" if self._deep_dive_active else "OFF"
            color = ACCENT_TEAL if self._deep_dive_active else TXT_MUTED
            badge = _make_status_badge(f"DIVE {state}", color)
            console.print(Text("  ", style=""), end="")
            console.print(badge)
            if self.on_deep_dive_toggle:
                threading.Thread(target=self.on_deep_dive_toggle, args=(self._deep_dive_active,), daemon=True).start()
            self._timeline.add("mode", f"Deep dive: {state}")

        elif cmd == "/status":
            self._show_status_panel()

        elif cmd == "/stats":
            self._show_stats()

        elif cmd == "/timeline":
            self._show_timeline()

        elif cmd == "/science":
            self._show_science_help()

        elif cmd.startswith("/discover "):
            args = cmd[len("/discover "):].strip()
            self._start_discovery("discover", args)

        elif cmd == "/discover":
            console.print(Text("  usage: /discover <topic>", style=TXT_MUTED))

        elif cmd.startswith("/grounded "):
            args = cmd[len("/grounded "):].strip()
            self._start_discovery("grounded", args)

        elif cmd == "/grounded":
            console.print(Text("  usage: /grounded <topic>", style=TXT_MUTED))

        elif cmd.startswith("/search "):
            args = cmd[len("/search "):].strip()
            self._start_discovery("search", args)

        elif cmd.startswith("/hypothesize "):
            args = cmd[len("/hypothesize "):].strip()
            self._start_discovery("hypothesize", args)

        elif cmd == "/hypothesize":
            console.print(Text("  usage: /hypothesize <topic>", style=TXT_MUTED))

        elif cmd.startswith("/generate "):
            args = cmd[len("/generate "):].strip()
            self._start_discovery("generate", args)

        elif cmd == "/generate":
            console.print(Text("  usage: /generate <target>", style=TXT_MUTED))

        elif cmd == "/contradictions":
            self._start_discovery("contradictions", "")

        elif cmd == "/enrich":
            self._start_discovery("enrich", "")

        elif cmd == "/graph":
            self._start_discovery("graph", "")

        elif cmd == "/dashboard":
            self._start_discovery("dashboard", "")

        elif cmd == "/discoveries":
            self._start_discovery("discoveries", "")

        elif cmd.startswith("/domain "):
            args = cmd[len("/domain "):].strip()
            self._start_discovery("domain", args)

        elif cmd == "/domain":
            self._start_discovery("domain", "")

        elif cmd == "/experiment":
            self._show_tool_call("Experiment Designer", "Designing experiment...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Help me design a scientific experiment. What hypothesis should I test?",),
                    daemon=True,
                ).start()

        elif cmd == "/papers":
            self._show_tool_call("Paper Search", "Searching literature...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Search for academic papers. Who or what topic should I search for?",),
                    daemon=True,
                ).start()

        elif cmd == "/review":
            self._show_tool_call("Peer Review", "Reviewing claim...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Perform a peer review on a paper or scientific claim.",),
                    daemon=True,
                ).start()

        elif cmd == "/notebook":
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Show my recent lab notebook entries and stats.",),
                    daemon=True,
                ).start()

        elif cmd == "/domains":
            self._show_domains()

        elif cmd.startswith("/reason "):
            args = cmd[len("/reason "):].strip()
            self._start_discovery("reason", args)

        elif cmd.startswith("/theorize "):
            args = cmd[len("/theorize "):].strip()
            self._start_discovery("theorize", args)

        # === NEW: Simulation, Debate, Continuous, Transfer, Curiosity ===
        elif cmd.startswith("/simulate "):
            args = cmd[len("/simulate "):].strip()
            self._start_discovery("simulate", args)

        elif cmd == "/simulate":
            console.print(Text("  usage: /simulate <hypothesis>", style=TXT_MUTED))

        elif cmd.startswith("/debate "):
            args = cmd[len("/debate "):].strip()
            self._start_discovery("debate", args)

        elif cmd == "/debate":
            console.print(Text("  usage: /debate <hypothesis>", style=TXT_MUTED))

        elif cmd.startswith("/continuous"):
            args = cmd[len("/continuous"):].strip()
            self._start_discovery("continuous", args)

        elif cmd.startswith("/transfer "):
            args = cmd[len("/transfer "):].strip()
            self._start_discovery("transfer", args)

        elif cmd == "/transfer":
            console.print(Text("  usage: /transfer <domain>:<mechanism> to <domain>", style=TXT_MUTED))

        elif cmd == "/curiosity":
            self._start_discovery("curiosity", "")

        elif cmd == "/evolve":
            self._start_discovery("evolve", "")

        elif cmd == "/consistency":
            self._start_discovery("consistency", "")

        elif cmd == "/personality":
            self._handle_personality()

        elif cmd == "/exit":
            console.print()
            console.print(Text("  Shutting down RUMI...", style=f"bold {ACCENT_RED}"))
            console.print()
            self._show_session_summary()
            self._running = False
            _reset_terminal_bg()
            time.sleep(0.3)
            sys.exit(0)

        else:
            suggestions = []
            clean_cmd = cmd.strip().lower()
            for sc in SLASH_COMMANDS:
                if clean_cmd in sc or sc in clean_cmd:
                    suggestions.append(sc)
            console.print()
            if suggestions:
                console.print(Text(f"  Unknown command: {cmd}", style=ACCENT_RED))
                console.print(Text(f"  Did you mean: {', '.join(suggestions[:3])}?", style=ACCENT_AMBER))
            else:
                console.print(Text(f"  Unknown command: {cmd}", style=ACCENT_RED))
                console.print(Text(f"  Type /help for available commands", style=TXT_MUTED))
            console.print()

    # ----------------------------------------------------------------
    # DISCOVERY STARTER
    # ----------------------------------------------------------------
    def _start_discovery(self, mode: str, args: str):
        self._discovery_running = True
        self._discovery_topic = args
        self._pipeline.reset()
        self._timeline.add("discovery", f"{mode}: {args[:50]}..." if args else mode)
        self._activity_feed.add(f"discovery: {mode}", ACCENT_PURPLE)

        console.print()
        self._show_discovery_dashboard(args)

        if self.on_discovery_command:
            threading.Thread(target=self.on_discovery_command, args=(mode, args), daemon=True).start()

    # ----------------------------------------------------------------
    # TOOL CALL DISPLAY (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_tool_call(self, name: str, query: str = ""):
        """Tool call with tree display and trail tracking."""
        self._tool_calls.start(name, query)
        self._activity_feed.add(f"{name}", ACCENT_TEAL)

        # Track in tool trail
        self._tool_trail.append({
            "name": name,
            "query": query,
            "status": "running",
            "start_time": time.time(),
            "elapsed": 0,
            "result": "",
        })

        # Get tool-specific verb if available
        tool_verb = TOOL_VERBS.get(name.lower(), "processing")
        face = FACES[self._face_idx % len(FACES)]

        line = Text()
        line.append("  ├─ ", style=TXT_SECOND)
        line.append(f"{face} ", style=ACCENT_CYAN)
        line.append(f"{name}", style=f"bold {ACCENT_CYAN}")
        if query:
            short = query[:40] + "..." if len(query) > 40 else query
            line.append(f" {short}", style=TXT_SECOND)
        console.print(line)

    def complete_tool_call(self, name: str, result: str = ""):
        """Tool completion with duration and trail update."""
        self._tool_calls.complete(name, result)

        elapsed = 0
        for call in reversed(self._tool_calls.get_recent(5)):
            if call["name"] == name and call.get("elapsed"):
                elapsed = call["elapsed"]
                break

        # Update tool trail
        for tool in reversed(self._tool_trail):
            if tool["name"] == name and tool["status"] == "running":
                tool["status"] = "done"
                tool["elapsed"] = elapsed
                tool["result"] = result
                break

        line = Text()
        line.append("  └─ ", style=TXT_SECOND)
        line.append(f"✓ ", style=f"bold {ACCENT_GREEN}")
        line.append(f"{name}", style=f"bold {ACCENT_GREEN}")
        if elapsed:
            line.append(f" ({elapsed:.1f}s)", style=TXT_SECOND)
        if result:
            short = result[:50] + "..." if len(result) > 50 else result
            line.append(f"  {short}", style=TXT_SECOND)
        console.print(line)

        # Clean up trail when all tools done
        if not any(t["status"] == "running" for t in self._tool_trail):
            self._tool_trail = []

    # ----------------------------------------------------------------
    # STATUS (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_status_panel(self):
        """Minimal status."""
        uptime = self._get_uptime()
        console.print()
        line = Text()
        line.append("RUMI", style=f"bold {ACCENT_CYAN}")
        line.append(f"  {uptime}", style=TXT_SECOND)
        line.append(f"  {self._total_tokens:,} tok", style=TXT_SECOND)
        line.append(f"  {self._message_count} msgs", style=TXT_SECOND)
        console.print(line)
        console.print()

    def _show_stats(self):
        """Minimal stats."""
        uptime = int(time.time() - self._start_time)
        line = Text()
        line.append("stats", style=TXT_SECOND)
        line.append(f"  {uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}", style=TXT_PRIMARY)
        line.append(f"  {self._message_count} msgs", style=TXT_SECOND)
        line.append(f"  {self._graph_metrics.nodes} nodes", style=TXT_SECOND)
        line.append(f"  {self._graph_metrics.edges} edges", style=TXT_SECOND)
        console.print(line)

    # ----------------------------------------------------------------
    # TIMELINE DISPLAY (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_timeline(self):
        """Compact timeline."""
        events = self._timeline.get_events(last_n=10)

        if not events:
            console.print(Text("  No events yet.", style=TXT_SECOND))
            return

        for ev in events:
            type_color = {
                "system": ACCENT_BLUE,
                "user": ACCENT_CYAN,
                "discovery": ACCENT_GREEN,
                "mode": ACCENT_PURPLE,
                "tool": ACCENT_AMBER,
                "error": ACCENT_RED,
            }.get(ev["type"], TXT_SECOND)

            line = Text()
            line.append(f"  {ev['time']} ", style=TXT_SECOND)
            line.append(f"{ev['desc']}", style=type_color)
            console.print(line)

    # ----------------------------------------------------------------
    # SESSION SUMMARY (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_session_summary(self):
        """Compact session summary."""
        uptime = int(time.time() - self._start_time)
        line = Text()
        line.append("  session ", style=TXT_SECOND)
        line.append(f"{uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}", style=TXT_PRIMARY)
        line.append(f"  {self._message_count} msgs", style=TXT_SECOND)
        line.append(f"  {self._total_tokens:,} tok", style=TXT_SECOND)
        line.append(f"  ${self._total_cost:.4f}", style=ACCENT_GREEN)
        console.print(line)

    # ----------------------------------------------------------------
    # HEARTBEAT
    # ----------------------------------------------------------------
    def _heartbeat_loop(self):
        """Heartbeat with face ticker rotation."""
        while self._running:
            if self._rumi_state in ("THINKING", "PROCESSING"):
                self._face_idx = (self._face_idx + 1) % len(FACES)
                time.sleep(0.25)
            else:
                time.sleep(1)

    def _print_status_bar(self):
        """Print status bar (ANSI fallback when no prompt_toolkit)."""
        elapsed = int(time.time() - self._start_time)
        uptime = f"{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d}"

        if HAVE_RICH:
            status = Text()
            status.append("┌", style=TXT_SECOND)
            status.append("─" * 76, style=TXT_SECOND)
            status.append("┐", style=TXT_SECOND)
            console.print(status)
            line = Text()
            line.append("  ", style="")
            line.append("● ready", style=ACCENT_GREEN)
            line.append(" │ ", style=TXT_SECOND)
            line.append("Gemini 2.5", style=ACCENT_BLUE)
            pct = min(100, int((self._total_tokens / 200000) * 100))
            filled = int(pct / 10)
            empty = 10 - filled
            bar = "█" * filled + "░" * empty
            color = ACCENT_GREEN if pct < 50 else ACCENT_AMBER
            line.append(" │ ", style=TXT_SECOND)
            line.append(f"[{bar}] {pct}%", style=color)
            line.append(" │ ", style=TXT_SECOND)
            line.append(f"{self._total_tokens:,} tok", style=TXT_PRIMARY)
            line.append(" │ ", style=TXT_SECOND)
            line.append(uptime, style=TXT_SECOND)
            console.print(line)
            end = Text()
            end.append("└", style=TXT_SECOND)
            end.append("─" * 76, style=TXT_SECOND)
            end.append("┘", style=TXT_SECOND)
            console.print(end)
        else:
            # ANSI fallback
            g = _ansi(ACCENT_GREEN)
            b = _ansi(ACCENT_BLUE)
            d = _ansi(TXT_SECOND)
            w = _ansi(TXT_PRIMARY)
            r = _RESET
            pct = min(100, int((self._total_tokens / 200000) * 100))
            filled = int(pct / 10)
            empty = 10 - filled
            bar = "█" * filled + "░" * empty
            color = g if pct < 50 else _ansi(ACCENT_AMBER)
            print(f"{d}┌{'─' * 76}┐{r}")
            print(f"  {g}● ready{r} {d}│{r} {b}Gemini 2.5{r} {d}│{r} {color}[{bar}] {pct}%{r} {d}│{r} {w}{self._total_tokens:,} tok{r} {d}│{r} {d}{uptime}{r}")
            print(f"{d}└{'─' * 76}┘{r}")
            sys.stdout.write("".join(parts) + "\n")
            sys.stdout.flush()

    def show_thinking(self, message: str = ""):
        """Start animated thinking display."""
        verb = message or random.choice(THINKING_VERBS_HERMES)
        self._thinking_active = True
        self._thinking_verb = verb
        self._thinking_dots = 0
        # Start animation thread
        threading.Thread(target=self._thinking_animation, daemon=True).start()

    def _thinking_animation(self):
        """Animate thinking: cycling faces + growing dots."""
        if HAVE_RICH:
            try:
                from rich.live import Live
                with Live(console=console, refresh_per_second=4, transient=True) as live:
                    while self._thinking_active:
                        face = FACES[self._face_idx % len(FACES)]
                        dots = "." * (self._thinking_dots % 4 + 1)
                        verb = self._thinking_verb
                        line = Text()
                        line.append("  ├─ ", style=TXT_SECOND)
                        line.append(f"{face} ", style=ACCENT_CYAN)
                        line.append(f"{verb}{dots}", style=ACCENT_CYAN)
                        live.update(line)
                        self._thinking_dots += 1
                        time.sleep(0.25)
                return
            except Exception:
                pass
        # ANSI fallback: use \r to animate on same line
        while self._thinking_active:
            face = FACES[self._face_idx % len(FACES)]
            dots = "." * (self._thinking_dots % 4 + 1)
            verb = self._thinking_verb
            line = f"  ├─ {face} {verb}{dots}"
            sys.stdout.write(f"\r{_CLEAR_LINE}{_ansi(ACCENT_CYAN)}{line}{_RESET}")
            sys.stdout.flush()
            self._thinking_dots += 1
            time.sleep(0.3)
        # Clear line when done
        sys.stdout.write(f"\r{_CLEAR_LINE}")
        sys.stdout.flush()

    def stop_thinking(self):
        """Stop thinking animation."""
        self._thinking_active = False

    def show_thinking_content(self, content: str):
        """Display actual thinking/reasoning content."""
        if not content:
            return
        self._thinking_content.append(content)
        # Show as collapsible tree
        for line in content.split("\n")[:5]:  # Show first 5 lines
            line = line.strip()
            if line:
                console.print(Text(f"  │  {line}", style=TXT_MUTED))
        if content.count("\n") > 5:
            console.print(Text(f"  │  …", style=TXT_MUTED))

    def finish_thinking(self):
        """Close thinking section."""
        self._thinking_active = False
        self._thinking_content = []

    def show_done(self, message: str = ""):
        """Minimal done indicator."""
        pass  # No done indicator — response speaks for itself

    # ================================================================
    # PUBLIC API
    # ================================================================

    def write_log(self, text: str):
        """Hermes-style response display with role glyphs and box-drawing."""
        with self._input_lock:
            tl = text.lower().strip()

            # Skip internal noise
            if any(skip in tl for skip in ["[rumi]", "[episodic]", "[selfawareness]",
                                            "[coordinator]", "[dreaming]", "[vectormemory]",
                                            "[telegram]", "non-data parts", "[focus]"]):
                return

            # User input — role glyph + clean echo
            if tl.startswith("you:"):
                content = text[4:].strip()
                role = ROLES["user"]
                self.set_state("PROCESSING")
                console.print()
                line = Text()
                line.append(f"  {role['glyph']} ", style=f"bold {role['color']}")
                line.append(f"[{role['label']}] ", style=f"bold {role['color']}")
                line.append(content, style=role["color"])
                console.print(line)
                self.show_thinking()

            # RUMI response — role glyph + markdown
            elif tl.startswith("rumi:") or tl.startswith("ai:"):
                prefix_len = 5 if tl.startswith("rumi:") else 3
                content = text[prefix_len:].strip()
                # Strip thinking/reasoning headers
                content = _re.sub(r'\*\*Thinking(?:\s*\(.*?\))?\*\*\s*', '', content).strip()
                content = _re.sub(r'\*\*Reasoning\*\*\s*', '', content).strip()
                if content:
                    role = ROLES["assistant"]
                    console.print()
                    line = Text()
                    line.append(f"  {role['glyph']} ", style=f"bold {role['color']}")
                    line.append(f"[{role['label']}]", style=f"bold {role['color']}")
                    console.print(line)
                    # Content
                    try:
                        console.print(Markdown(content))
                    except Exception:
                        console.print(Text(content, style=TXT_PRIMARY))
                    console.print()
                self.finish_thinking()
                self.set_state("IDLE")

            # System messages — role glyph, minimal
            elif tl.startswith("sys:"):
                content = text[4:].strip()
                if any(skip in content.lower() for skip in ["queued", "session", "online", "ended"]):
                    return
                role = ROLES["system"]
                console.print(Text(f"  {role['glyph']} {content}", style=role["color"]))

            # Errors — red, visible
            elif tl.startswith("err:") or tl.startswith("error:"):
                err_msg = text[4:].strip() if ":" in text[4:5] else text[4:].strip()
                console.print(Text(f"  ✗ {err_msg}", style=ACCENT_RED))

            # Security messages
            elif tl.startswith("sec:"):
                sec_msg = text[4:].strip()
                console.print(Text(f"  ⚠ {sec_msg}", style=ACCENT_AMBER))

            # Tool output — role glyph
            elif tl.startswith("tool:"):
                content = text[5:].strip()
                role = ROLES["tool"]
                console.print(Text(f"  {role['glyph']} {content}", style=role["color"]))

            # Discovery output — render as rich markup
            elif tl.startswith("[bold") or tl.startswith("[dim") or tl.startswith("[green") or tl.startswith("[yellow") or tl.startswith("[red"):
                try:
                    console.print(text)
                except Exception:
                    console.print(Text(text, style=TXT_PRIMARY))

            # Everything else — markdown or plain
            else:
                if not text.strip():
                    return
                if any(marker in text for marker in ["**", "## ", "- ", "```", "| ", "1."]):
                    try:
                        console.print(Markdown(text))
                    except Exception:
                        console.print(Text(text, style=TXT_PRIMARY))
                else:
                    console.print(Text(text, style=TXT_PRIMARY))

    def set_state(self, state: str):
        self._rumi_state = state
        self.status_text = state

    def set_discovery_step(self, step: str):
        """Discovery step with inline progress."""
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

        # Step name + inline progress
        pct = self._pipeline.get_progress_pct()
        bar = _make_progress_bar(pct, 8)
        line = Text()
        line.append(f"  ├─ ", style=TXT_SECOND)
        line.append(f"{step} ", style=f"{color}")
        line.append(bar, style=TXT_SECOND)
        console.print(line)

    def set_discovery_done(self):
        self._discovery_running = False
        self._discovery_step = ""
        self._pipeline.reset()
        self._activity_feed.add("Discovery complete", ACCENT_GREEN)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        self.set_state("LISTENING")

    def show_toast(self, message: str, duration: float = 2.5):
        console.print(Text(f"  {message}", style=f"bold {ACCENT_BLUE}"))

    def feed_amplitude(self, amplitude: float):
        pass

    def wait_for_api_key(self):
        while not self._api_key_ready:
            time.sleep(0.1)

    def update_tokens(self, tokens: int, cost: float = 0.0, latency: float = 0.0):
        self._total_tokens += tokens
        self._total_cost += cost
        if latency > 0:
            self._last_latency = latency

    def update_graph_metrics(self, **kwargs):
        self._graph_metrics.update(**kwargs)

    # ----------------------------------------------------------------
    # SCIENCE HELP (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_science_help(self):
        """Compact modules list."""
        console.print()
        modules = [
            ("discovery_engine", "full pipeline"),
            ("tournament_hypothesis", "GFlowNet generation"),
            ("knowledge_graph", "structured knowledge"),
            ("novelty_checker", "novelty check"),
            ("experiment_designer", "experiment design"),
            ("reproducibility", "claim verification"),
            ("active_experiment", "Bayesian selection"),
            ("cross_domain", "cross-field analogies"),
            ("peer_reviewer", "automated review"),
            ("paper_generator", "LaTeX manuscripts"),
            ("research_team", "multi-agent debate"),
            ("feynman_reducer", "first principles"),
            ("cross_validator", "statistical validation"),
            ("scientist_search", "researcher search"),
            ("lab_notebook", "experiment tracking"),
            ("scientific_reasoning", "multi-pass discovery"),
            ("theory_formation", "theory engine"),
            ("simulation_pipeline", "Monte Carlo testing"),
            ("math_consistency", "equation verification"),
            ("multi_agent_debate", "proposer/critic/advocate/synthesizer"),
            ("continuous_operation", "autonomous research loop"),
            ("cross_domain_transfer", "mechanism transfer across fields"),
            ("domain_ontologies", "real physics for 17 domains"),
        ]

        for name, desc in modules:
            line = Text()
            line.append(f"  {name}", style=f"bold {ACCENT_CYAN}")
            line.append(f"  {desc}", style=TXT_SECOND)
            console.print(line)
        console.print()

    def _show_domains(self):
        """Compact domain list."""
        from discovery.domains import list_domains
        from discovery.domain_computational import DOMAIN_COMPUTATIONS

        console.print()
        for d in list_domains():
            key = d["key"]
            has_calc = key in DOMAIN_COMPUTATIONS or key == "space_astronomy"
            calc = " *" if has_calc else ""
            line = Text()
            line.append(f"  {key}", style=f"bold {ACCENT_CYAN}")
            line.append(f"  {d['label']}{calc}", style=TXT_SECOND)
            console.print(line)
        console.print(Text("  /domain <key>  |  /discover <domain>: <topic>", style=TXT_SECOND))
        console.print()

    def _handle_personality(self):
        """Personality selector."""
        console.print()
        console.print(Text(f"  Current: {self._personality}", style=ACCENT_AMBER))
        console.print()

        pers_keys = list(PERSONALITIES.keys())
        for i, k in enumerate(pers_keys):
            p = PERSONALITIES[k]
            console.print(Text(f"  [{i+1}] {p['label']}", style=TXT_PRIMARY))
            console.print(Text(f"      {p['desc']}", style=TXT_SECOND))
        console.print()

        choice = input("  ❯ ").strip()
        try:
            idx = int(choice) - 1
            if idx < 0:
                console.print(Text("  cancelled", style=ACCENT_AMBER))
                return
            chosen = pers_keys[idx]
        except (ValueError, IndexError):
            console.print(Text("  invalid choice", style=ACCENT_RED))
            return

        if _set_personality(chosen):
            self._personality = chosen
            console.print(Text(f"  Switched to {PERSONALITIES[chosen]['label']}", style=ACCENT_GREEN))
            console.print(Text(f"  Takes effect next session", style=ACCENT_AMBER))
        else:
            console.print(Text("  Failed to switch", style=ACCENT_RED))
        console.print()

    # ----------------------------------------------------------------
    # API KEY SETUP (Hermes Agent style)
    # ----------------------------------------------------------------
    def _show_setup_ui(self):
        """First boot setup."""
        console.print()
        console.print(Rule(style=f"bold {ACCENT_PURPLE}"))
        console.print(Text("  FIRST BOOT -- API KEY SETUP", style=f"bold {TXT_PRIMARY}"), justify="center")
        console.print(Rule(style=f"bold {ACCENT_PURPLE}"))
        console.print()

        detected = _detect_os()

        console.print(Text("  Enter your Gemini API key:", style=ACCENT_CYAN))
        console.print(Text("  (Get one at: https://aistudio.google.com/apikey)", style=TXT_SECOND))
        gemini_key = input("  ❯ ").strip()
        while not gemini_key:
            console.print(Text("  API key cannot be empty.", style=f"bold {ACCENT_RED}"))
            gemini_key = input("  ❯ ").strip()

        console.print()

        console.print(Text("  Enter your Groq API key:", style=ACCENT_CYAN))
        console.print(Text("  (Get one at: https://console.groq.com/keys)", style=TXT_SECOND))
        groq_key = input("  ❯ ").strip()
        while not groq_key:
            console.print(Text("  API key cannot be empty.", style=f"bold {ACCENT_RED}"))
            groq_key = input("  ❯ ").strip()

        console.print()

        console.print(Text("  Enter your Cerebras API key:", style=ACCENT_CYAN))
        console.print(Text("  (Get one at: https://cloud.cerebras.ai)", style=TXT_SECOND))
        cerebras_key = input("  ❯ ").strip()
        if not cerebras_key:
            console.print(Text("  Skipped — Cerebras will not be available.", style=TXT_SECOND))
            cerebras_key = ""

        console.print()

        console.print(Text("  Second Groq key (optional, for rate limiting)", style=TXT_SECOND))
        groq_key2 = input("  ❯ ").strip()

        console.print()

        console.print(Text("  Your callsign (default: OPERATOR):", style=ACCENT_CYAN))
        user_name = input("  ❯ ").strip().upper() or "OPERATOR"

        console.print()
        console.print(Text("  Personality:", style=ACCENT_CYAN))
        pers_keys = list(PERSONALITIES.keys())
        for i, k in enumerate(pers_keys):
            p = PERSONALITIES[k]
            console.print(Text(f"  [{i+1}] {p['label']}", style=ACCENT_AMBER))
        pers_choice = input("  ❯ ").strip() or "1"
        try:
            idx = int(pers_choice) - 1
            chosen_pers = pers_keys[idx] if 0 <= idx < len(pers_keys) else "professional"
        except (ValueError, IndexError):
            chosen_pers = "professional"
        _set_personality(chosen_pers)
        self._personality = chosen_pers

        console.print()
        console.print(Text("  Telegram bot? (y/N)", style=TXT_SECOND))
        tg_choice = input("  ❯ ").strip().lower()
        tg_token = ""
        tg_user = ""
        if tg_choice in ("y", "yes"):
            console.print(Text("  Bot token:", style=TXT_PRIMARY))
            tg_token = input("  ❯ ").strip()
            console.print(Text("  User ID:", style=TXT_PRIMARY))
            tg_user = input("  ❯ ").strip()

        console.print()
        console.print(Text("  Optional enrichment keys (enter to skip):", style=TXT_SECOND))

        console.print(Text("  NASA API key:", style=TXT_SECOND))
        nasa_key = input("  ❯ ").strip()

        console.print(Text("  Materials Project key:", style=TXT_SECOND))
        mp_key = input("  ❯ ").strip()

        console.print()
        console.print(Text("  Voice mode: [1] Text only  [2] Text + Voice", style=ACCENT_AMBER))
        vm_choice = input("  ❯ ").strip() or "1"
        voice_enabled = vm_choice == "2"

        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(API_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "primary_provider": "groq",
                "gemini_api_key": gemini_key,
                "gemini_api_key_fallback": "",
                "groq_api_key": groq_key,
                "groq_api_key2": groq_key2,
                "cerebras_api_key": cerebras_key,
                "os_system": detected,
                "camera_index": 0,
                "telegram_bot_token": tg_token,
                "telegram_allowed_user": tg_user,
                "user_name": user_name,
                "personality": chosen_pers,
                "voice_enabled": voice_enabled,
                "nasa_api_key": nasa_key,
                "materials_project_api_key": mp_key,
            }, f, indent=4)

        from brain import model_router as mr_module
        mr_module._router_instance = None

        self._api_key_ready = True
        self.set_state("LISTENING")

        console.print()
        console.print(Text(f"  RUMI online. Welcome, {user_name}.", style=f"bold {ACCENT_GREEN}"))
        console.print()
