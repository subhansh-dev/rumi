"""
ui.py — RUMI Terminal UI (v3.0)
Claude Code / Hermes inspired terminal interface.
Clean, minimal, information-dense. Scientific accent colors.
"""

import sys
import os
import json
import time
import platform
import threading
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.table import Table
from rich.box import MINIMAL, SIMPLE, HEAVY
from rich.style import Style
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout

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


from rich.theme import Theme
_dark_theme = Theme({
    "black": "black",
    "white": "white",
    "cyan": "cyan",
    "green": "green",
    "yellow": "yellow",
    "blue": "blue",
    "magenta": "magenta",
    "red": "red",
    "dim": "#6b7280",
})
console = Console(force_terminal=True, color_system="truecolor", theme=_dark_theme)
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
API_FILE = CONFIG_DIR / "api_keys.json"

# ── Status Bar ──────────────────────────────────────────────────
SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
RUMI_WORDS = [
    "reasoning", "hypothesizing", "synthesizing",
    "calculating", "analyzing", "experimenting",
    "discovering", "researching", "thinking",
    "processing", "computing", "formulating",
    "investigating", "examining", "validating",
    "connecting patterns", "doing science",
    "conceptualizing", "theorizing", "postulating",
    "simulating", "optimizing", "verifying",
    "calibrating", "inferring", "deducing",
    "extrapolating", "brainstorming", "rumination",
    "conjuring science", "reading code", "writing code",
    "refactoring", "building", "constructing",
    "preparing response", "loading brain",
]

# ── Personality System ──────────────────────────────────────────
PERSONALITIES = {
    "cutesy": {
        "label": "Cutesy / UwU",
        "desc": "Playful, cute scientist — 'hewwoo!! let's do science!!'",
        "soul_file": "SOUL_cutesy.md",
        "rumi_file": "RUMI_cutesy.md",
    },
    "professional": {
        "label": "Professional / Sharp",
        "desc": "Direct, analytical scientist — 'Hypothesis formed. Let me verify.'",
        "soul_file": "SOUL_professional.md",
        "rumi_file": "RUMI_professional.md",
    },
}


def _set_personality(choice: str):
    """Copy chosen personality template over active SOUL.md and RUMI.md."""
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


# ── Colour Palette (Claude Code inspired, scientific twist) ─────
C_CYAN   = "#00d4ff"   # Primary accent — scientific
C_AMBER  = "#f59e0b"   # Secondary accent — warm
C_GREEN  = "#10b981"   # Success / confirmed
C_RED    = "#ef4444"   # Error / refuted
C_PURPLE = "#8b5cf6"   # Special / discovery
C_DIM    = "#6b7280"   # Muted text
C_WHITE  = "#e5e7eb"   # Primary text
C_BOLD   = "#f9fafb"   # Emphasized text
C_PANEL  = "#111827"   # Panel background
C_BORDER = "#1f2937"   # Panel borders
C_BG     = "#0a0a0a"   # Deep background

# ── Prompt symbols ──────────────────────────────────────────────
PROMPT_SYMBOL = ">"
PROMPT_BUSY = "..."
PROMPT_READY = ">"

# ── Help text ──────────────────────────────────────────────────
HELP_TEXT = """[bold]RUMI Scientist AI[/bold] — Commands

[bold amber]General[/bold amber]
  /help            Show this help
  /clear           Clear screen
  /status          System status & uptime
  /stats           Session statistics
  /personality     Switch personality (cutesy / professional)
  /exit            Exit RUMI

[bold #f59e0b]Modes[/bold #f59e0b]
  /think           Toggle Think mode (reasoning before responses)
  /dive            Toggle Deep Dive mode (thorough research)

[bold #00d4ff]Grounded Discovery[/bold #00d4ff]
  /grounded <topic>    Full grounded pipeline (real papers + real math + claim labels)
  /discover <topic>    Run autonomous discovery pipeline
  /domains             List scientific domains with available calculations

[bold #00d4ff]Scientist AI[/bold #00d4ff]
  /science         Show Scientist AI capabilities
  /hypothesize     Generate diverse hypotheses on a topic
  /experiment      Design or run an experiment
  /papers          Search papers from famous researchers
  /review          Peer review a paper or claim
  /graph           Knowledge graph operations
  /notebook        Lab notebook operations
  /reason          Multi-pass scientific reasoning
  /theorize        Theory formation from observations

[bold #10b981]Grounded Pipeline (all domains)[/bold #10b981]
  /grounded KRAS G12C inhibitor resistance mechanisms
  /grounded Perovskite solar cell degradation
  /grounded Dopamine receptor signaling in addiction
  /grounded Biodiversity loss and ecosystem function

[green]The /grounded command fetches real papers from arXiv + PubMed,
runs domain-specific calculations (Lipinski rules, Nernst potentials,
radiative forcing, Shannon diversity, etc.), generates a report with
real citations, and labels every claim as VALIDATED / INFERRED /
SIMULATED / SPECULATIVE / HYPOTHETICAL with a reliability score.[/green]"""

