"""
ui.py -- RUMI Terminal UI (v8.0 Professional AI Research OS)
Compact, dense, professional. Inspired by Claude Code, OpenCode, Hermes Agent.
Premium dark theme, distinct panels, clean box-drawing, progress indicators.
Every screen maximizes information density while remaining visually clean.
"""

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
# HERMES-STYLE WARM DARK THEME
# ================================================================

# Background layers
BG_DEEP    = "#0d1117"
BG_SECOND  = "#161b22"
BG_PANEL   = "#1c2128"
BG_ELEMENT = "#21262d"
BG_HOVER   = "#30363d"
BG_INPUT   = "#0d1117"

# Text hierarchy
TXT_BRIGHT  = "#f0f6fc"
TXT_PRIMARY = "#c9d1d9"
TXT_SECOND  = "#8b949e"
TXT_MUTED   = "#484f58"
TXT_DIM     = "#30363d"

# Accent palette
ACCENT_CYAN    = "#39d353"
ACCENT_BLUE    = "#58a6ff"
ACCENT_GREEN   = "#39d353"
ACCENT_AMBER   = "#d29922"
ACCENT_RED     = "#f85149"
ACCENT_PURPLE  = "#bc8cff"
ACCENT_TEAL    = "#39d353"
ACCENT_PINK    = "#f778ba"

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
BORDER_SUBTLE  = "#21262d"
BORDER_NORMAL  = "#30363d"
BORDER_ACTIVE  = "#58a6ff"

# Status bar
SB_BG = "#0d1117"
SB_FG = "#8b949e"

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

# Terminal background
_BG_DARK = "#0d1117"
_BG_RESET = "\033[0m"

def _set_terminal_bg():
    """No background transform -- use terminal default."""
    pass

def _reset_terminal_bg():
    """No background reset needed."""
    pass

_set_terminal_bg()

import atexit
atexit.register(_reset_terminal_bg)

# ================================================================
# CONSTANTS
# ================================================================

PROMPT_SYMBOL = "> "
PROMPT_BUSY   = "..."
PROMPT_READY  = "> "

SPINNER_CHARS = "|/-\\"

# Thinking animations
THINKING_MESSAGES = [
    "Thinking...",
    "Analyzing Literature...",
    "Constructing Hypotheses...",
    "Searching Knowledge Graph...",
    "Mining Contradictions...",
    "Synthesizing Evidence...",
    "Validating Claims...",
    "Formulating Reasoning...",
    "Processing Research Data...",
    "Connecting Patterns...",
]

# Status badges
BADGE_ONLINE    = "[ONLINE]"
BADGE_THINKING  = "[THINKING]"
BADGE_RESEARCH  = "[RESEARCHING]"
BADGE_DISCOVER  = "[DISCOVERING]"
BADGE_MEMORY    = "[MEMORY ACTIVE]"
BADGE_DREAM     = "[DREAM ENGINE]"
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


def _make_progress_bar(pct: int, width: int = 20) -> str:
    filled = int(pct / 100 * width)
    empty = width - filled
    return f"[{'#' * filled}{'.' * empty}] {pct}%"


def _make_status_badge(text: str, color: str) -> Text:
    badge = Text()
    badge.append(f" {text} ", style=f"bold {color}")
    return badge


# ================================================================
# HELP TEXT
# ================================================================