# ── Slash commands list (for tab completion) ─────
SLASH_COMMANDS = [
    "/help", "/clear", "/think", "/dive",
    "/status", "/stats", "/model", "/exit",
    "/science", "/discover", "/search", "/enrich", "/hypothesize", "/experiment", "/generate",
    "/papers", "/review", "/graph", "/dashboard", "/discoveries", "/notebook", "/domains",
    "/personality", "/reason", "/theorize",
    "/grounded",
]


# ── Utility Functions ──────────────────────────────────────────
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


# ── RUMI Terminal UI ──────────────────────────────────────────
class RumiUI:
    """Claude Code / Hermes inspired terminal UI for RUMI Scientist AI."""

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

        # Callbacks
        self.on_text_command = None
        self.on_discovery_command = None
        self.on_think_mode_toggle = None
        self.on_deep_dive_toggle = None
        self.on_idle_scan = None

        # Threading
        self._running = True
        self._input_lock = threading.Lock()

        # Interrupt & Message Queue
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

        # Input history & completion
        self._pt_history = InMemoryHistory() if HAVE_PT else None
        self._message_count = 0

        # Status bar updater thread
        self._status_thread = threading.Thread(target=self._status_updater, daemon=True)
        self._status_thread.start()

        # Animated Startup
        self._show_startup()

        # Check API keys
        self._api_key_ready = _api_keys_exist()
        if not self._api_key_ready:
            self._show_setup_ui()

        # Start input reader
        self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self._input_thread.start()

        # Start heartbeat for thinking indicator
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _status_updater(self):
        """Background thread: cycles spinner & random words for status bar."""
        while self._running:
            self._current_spin_idx = (self._current_spin_idx + 1) % len(SPINNER_CHARS)
            if self._current_spin_idx == 0:
                self._current_word_idx = (self._current_word_idx + 1) % len(RUMI_WORDS)
            time.sleep(0.15)

    def _get_toolbar(self):
        if not HAVE_PT:
            return ""
        if self._is_busy or self._discovery_running:
            spin = SPINNER_CHARS[self._current_spin_idx]
            word = self._discovery_step or RUMI_WORDS[self._current_word_idx]
            parts = [f"{spin} {word}"]
            if self._message_queue_count:
                parts.append(f"queue:{self._message_queue_count}")
            if self._interrupt_requested.is_set():
                parts.append("ESC to cancel")
            return HTML(f"<style fg='#10b981'>{'  '.join(parts)}</style>")
        else:
            spin = SPINNER_CHARS[self._current_spin_idx]
            modes = []
            if self._think_mode:
                modes.append("think")
            if self._deep_dive_active:
                modes.append("dive")
            mode_str = f"  [{'/'.join(modes)}]" if modes else ""
            return HTML(f"<style fg='#6b7280'>{spin} ready{mode_str}</style>")

    def interrupt_requested(self):
        return self._interrupt_requested.is_set()

    def clear_interrupt(self):
        self._interrupt_requested.clear()

    # ── Startup ─────────────────────────────────────────────────
    def _show_startup(self):
        """Display clean startup sequence — Claude Code / Hermes style."""
        console.clear()

        # RUMI logo — clean block letters
        logo_lines = [
            "  ▓▓▓▓▓  ▓    ▓ ▓▓▓   ▓▓▓▓",
            "  ▓   ▓  ▓    ▓ ▓  ▓  ▓  ▓",
            "  ▓▓▓▓▓  ▓    ▓ ▓   ▓ ▓  ▓",
            "  ▓   ▓  ▓    ▓ ▓  ▓  ▓  ▓",
            "  ▓   ▓   ▓▓▓▓  ▓▓▓   ▓▓▓▓",
        ]
        for line in logo_lines:
            console.print(Text(line, style=f"bold {C_CYAN}"))

        console.print()
        console.print(Text("  Research & Unified Machine Intelligence", style=f"bold {C_WHITE}"))
        console.print(Text("  Autonomous Scientific Discovery Framework", style=C_AMBER))
        console.print()

        # System info — colorful, no dim text
        from discovery.llm_client import get_status
        status = get_status()
        provider = status.get("primary", "unknown").upper()
        groq_ok = status.get("groq", {}).get("available", False)
        gemini_ok = status.get("gemini", {}).get("available", False)

        info = Table(show_header=False, box=None, padding=(0, 2), expand=False)
        info.add_column("key", style=C_AMBER, min_width=12)
        info.add_column("value", style=C_WHITE)
        info.add_row("model", Text(f"Groq Llama 3.3 70B {'(primary)' if provider == 'GROQ' else ''}", style=C_GREEN if groq_ok else C_RED))
        info.add_row("fallback", Text(f"Gemini 2.5 Flash {'OK' if gemini_ok else 'not configured'}", style=C_GREEN if gemini_ok else C_RED))
        info.add_row("brain", Text("88 cognitive modules", style=C_CYAN))
        info.add_row("scientist", Text("15 discovery modules · 10 domains with real calculations", style=C_CYAN))
        info.add_row("pipeline", Text("arXiv + PubMed citations · Bayesian scoring · Monte Carlo", style=C_PURPLE))
        console.print(info)
        console.print()

        # Bottom hint
        console.print(Text("  /help for commands  ·  /discover <topic>  ·  /grounded <topic>", style=C_AMBER))
        console.print()

    # ── Input Loop ──────────────────────────────────────────────
    def _idle_monitor(self):
        """Background thread that triggers idle scan after 30s of inactivity."""
        while self._running:
            idle_time = time.time() - self._last_input_time
            time_since_last_scan = time.time() - self._last_idle_scan_time
            if idle_time > 30 and time_since_last_scan > 3600:
                self._last_idle_scan_time = time.time()
                if self.on_idle_scan:
                    self.on_idle_scan()
            time.sleep(10)

    def _input_loop(self):
        """Background thread reading user input via prompt_toolkit or fallback."""
        pt_style = PtStyle([
            ('prompt', f'bold {C_CYAN}'),
        ]) if HAVE_PT else None

        # Set up ESC key binding for interrupt
        kb = KeyBindings() if HAVE_PT else None
        if kb:
            @kb.add('escape')
            def _(event):
                self._interrupt_requested.set()
            @kb.add('c-c')
            def _(event):
                self._interrupt_requested.set()

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

                # Handle slash commands
                if value.startswith("/"):
                    self._handle_command(value)
                    continue

                # Dispatch to main app
                if self.on_text_command:
                    self._last_input_time = time.time()
                    self._message_count += 1
                    self.write_log(f"You: {value}")
                    threading.Thread(target=self.on_text_command, args=(value,), daemon=True).start()

            except (EOFError, KeyboardInterrupt):
                console.print()
                self._handle_command("/exit")
                break
            except Exception:
                time.sleep(0.1)

    def _handle_command(self, cmd: str):
        """Handle slash commands."""
        self._last_input_time = time.time()
        cmd = cmd.lower().strip()

        if cmd == "/help":
            console.print(Markdown(HELP_TEXT))
            console.print()

        elif cmd == "/clear":
            console.clear()
            self._show_startup()

        elif cmd == "/think":
            self._think_mode = not self._think_mode
            state = "on" if self._think_mode else "off"
            console.print(Text(f"  think mode {state}", style=C_CYAN))
            if self.on_think_mode_toggle:
                threading.Thread(target=self.on_think_mode_toggle, args=(self._think_mode,), daemon=True).start()

        elif cmd == "/dive":
            self._deep_dive_active = not self._deep_dive_active
            state = "on" if self._deep_dive_active else "off"
            console.print(Text(f"  deep dive {state}", style=C_CYAN))
            if self.on_deep_dive_toggle:
                threading.Thread(target=self.on_deep_dive_toggle, args=(self._deep_dive_active,), daemon=True).start()

        elif cmd == "/status":
            uptime = int(time.time() - self._start_time)
            modes = []
            if self._think_mode:
                modes.append("think")
            if self._deep_dive_active:
                modes.append("dive")
            mode_str = " + ".join(modes) if modes else "normal"

            console.print()
            console.print(Text(f"  uptime    {uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}", style=C_WHITE))
            console.print(Text(f"  mode      {mode_str}", style=C_WHITE))
            console.print(Text(f"  messages  {self._message_count}", style=C_WHITE))
            console.print(Text(f"  state     {self._rumi_state}", style=C_WHITE))
            if self._message_count > 0:
                rate = self._message_count / max(uptime, 1) * 3600
                console.print(Text(f"  rate      {rate:.1f}/hr", style=C_WHITE))
            console.print()

        elif cmd == "/stats":
            uptime = int(time.time() - self._start_time)
            console.print()
            console.print(Text(f"  session   {uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}", style=C_WHITE))
            console.print(Text(f"  messages  {self._message_count}", style=C_WHITE))
            console.print(Text(f"  state     {self._rumi_state}", style=C_WHITE))
            console.print()

        elif cmd == "/science":
            self._show_science_help()

        elif cmd.startswith("/discover "):
            args = cmd[len("/discover "):].strip()
            console.print(Text(f"  starting discovery: {args}", style=C_CYAN))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("discover", args), daemon=True).start()

        elif cmd == "/discover":
            console.print(Text("  discovery pipeline (specify topic)", style=C_AMBER))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("discover", ""), daemon=True).start()

        elif cmd.startswith("/grounded "):
            args = cmd[len("/grounded "):].strip()
            console.print(Text(f"  grounded discovery: {args}", style=f"bold {C_CYAN}"))
            console.print(Text(f"  fetching real papers + running domain calculations...", style=C_AMBER))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("grounded", args), daemon=True).start()

        elif cmd == "/grounded":
            console.print(Text("  grounded discovery (specify topic)", style=C_AMBER))
            console.print(Text("  example: /grounded KRAS G12C inhibitor resistance", style=C_AMBER))

        elif cmd.startswith("/search "):
            args = cmd[len("/search "):].strip()
            console.print(Text(f"  searching: {args}", style=C_CYAN))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("search", args), daemon=True).start()

        elif cmd.startswith("/hypothesize "):
            args = cmd[len("/hypothesize "):].strip()
            console.print(Text(f"  generating hypotheses: {args}", style=C_CYAN))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("hypothesize", args), daemon=True).start()

        elif cmd == "/hypothesize":
            console.print(Text("  specify topic: /hypothesize <topic>", style=C_AMBER))

        elif cmd.startswith("/generate "):
            args = cmd[len("/generate "):].strip()
            console.print(Text(f"  generating: {args}", style=C_CYAN))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("generate", args), daemon=True).start()

        elif cmd == "/generate":
            console.print(Text("  specify target: /generate <target>", style=C_AMBER))

        elif cmd == "/contradictions":
            console.print(Text("  detecting contradictions...", style=C_CYAN))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("contradictions", ""), daemon=True).start()

        elif cmd == "/enrich":
            console.print(Text("  enriching entities...", style=C_CYAN))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("enrich", ""), daemon=True).start()

        elif cmd == "/graph":
            console.print(Text("  knowledge graph", style=C_CYAN))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("graph", ""), daemon=True).start()

        elif cmd == "/dashboard":
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("dashboard", ""), daemon=True).start()

        elif cmd == "/discoveries":
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("discoveries", ""), daemon=True).start()

        elif cmd.startswith("/domain "):
            args = cmd[len("/domain "):].strip()
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("domain", args), daemon=True).start()

        elif cmd == "/domain":
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("domain", ""), daemon=True).start()

        elif cmd == "/experiment":
            console.print(Text("  experiment design mode", style=C_CYAN))
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Help me design a scientific experiment. What hypothesis should I test?",),
                    daemon=True,
                ).start()

        elif cmd == "/papers":
            console.print(Text("  paper search mode", style=C_CYAN))
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Search for academic papers. Who or what topic should I search for?",),
                    daemon=True,
                ).start()

        elif cmd == "/review":
            console.print(Text("  peer review mode", style=C_CYAN))
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Perform a peer review on a paper or scientific claim. Paste the text or describe what to review.",),
                    daemon=True,
                ).start()

        elif cmd == "/notebook":
            console.print(Text("  lab notebook", style=C_CYAN))
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
            console.print(Text(f"  scientific reasoning: {args}", style=C_PURPLE))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("reason", args), daemon=True).start()

        elif cmd.startswith("/theorize "):
            args = cmd[len("/theorize "):].strip()
            console.print(Text(f"  theorizing: {args}", style=C_PURPLE))
            if self.on_discovery_command:
                threading.Thread(target=self.on_discovery_command, args=("theorize", args), daemon=True).start()

        elif cmd == "/personality":
            self._handle_personality()

        elif cmd == "/exit":
            console.print(Text("  shutting down...", style=C_RED))
            self._running = False
            os._exit(0)

        else:
            console.print(Text(f"  unknown command: {cmd}", style=C_RED))
            console.print(Text(f"  type /help for commands", style=C_AMBER))

    def _heartbeat_loop(self):
        """Background thread for thinking state animations."""
        dots = 0
        while self._running:
            if self._rumi_state in ("THINKING", "PROCESSING"):
                dots = (dots + 1) % 4
                time.sleep(0.5)
            else:
                dots = 0
                time.sleep(1)

    # ── Public API ──────────────────────────────────────────────
    def write_log(self, text: str):
        """Display a formatted message in the terminal.

        Handles prefixes:
          'You:'   → user message (dim echo)
          'RUMI:'  → AI response (markdown rendered)
          'AI:'    → AI response (fallback)
          'SYS:'   → system message (dim)
          'ERR:'   → error message (red)
          other    → plain text
        """
        with self._input_lock:
            tl = text.lower().strip()

            if tl.startswith("you:"):
                content = text[4:].strip()
                self.set_state("PROCESSING")
                console.print()
                console.print(Text(f"  {PROMPT_SYMBOL} {content}", style=f"bold {C_WHITE}"))

            elif tl.startswith("rumi:") or tl.startswith("ai:"):
                prefix_len = 5 if tl.startswith("rumi:") else 3
                content = text[prefix_len:].strip()

                console.print()

                # Attempt markdown rendering
                try:
                    body = Markdown(content)
                except Exception:
                    body = Text(content, style=C_CYAN)

                # Use minimal panel — thin border, no title
                console.print(Panel(
                    body,
                    border_style=C_BORDER,
                    box=SIMPLE,
                    padding=(0, 1),
                    expand=True,
                ))
                self.set_state("SPEAKING")

            elif tl.startswith("sys:"):
                content = text[4:].strip()
                console.print(Text(f"  {content}", style=C_AMBER))

            elif tl.startswith("err:") or tl.startswith("error:"):
                content = text[4:].strip() if len(text) > 4 else text
                console.print(Text(f"  error: {content}", style=f"bold {C_RED}"))

            else:
                console.print(Text(f"  {text}", style=C_WHITE))

    def set_state(self, state: str):
        """Update RUMI's state indicator."""
        self._rumi_state = state
        self.status_text = state

    def set_discovery_step(self, step: str):
        """Update discovery pipeline progress with phase indicator."""
        self._discovery_step = step
        # Color-code by phase type
        if "paper" in step.lower() or "fetch" in step.lower() or "arxiv" in step.lower():
            color = C_GREEN  # Green for real data
        elif "comput" in step.lower() or "bayesian" in step.lower() or "monte carlo" in step.lower():
            color = C_PURPLE  # Purple for calculations
        elif "label" in step.lower() or "ground" in step.lower() or "cit" in step.lower():
            color = C_AMBER  # Amber for validation
        elif "generat" in step.lower() or "llm" in step.lower():
            color = C_CYAN  # Cyan for LLM
        else:
            color = C_DIM
        console.print(Text(f"  {SPINNER_CHARS[0]} {step}", style=color))

    def set_discovery_done(self):
        self._discovery_running = False
        self._discovery_step = ""

    def start_speaking(self):
        """Mark the start of speech output."""
        self.set_state("SPEAKING")

    def stop_speaking(self):
        """Mark the end of speech output."""
        self.set_state("LISTENING")

    def show_toast(self, message: str, duration: float = 2.5):
        """Display a brief notification message."""
        console.print(Text(f"  {message}", style=C_CYAN))

    def feed_amplitude(self, amplitude: float):
        """Receive voice amplitude data (no-op in terminal mode)."""
        pass

    def wait_for_api_key(self):
        """Block until API keys are configured."""
        while not self._api_key_ready:
            time.sleep(0.1)

    def _show_science_help(self):
        """Show Scientist AI capabilities — compact table."""
        table = Table(
            border_style=C_BORDER,
            box=SIMPLE,
            show_header=True,
            header_style=f"bold {C_DIM}",
            padding=(0, 1),
        )
        table.add_column("Module", style=C_CYAN, min_width=22)
        table.add_column("What It Does", style=C_WHITE)
        table.add_column("Example", style=C_AMBER)

        capabilities = [
            ("discovery_engine", "Full pipeline: idea → experiment → paper", "Discover new insights about quantum computing"),
            ("tournament_hypothesis", "GFlowNet-style diverse generation", "Generate 10 hypotheses about neural scaling laws"),
            ("knowledge_graph", "Structured knowledge, gap finding", "Add paper to KG and find gaps"),
            ("novelty_checker", "Check novelty against literature", "Is this idea novel: GFlowNets for protein design?"),
            ("experiment_designer", "Design sandboxed experiments", "Design experiment to test attention hypothesis"),
            ("reproducibility", "Extract and verify claims", "Reproduce claims in Chinchilla scaling paper"),
            ("active_experiment", "Bayesian optimal experiment selection", "What experiment to run next?"),
            ("cross_domain", "Find analogies across fields", "Analogies between evolution and NAS"),
            ("peer_reviewer", "Automated peer review", "Review this paper for rigor"),
            ("paper_generator", "Generate LaTeX manuscripts", "Write paper about scaling law findings"),
            ("research_team", "Multi-agent debate", "Debate whether transformers scale to AGI"),
            ("feynman_reducer", "First-principles decomposition", "Explain backprop from first principles"),
            ("cross_validator", "Statistical validation", "Validate results with bootstrap sampling"),
            ("scientist_search", "Search researcher papers", "Find papers by Bengio on GFlowNets"),
            ("lab_notebook", "Track experiments", "Create notebook entry for scaling experiment"),
            ("scientific_reasoning", "Multi-pass discovery cycle", "Reason about neural scaling laws"),
            ("theory_formation", "Bengio-inspired theory engine", "Form theories from observations"),
        ]

        for name, desc, example in capabilities:
            table.add_row(name, desc, example)

        console.print()
        console.print(table)
        console.print()

    def _show_domains(self):
        """Show available Discovery Engine domains with calculation availability."""
        from discovery.domains import list_domains
        from discovery.domain_computational import DOMAIN_COMPUTATIONS
        table = Table(
            border_style=C_BORDER,
            box=SIMPLE,
            show_header=True,
            header_style=f"bold {C_DIM}",
            padding=(0, 1),
        )
        table.add_column("Domain", style=C_CYAN, min_width=20)
        table.add_column("Label", style=C_GREEN)
        table.add_column("Real Calculations", style=C_WHITE)
        table.add_column("Sources", style=C_AMBER)

        domain_sources = {
            "drug_discovery": "PubChem, OpenFDA, PDB",
            "materials_science": "PubChem, Materials Project",
            "neuroscience": "UniProt, PDB",
            "molecular_biology": "UniProt, PDB",
            "climate_energy": "NASA POWER",
            "space_astronomy": "NASA API, arXiv, HITRAN",
            "ecology": "GBIF",
            "physics": "arXiv",
            "computer_science": "GitHub, Semantic Scholar",
            "earth_science": "USGS",
            "oceanography": "NOAA",
            "economics": "World Bank",
            "public_health": "WHO",
            "mathematics": "OEIS, arXiv",
            "chemistry": "PubChem, CIR",
        }

        for d in list_domains():
            key = d["key"]
            has_calc = key in DOMAIN_COMPUTATIONS or key == "space_astronomy"
            calc_status = "YES - real formulas" if has_calc else "generic (Bayesian only)"
            calc_color = C_GREEN if has_calc else C_DIM
            sources = domain_sources.get(key, "Semantic Scholar")
            table.add_row(key, d["label"],
                         Text(calc_status, style=calc_color if has_calc else C_DIM),
                         sources)

        console.print()
        console.print(table)
        console.print(Text("  /domain <key> to switch  ·  /discover <domain>: <topic>", style=C_AMBER))
        console.print(Text("  Domains with 'YES' use real physics/chemistry/biology formulas", style=C_GREEN))
        console.print()

    def _handle_personality(self):
        """Handle /personality command."""
        console.print()
        console.print(Text(f"  current: {self._personality}", style=C_AMBER))
        console.print()

        pers_keys = list(PERSONALITIES.keys())
        for i, k in enumerate(pers_keys):
            p = PERSONALITIES[k]
            console.print(Text(f"  [{i+1}] {p['label']}", style=C_WHITE))
            console.print(Text(f"      {p['desc']}", style=C_AMBER))
        console.print()

        choice = input("  > ").strip()
        try:
            idx = int(choice) - 1
            if idx < 0:
                console.print(Text("  cancelled", style=C_AMBER))
                return
            chosen = pers_keys[idx]
        except (ValueError, IndexError):
            console.print(Text("  invalid choice", style=C_RED))
            return

        if _set_personality(chosen):
            self._personality = chosen
            console.print(Text(f"  switched to {PERSONALITIES[chosen]['label']}", style=C_GREEN))
            console.print(Text(f"  takes effect next session", style=C_AMBER))
        else:
            console.print(Text("  failed to switch", style=C_RED))
        console.print()

    # ── API Key Setup ───────────────────────────────────────────
    def _show_setup_ui(self):
        """Terminal-based first-time setup — clean and compact."""
        console.print()
        console.print(Text("  SETUP", style=f"bold {C_CYAN}"))
        console.print(Text(f"  Configure API keys for RUMI", style=C_AMBER))
        console.print()

        detected = _detect_os()

        # Gemini
        console.print(Text("  Gemini API key", style=C_WHITE))
        console.print(Text("  https://aistudio.google.com/apikey", style=C_AMBER))
        gemini_key = input("  > ").strip()
        while not gemini_key:
            console.print(Text("  required", style=C_RED))
            gemini_key = input("  > ").strip()

        console.print()

        # Groq
        console.print(Text("  Groq API key", style=C_WHITE))
        console.print(Text("  https://console.groq.com/keys", style=C_AMBER))
        groq_key = input("  > ").strip()
        while not groq_key:
            console.print(Text("  required", style=C_RED))
            groq_key = input("  > ").strip()

        console.print()

        # Optional: second Groq key
        console.print(Text("  Second Groq key (optional, for rate limiting)", style=C_AMBER))
        groq_key2 = input("  > ").strip()

        console.print()

        # Callsign
        console.print(Text("  Your callsign", style=C_WHITE))
        user_name = input("  > ").strip().upper() or "OPERATOR"

        # Personality
        console.print()
        console.print(Text("  Personality", style=C_WHITE))
        pers_keys = list(PERSONALITIES.keys())
        for i, k in enumerate(pers_keys):
            p = PERSONALITIES[k]
            console.print(Text(f"  [{i+1}] {p['label']}", style=C_AMBER))
        pers_choice = input("  > ").strip() or "1"
        try:
            idx = int(pers_choice) - 1
            chosen_pers = pers_keys[idx] if 0 <= idx < len(pers_keys) else "professional"
        except (ValueError, IndexError):
            chosen_pers = "professional"
        _set_personality(chosen_pers)
        self._personality = chosen_pers

        # Telegram (optional)
        console.print()
        console.print(Text("  Telegram bot? (y/N)", style=C_AMBER))
        tg_choice = input("  > ").strip().lower()
        tg_token = ""
        tg_user = ""
        if tg_choice in ("y", "yes"):
            console.print(Text("  Bot token:", style=C_WHITE))
            tg_token = input("  > ").strip()
            console.print(Text("  User ID:", style=C_WHITE))
            tg_user = input("  > ").strip()

        # Enrichment keys (optional)
        console.print()
        console.print(Text("  Optional enrichment keys (enter to skip):", style=C_AMBER))

        console.print(Text("  NASA API key:", style=C_AMBER))
        nasa_key = input("  > ").strip()

        console.print(Text("  Materials Project key:", style=C_AMBER))
        mp_key = input("  > ").strip()

        # Voice mode
        console.print()
        console.print(Text("  Voice mode: [1] Text only  [2] Text + Voice", style=C_AMBER))
        vm_choice = input("  > ").strip() or "1"
        voice_enabled = vm_choice == "2"

        # Save config
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
        console.print(Text(f"  ready. welcome, {user_name}.", style=C_GREEN))
        console.print()