HELP_TEXT = f"""[bold {ACCENT_CYAN}]RUMI[/bold {ACCENT_CYAN}] [dim]v3.0 | Research Unified Machine Intelligence[/dim]

[bold]Commands[/bold]
  [bold {ACCENT_BLUE}]/help[/{ACCENT_BLUE}]          Show this help
  [bold {ACCENT_BLUE}]/clear[/{ACCENT_BLUE}]         Clear screen
  [bold {ACCENT_BLUE}]/status[/{ACCENT_BLUE}]        System status
  [bold {ACCENT_BLUE}]/stats[/{ACCENT_BLUE}]         Session stats
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

[bold]Shortcuts[/bold]
  [bold {ACCENT_AMBER}]Ctrl+K[/{ACCENT_AMBER}]  Command palette
  [bold {ACCENT_AMBER}]Ctrl+L[/{ACCENT_AMBER}]  Clear screen
  [bold {ACCENT_AMBER}]Escape[/{ACCENT_AMBER}]  Interrupt"""

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
        """Hermes-style boot -- ASCII logo centered, compact info."""
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

        # Status line centered
        status_parts = []
        status_parts.append("groq" if groq_ok else "groq?")
        status_parts.append("gemini" if gemini_ok else "gemini?")
        status_parts.append("17 domains")
        status_parts.append("88 modules")
        status_str = "  |  ".join(status_parts)
        s_pad = max(0, (term_width - len(status_str) - 2) // 2)

        status_line = Text()
        status_line.append(f"{' ' * s_pad}", style="")
        status_line.append("groq", style=ACCENT_GREEN if groq_ok else ACCENT_RED)
        status_line.append("  |  ", style=TXT_DIM)
        status_line.append("gemini", style=ACCENT_GREEN if gemini_ok else ACCENT_RED)
        status_line.append("  |  ", style=TXT_DIM)
        status_line.append("17 domains", style=TXT_SECOND)
        status_line.append("  |  ", style=TXT_DIM)
        status_line.append("88 modules", style=TXT_SECOND)
        console.print(status_line)

        help_text = "/help for commands"
        h_pad = max(0, (term_width - len(help_text) - 2) // 2)
        console.print(Text(f"{' ' * h_pad}{help_text}", style=TXT_DIM))
        console.print()

    # ----------------------------------------------------------------
    # HEADER PANEL (Hermes style)
    # ----------------------------------------------------------------
    def _show_header_panel(self):
        """Hermes-style compact header."""
        uptime = self._get_uptime()
        line = Text()
        line.append("  R", style=f"bold {ACCENT_BLUE}")
        line.append("UMI", style=f"bold {TXT_PRIMARY}")
        line.append(f"  {uptime}", style=TXT_DIM)
        line.append(f"  {self._total_tokens:,} tok", style=TXT_SECOND)
        line.append(f"  ${self._total_cost:.4f}", style=ACCENT_GREEN)
        line.append(f"  {self._get_mode_str()}", style=ACCENT_PURPLE if self._get_mode_str() != "normal" else TXT_DIM)
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
    # ACTIVITY FEED (compact)
    # ----------------------------------------------------------------
    def _show_activity_feed(self):
        """Hermes-style compact event stream."""
        events = self._activity_feed.get_recent(6)
        if not events:
            return

        for ev in events:
            line = Text()
            line.append(f"  {ev['time']} ", style=TXT_DIM)
            line.append(ev["msg"], style=ev["color"])
            console.print(line)

    # ----------------------------------------------------------------
    # DISCOVERY DASHBOARD (dense, professional)
    # ----------------------------------------------------------------
    def _show_discovery_dashboard(self, topic: str = ""):
        """Hermes-style discovery dashboard."""
        pct = self._pipeline.get_progress_pct()
        bar = _make_progress_bar(pct, 16)

        table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
        table.add_column(style=TXT_DIM, min_width=14)
        table.add_column(style=TXT_PRIMARY)
        table.add_row("TOPIC:", topic or "N/A")
        table.add_row("PROGRESS:", bar)
        table.add_row("PAPERS:", str(self._graph_metrics.papers))
        table.add_row("ENTITIES:", str(self._graph_metrics.entities))
        table.add_row("RELATIONSHIPS:", str(self._graph_metrics.relationships))
        table.add_row("KNOWLEDGE GAPS:", str(self._graph_metrics.contradictions))
        table.add_row("HYPOTHESES:", str(self._graph_metrics.novelty_candidates))

        console.print()
        console.print(Text("  DISCOVERY", style=f"bold {ACCENT_PURPLE}"))
        console.print(table)
        console.print()

    # ----------------------------------------------------------------
    # THINKING ANIMATION (compact)
    # ----------------------------------------------------------------
    def _show_thinking_animation(self, message: str = ""):
        """Compact thinking indicator."""
        msg = message or random.choice(THINKING_MESSAGES)
        console.print(Text(f"  ... {msg}", style=f"bold {ACCENT_CYAN}"))

    # ----------------------------------------------------------------
    # INPUT BOX (compact)
    # ----------------------------------------------------------------
    def _show_input_box(self):
        """Compact input hint."""
        console.print(Text("  /discover /research /status /help", style=TXT_DIM))

    # ----------------------------------------------------------------
    # PANELS (compact, dense)
    # ----------------------------------------------------------------
    def _show_panel(self, title: str, content: str, color: str = BORDER_NORMAL):
        """Compact panel."""
        console.print(Text(f"  [{title}] {content}", style=f"bold {color}"))

    def _show_dream_panel(self):
        """Dream Engine status -- compact."""
        line = Text()
        line.append("  [dream] ", style=f"bold {ACCENT_PINK}")
        line.append("active  ", style=ACCENT_GREEN)
        line.append("3 hypotheses  ", style=TXT_SECOND)
        line.append("12s ago", style=TXT_DIM)
        console.print(line)

    # ----------------------------------------------------------------
    # SIDEBAR (compact)
    # ----------------------------------------------------------------
    def _show_sidebar(self):
        """Compact sidebar -- single line."""
        line = Text()
        line.append("  memory ", style=f"{ACCENT_GREEN}")
        line.append("dream ", style=f"{ACCENT_PINK}")
        line.append("research ", style=f"{ACCENT_BLUE}")
        line.append(f"kg:{self._graph_metrics.nodes}", style=TXT_DIM)
        console.print(line)

    # ----------------------------------------------------------------
    # STATUS UPDATER
    # ----------------------------------------------------------------
    def _status_updater(self):
        while self._running:
            self._current_spin_idx = (self._current_spin_idx + 1) % len(SPINNER_CHARS)
            if self._current_spin_idx == 0:
                self._current_word_idx = (self._current_word_idx + 1) % len(THINKING_MESSAGES)
            time.sleep(0.15)

    # ----------------------------------------------------------------
    # CONTEXT BAR
    # ----------------------------------------------------------------
    def _get_context_bar(self, tokens_used: int = 0, max_tokens: int = 200000) -> str:
        pct = min(100, int((tokens_used / max_tokens) * 100))
        filled = int(pct / 10)
        empty = 10 - filled
        bar = "#" * filled + "." * empty
        if pct < 50:
            color = "#39d353"
        elif pct < 80:
            color = "#d29922"
        elif pct < 95:
            color = "#f0883e"
        else:
            color = "#f85149"
        return f"<style fg='{color}'>[{bar}] {pct}%</style>"

    # ----------------------------------------------------------------
    # TOOLBAR
    # ----------------------------------------------------------------
    def _get_toolbar(self):
        if not HAVE_PT:
            return ""

        spin = SPINNER_CHARS[self._current_spin_idx]
        elapsed = int(time.time() - self._start_time)
        uptime = f"{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d}"

        parts = []
        parts.append(f"<style fg='#58a6ff'>RUMI</style>")
        parts.append(f"<style fg='#30363d'> | </style>")

        if self._is_busy or self._discovery_running:
            word = self._discovery_step or THINKING_MESSAGES[self._current_word_idx]
            parts.append(f"<style fg='#39d353'>{spin} {word}</style>")
        else:
            parts.append(f"<style fg='#8b949e'>idle</style>")

        parts.append(f"<style fg='#30363d'> | </style>")
        parts.append(self._get_context_bar(self._total_tokens, 200000))

        parts.append(f"<style fg='#30363d'> | </style>")
        parts.append(f"<style fg='#8b949e'>${self._total_cost:.3f}</style>")
        parts.append(f"<style fg='#30363d'> | </style>")
        parts.append(f"<style fg='#8b949e'>{uptime}</style>")

        if self._think_mode:
            parts.append(f"<style fg='#30363d'> | </style>")
            parts.append(f"<style fg='#bc8cff'>think</style>")
        if self._deep_dive_active:
            parts.append(f"<style fg='#30363d'> | </style>")
            parts.append(f"<style fg='#39d353'>dive</style>")

        parts.append(f"<style fg='#30363d'> | </style>")
        parts.append(f"<style fg='#484f58'>Ctrl+K</style>")

        return HTML("".join(parts))

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

        while self._running:
            try:
                if HAVE_PT and self._pt_history is not None:
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
                    threading.Thread(target=self.on_text_command, args=(value,), daemon=True).start()

            except (EOFError, KeyboardInterrupt):
                console.print()
                self._handle_command("/exit")
                break
            except Exception:
                time.sleep(0.1)

    # ----------------------------------------------------------------
    # COMMAND PALETTE
    # ----------------------------------------------------------------
    def _show_command_palette(self):
        """Hermes-style command palette."""
        console.print()
        console.print(Text(f"  Commands", style=f"bold {ACCENT_BLUE}"))
        console.print()
        for i, (key, label, cmd) in enumerate(COMMAND_PALETTE_ITEMS):
            line = Text()
            line.append(f"  {i+1:2d} ", style=TXT_DIM)
            line.append(f"{label}", style=TXT_PRIMARY)
            line.append(f"  {cmd}", style=ACCENT_BLUE)
            console.print(line)
        console.print()
        console.print(Text(f"  Type number or command directly", style=TXT_DIM))
        console.print()
        for i, (key, label, cmd) in enumerate(COMMAND_PALETTE_ITEMS):
            line = Text()
            line.append(f"  {i+1:2d} ", style=TXT_DIM)
            line.append(f"{label}", style=TXT_PRIMARY)
            line.append(f"  {cmd}", style=ACCENT_BLUE)
            console.print(line)
        console.print()
        console.print(Text(f"  Type number or command directly", style=TXT_DIM))
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
    # TOOL CALL DISPLAY
    # ----------------------------------------------------------------
    def _show_tool_call(self, name: str, query: str = ""):
        self._tool_calls.start(name, query)
        self._activity_feed.add(f"{name}", ACCENT_TEAL)

        line = Text()
        line.append(f"  {name}", style=f"bold {TXT_SECOND}")
        if query:
            short = query[:40] + "..." if len(query) > 40 else query
            line.append(f" {short}", style=TXT_DIM)
        line.append(" ...", style=TXT_MUTED)
        console.print(line)

    def complete_tool_call(self, name: str, result: str = ""):
        self._tool_calls.complete(name, result)

        elapsed = ""
        for call in reversed(self._tool_calls.get_recent(5)):
            if call["name"] == name and call.get("elapsed"):
                elapsed = f" ({call['elapsed']:.1f}s)"
                break

        line = Text()
        line.append(f"  {name}", style=f"bold {ACCENT_GREEN}")
        line.append(f"{elapsed}", style=TXT_DIM)
        if result:
            short = result[:50] + "..." if len(result) > 50 else result
            line.append(f"  {short}", style=TXT_DIM)
        console.print(line)

    # ----------------------------------------------------------------
    # STATUS (compact)
    # ----------------------------------------------------------------
    def _show_status_panel(self):
        """Hermes-style compact status."""
        uptime = self._get_uptime()
        pct = min(100, int((self._total_tokens / 200000) * 100))
        filled = int(pct / 10)
        empty = 10 - filled
        bar_text = f"[{'#' * filled}{'.' * empty}] {pct}%"
        if pct < 50:
            bar_color = ACCENT_GREEN
        elif pct < 80:
            bar_color = ACCENT_AMBER
        elif pct < 95:
            bar_color = "#f0883e"
        else:
            bar_color = ACCENT_RED

        console.print()
        line = Text()
        line.append("  RUMI ", style=f"bold {ACCENT_BLUE}")
        line.append(f"up {uptime} ", style=TXT_SECOND)
        line.append(f"{self._message_count} msgs ", style=TXT_SECOND)
        line.append(f"{self._total_tokens:,} tok ", style=TXT_SECOND)
        line.append(f"${self._total_cost:.4f} ", style=ACCENT_GREEN)
        line.append(f"{bar_text}", style=f"bold {bar_color}")
        console.print(line)
        console.print()

    def _show_stats(self):
        """Compact stats -- single line."""
        uptime = int(time.time() - self._start_time)
        line = Text()
        line.append("  stats ", style=TXT_DIM)
        line.append(f"{uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}", style=TXT_PRIMARY)
        line.append(f"  {self._message_count} msgs", style=TXT_SECOND)
        line.append(f"  {self._timeline.count()} events", style=TXT_SECOND)
        line.append(f"  {self._graph_metrics.nodes} nodes", style=TXT_SECOND)
        line.append(f"  {self._graph_metrics.edges} edges", style=TXT_SECOND)
        console.print(line)

    # ----------------------------------------------------------------
    # TIMELINE DISPLAY
    # ----------------------------------------------------------------
    def _show_timeline(self):
        """Compact timeline -- dense event list."""
        events = self._timeline.get_events(last_n=10)

        if not events:
            console.print(Text("  No events yet.", style=TXT_DIM))
            return

        for ev in events:
            type_color = {
                "system": ACCENT_BLUE,
                "user": ACCENT_CYAN,
                "discovery": ACCENT_GREEN,
                "mode": ACCENT_PURPLE,
                "tool": ACCENT_AMBER,
                "error": ACCENT_RED,
            }.get(ev["type"], TXT_MUTED)

            line = Text()
            line.append(f"  {ev['time']} ", style=TXT_DIM)
            line.append(f"{ev['desc']}", style=type_color)
            console.print(line)

    # ----------------------------------------------------------------
    # SESSION SUMMARY
    # ----------------------------------------------------------------
    def _show_session_summary(self):
        """Compact session summary."""
        uptime = int(time.time() - self._start_time)
        line = Text()
        line.append("  session ", style=TXT_DIM)
        line.append(f"{uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}", style=TXT_PRIMARY)
        line.append(f"  {self._message_count} msgs", style=TXT_SECOND)
        line.append(f"  {self._total_tokens:,} tok", style=TXT_SECOND)
        line.append(f"  ${self._total_cost:.4f}", style=ACCENT_GREEN)
        console.print(line)

    # ----------------------------------------------------------------
    # HEARTBEAT
    # ----------------------------------------------------------------
    def _heartbeat_loop(self):
        kaomoji_idx = 0
        while self._running:
            if self._rumi_state in ("THINKING", "PROCESSING"):
                kaomoji_idx = (kaomoji_idx + 1) % len(THINKING_MESSAGES)
                time.sleep(0.5)
            else:
                kaomoji_idx = 0
                time.sleep(1)

    def show_thinking(self, message: str = ""):
        msg = message or random.choice(THINKING_MESSAGES)
        console.print(Text(f"  ... {msg}", style=f"bold {ACCENT_BLUE}"))

    def show_done(self, message: str = ""):
        msg = message or "Done."
        console.print(Text(f"  {msg}", style=f"bold {ACCENT_GREEN}"))

    # ================================================================
    # PUBLIC API
    # ================================================================

    def write_log(self, text: str):
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
                console.print(Text(f"  > {content}", style=f"bold {ACCENT_BLUE}"))
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
                console.print(Text(f"  {content}", style=TXT_SECOND))

            elif tl.startswith("err:") or tl.startswith("error:"):
                err_msg = text[4:].strip() if ":" in text[4:5] else text[4:].strip()
                self._activity_feed.add(f"error: {err_msg}", ACCENT_RED)
                console.print(Text(f"  error: {err_msg}", style=f"bold {ACCENT_RED}"))

            else:
                if not text.strip() or text.strip().startswith("["):
                    return
                console.print(Text(f"  {text}", style=TXT_PRIMARY))

    def set_state(self, state: str):
        self._rumi_state = state
        self.status_text = state

    def set_discovery_step(self, step: str):
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
            color = ACCENT_CYAN

        # Hermes-style: step name + inline progress
        pct = self._pipeline.get_progress_pct()
        bar = _make_progress_bar(pct, 8)
        line = Text()
        line.append(f"  {step} ", style=f"{color}")
        line.append(bar, style=TXT_DIM)
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
    # SCIENCE HELP
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
        console.print(Text("  /domain <key>  |  /discover <domain>: <topic>", style=TXT_DIM))
        console.print()

    def _handle_personality(self):
        console.print()
        console.print(Text(f"  Current: {self._personality}", style=ACCENT_AMBER))
        console.print()

        pers_keys = list(PERSONALITIES.keys())
        for i, k in enumerate(pers_keys):
            p = PERSONALITIES[k]
            console.print(Text(f"  [{i+1}] {p['label']}", style=TXT_PRIMARY))
            console.print(Text(f"      {p['desc']}", style=TXT_MUTED))
        console.print()

        choice = input("  > ").strip()
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
            console.print(Text(f"  OK Switched to {PERSONALITIES[chosen]['label']}", style=ACCENT_GREEN))
            console.print(Text(f"  Takes effect next session", style=ACCENT_AMBER))
        else:
            console.print(Text("  X Failed to switch", style=ACCENT_RED))
        console.print()

    # ----------------------------------------------------------------
    # API KEY SETUP
    # ----------------------------------------------------------------
    def _show_setup_ui(self):
        console.print()
        console.print(Rule(style=f"bold {ACCENT_PURPLE}"))
        console.print(Text("  FIRST BOOT -- API KEY SETUP", style=f"bold {TXT_PRIMARY}"), justify="center")
        console.print(Rule(style=f"bold {ACCENT_PURPLE}"))
        console.print()

        detected = _detect_os()

        console.print(Text("  Enter your Gemini API key:", style=ACCENT_CYAN))
        console.print(Text("  (Get one at: https://aistudio.google.com/apikey)", style=TXT_MUTED))
        gemini_key = input("  > ").strip()
        while not gemini_key:
            console.print(Text("  API key cannot be empty.", style=f"bold {ACCENT_RED}"))
            gemini_key = input("  > ").strip()

        console.print()

        console.print(Text("  Enter your Groq API key:", style=ACCENT_CYAN))
        console.print(Text("  (Get one at: https://console.groq.com/keys)", style=TXT_MUTED))
        groq_key = input("  > ").strip()
        while not groq_key:
            console.print(Text("  API key cannot be empty.", style=f"bold {ACCENT_RED}"))
            groq_key = input("  > ").strip()

        console.print()

        console.print(Text("  Second Groq key (optional, for rate limiting)", style=TXT_MUTED))
        groq_key2 = input("  > ").strip()

        console.print()

        console.print(Text("  Your callsign (default: OPERATOR):", style=ACCENT_CYAN))
        user_name = input("  > ").strip().upper() or "OPERATOR"

        console.print()
        console.print(Text("  Personality:", style=ACCENT_CYAN))
        pers_keys = list(PERSONALITIES.keys())
        for i, k in enumerate(pers_keys):
            p = PERSONALITIES[k]
            console.print(Text(f"  [{i+1}] {p['label']}", style=ACCENT_AMBER))
        pers_choice = input("  > ").strip() or "1"
        try:
            idx = int(pers_choice) - 1
            chosen_pers = pers_keys[idx] if 0 <= idx < len(pers_keys) else "professional"
        except (ValueError, IndexError):
            chosen_pers = "professional"
        _set_personality(chosen_pers)
        self._personality = chosen_pers

        console.print()
        console.print(Text("  Telegram bot? (y/N)", style=TXT_MUTED))
        tg_choice = input("  > ").strip().lower()
        tg_token = ""
        tg_user = ""
        if tg_choice in ("y", "yes"):
            console.print(Text("  Bot token:", style=TXT_PRIMARY))
            tg_token = input("  > ").strip()
            console.print(Text("  User ID:", style=TXT_PRIMARY))
            tg_user = input("  > ").strip()

        console.print()
        console.print(Text("  Optional enrichment keys (enter to skip):", style=TXT_MUTED))

        console.print(Text("  NASA API key:", style=TXT_MUTED))
        nasa_key = input("  > ").strip()

        console.print(Text("  Materials Project key:", style=TXT_MUTED))
        mp_key = input("  > ").strip()

        console.print()
        console.print(Text("  Voice mode: [1] Text only  [2] Text + Voice", style=ACCENT_AMBER))
        vm_choice = input("  > ").strip() or "1"
        voice_enabled = vm_choice == "2"

        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(API_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "primary_provider": "groq",
                "gemini_api_key": gemini_key,
                "gemini_api_key_fallback": "",
                "groq_api_key": groq_key,
                "groq_api_key2": groq_key2,
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
        console.print(Text(f"  * RUMI online. Welcome, {user_name}.", style=f"bold {ACCENT_GREEN}"))
        console.print()
