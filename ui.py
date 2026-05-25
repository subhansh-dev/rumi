"""
ui.py — RUMI Terminal UI (v2.0)
Modern scientist-AI terminal interface using Rich + prompt_toolkit.
Replaces the old tkinter holographic GUI entirely.
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
from rich.box import ROUNDED, MINIMAL, HEAVY
from rich.style import Style
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    from prompt_toolkit import prompt as _pt_prompt
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style as PtStyle
    HAVE_PT = True
except ImportError:
    HAVE_PT = False


console = Console()
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
API_FILE = CONFIG_DIR / "api_keys.json"

# ── Colour Palette ──────────────────────────────────────────────
C_CYAN   = "#00d4ff"
C_BLUE   = "#3b82f6"
C_PURPLE = "#8b5cf6"
C_VIOLET = "#6d28d9"
C_GREEN  = "#10b981"
C_YELLOW = "#f59e0b"
C_RED    = "#ef4444"
C_WHITE  = "#f0f0f0"
C_DIM    = "#6b7280"
C_DARK   = "#0f172a"
C_PANEL  = "#1e293b"
C_BORDER = "#334155"

# ── RUMI ASCII Logo ──────────────────────────────────────────────
RUMI_LOGO = """
    ██████╗ ██╗   ██╗███╗   ███╗██╗
    ██╔══██╗██║   ██║████╗ ████║██║
    ██████╔╝██║   ██║██╔████╔██║██║
    ██╔══██╗██║   ██║██║╚██╔╝██║██║
    ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║
    ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝
"""

# ── Help text ──────────────────────────────────────────────────
HELP_TEXT = """
[bold cyan]RUMI Scientist AI — Commands[/bold cyan]

[bold]General:[/bold]
  [cyan]/help[/cyan]        Show this help message
  [cyan]/clear[/cyan]       Clear the screen
  [cyan]/status[/cyan]      Show system status and uptime
  [cyan]/stats[/cyan]       Show session statistics
  [cyan]/exit[/cyan]        Exit RUMI

[bold]Modes:[/bold]
  [cyan]/focus[/cyan]       Toggle Focus mode (only respond when addressed)
  [cyan]/think[/cyan]       Toggle Think mode (reasoning before responses)
  [cyan]/dive[/cyan]        Toggle Deep Dive mode (thorough research)
  [cyan]/mute[/cyan]        Toggle microphone mute

[bold]Scientist AI:[/bold]
  [cyan]/science[/cyan]     Show Scientist AI capabilities
  [cyan]/discover[/cyan]    Run autonomous discovery pipeline
  [cyan]/hypothesize[/cyan] Generate diverse hypotheses on a topic
  [cyan]/experiment[/cyan]  Design or run an experiment
  [cyan]/papers[/cyan]      Search papers from famous researchers
  [cyan]/review[/cyan]      Peer review a paper or claim
  [cyan]/graph[/cyan]       Knowledge graph operations
  [cyan]/notebook[/cyan]    Lab notebook operations
  [cyan]/domains[/cyan]     List scientific domains for cross-domain analysis

[bold]Tips:[/bold]
  • Press [cyan]Tab[/cyan] to autocomplete commands
  • Type naturally — RUMI understands scientific context
  • Ask things like: "Hypothesize about neural scaling laws"
  • Or: "Find analogies between evolution and machine learning"
  • Or: "Reproduce the claims in this paper: ..."
"""

# ── Slash commands list (for tab completion) ─────
SLASH_COMMANDS = [
    "/help", "/clear", "/focus", "/think", "/dive",
    "/mute", "/status", "/stats", "/model", "/exit",
    "/science", "/discover", "/hypothesize", "/experiment",
    "/papers", "/review", "/graph", "/notebook", "/domains",
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
        has_os = bool(data.get("os_system"))
        return has_gemini and has_os
    except Exception:
        return False


# ── RUMI Terminal UI ──────────────────────────────────────────
class RumiUI:
    """Modern terminal UI for RUMI Scientist AI."""

    def __init__(self, face_path=None, size=None):
        self.W = None
        self.H = None

        # State
        self.speaking = False
        self.muted = False
        self.focus_mode = False
        self._think_mode = False
        self._deep_dive_active = False
        self._rumi_state = "INITIALISING"
        self.status_text = "INITIALISING"
        self._start_time = time.time()

        # Callbacks
        self.on_text_command = None
        self.on_focus_mode_toggle = None
        self.on_think_mode_toggle = None
        self.on_deep_dive_toggle = None

        # Threading
        self._running = True
        self._input_lock = threading.Lock()

        # Input history & completion
        self._pt_history = InMemoryHistory() if HAVE_PT else None
        self._message_count = 0

        # ── Animated Startup ──────────────────────────────────────
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

    # ── Startup ─────────────────────────────────────────────────
    def _show_startup(self):
        """Display animated startup sequence."""
        console.clear()

        # Print logo with fade-in effect
        console.print()
        lines = RUMI_LOGO.split('\n')
        for line in lines:
            console.print(Text(line, style=f"bold {C_CYAN}"), justify="center")
            time.sleep(0.03)

        console.print()
        console.print(Text("SCIENTIST AI", style=f"bold {C_WHITE}"), justify="center")
        console.print(Text("Autonomous Scientific Research System", style=f"dim {C_CYAN}"), justify="center")
        console.print(
            Text(f"14 Scientist Modules  •  60+ Brain Modules  •  {platform.system().upper()}", style=f"dim {C_DIM}"),
            justify="center"
        )
        console.print()

        # Animated loading indicator
        with Progress(
            SpinnerColumn(spinner_name="dots", style=C_CYAN),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            tasks = [
                "  Initializing neural engines...",
                "  Loading memory systems...",
                "  Preparing tools manifest...",
                "  Calibrating research modules...",
            ]
            for desc in tasks:
                t = progress.add_task(desc, total=None)
                time.sleep(0.35)
                progress.remove_task(t)

        console.print()

        # System info grid
        info = Table.grid(padding=(0, 2))
        info.add_column(style=f"dim {C_DIM}")
        info.add_column(style=C_CYAN)
        info.add_row("◆ Model:", "Gemini 2.5 Flash")
        info.add_row("◆ Scientist:", "15 modules (discovery, tournament, KG, reproducibility, notebook, ...)")
        info.add_row("◆ Brain:", "60+ cognitive modules")
        info.add_row("◆ Mode:", "Interactive")
        info.add_row("◆ Status:", "Ready")
        console.print(info)
        console.print()
        console.print(Rule(style=f"dim {C_VIOLET}"))
        console.print(Text(f"  Type /help for commands  •  /science for capabilities   —   {datetime.now().strftime('%H:%M:%S')}", style=f"dim {C_DIM}"))
        console.print()

    # ── Input Loop ──────────────────────────────────────────────
    def _input_loop(self):
        """Background thread reading user input via prompt_toolkit or fallback."""
        pt_style = PtStyle([
            ('prompt', f'bold {C_CYAN}'),
        ]) if HAVE_PT else None

        while self._running:
            try:
                if HAVE_PT and self._pt_history is not None:
                    from prompt_toolkit.completion import WordCompleter
                    _completer = WordCompleter(SLASH_COMMANDS, ignore_case=True)
                    value = _pt_prompt(
                        "⚗  ",
                        history=self._pt_history,
                        style=pt_style,
                        completer=_completer,
                        complete_while_typing=True,
                    )
                else:
                    value = input("⚗  ")

                value = value.strip()
                if not value:
                    continue

                # Handle slash commands
                if value.startswith("/"):
                    self._handle_command(value)
                    continue

                # Dispatch to main app
                if self.on_text_command:
                    self._message_count += 1
                    self.write_log(f"You: {value}")
                    threading.Thread(target=self.on_text_command, args=(value,), daemon=True).start()

            except (EOFError, KeyboardInterrupt):
                console.print()
                self._handle_command("/exit")
                break
            except Exception as e:
                time.sleep(0.1)

    def _handle_command(self, cmd: str):
        """Handle slash commands."""
        cmd = cmd.lower().strip()

        if cmd == "/help":
            console.print(Markdown(HELP_TEXT))
            console.print()

        elif cmd == "/clear":
            console.clear()
            console.print(Text(RUMI_LOGO, style=f"bold {C_CYAN}"), justify="center")
            console.print()

        elif cmd == "/focus":
            self.focus_mode = not self.focus_mode
            self.write_log(f"SYS: Focus Mode {'activated' if self.focus_mode else 'deactivated'}.")
            if self.on_focus_mode_toggle:
                threading.Thread(target=self.on_focus_mode_toggle, args=(self.focus_mode,), daemon=True).start()

        elif cmd == "/think":
            self._think_mode = not self._think_mode
            self.write_log(f"SYS: Think Mode {'activated' if self._think_mode else 'deactivated'}.")
            if self.on_think_mode_toggle:
                threading.Thread(target=self.on_think_mode_toggle, args=(self._think_mode,), daemon=True).start()

        elif cmd == "/dive":
            self._deep_dive_active = not self._deep_dive_active
            self.write_log(f"SYS: Deep Dive mode {'activated' if self._deep_dive_active else 'deactivated'}.")
            if self.on_deep_dive_toggle:
                threading.Thread(target=self.on_deep_dive_toggle, args=(self._deep_dive_active,), daemon=True).start()

        elif cmd == "/mute":
            self.toggle_mute()

        elif cmd == "/status":
            uptime = int(time.time() - self._start_time)
            info = Table.grid(padding=(0, 2))
            info.add_column(style=f"bold {C_WHITE}")
            info.add_column(style=C_CYAN)
            info.add_row("Uptime:",   f"{uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}")
            info.add_row("Status:",   self._rumi_state)
            info.add_row("Mode:",     f"{'Focus ' if self.focus_mode else ''}{'Think ' if self._think_mode else ''}{'Dive ' if self._deep_dive_active else ''}Normal")
            info.add_row("Messages:", str(self._message_count))
            info.add_row("Muted:",    "Yes" if self.muted else "No")
            info.add_row("Model:",    "Gemini 2.5 Flash")
            info.add_row("OS:",       platform.system())
            console.print(Panel(info, title="[bold]System Status[/bold]", border_style=C_BLUE, box=ROUNDED))
            console.print()

        elif cmd == "/stats":
            uptime = int(time.time() - self._start_time)
            hours = uptime // 3600
            mins = (uptime % 3600) // 60
            secs = uptime % 60
            info = Table.grid(padding=(0, 2))
            info.add_column(style=f"bold {C_WHITE}")
            info.add_column(style=C_GREEN)
            info.add_row("Session Duration:", f"{hours:02d}h {mins:02d}m {secs:02d}s")
            info.add_row("Messages Sent:",   str(self._message_count))
            info.add_row("Avg Rate:",        f"{self._message_count / max(uptime, 1) * 3600:.1f}/hr" if self._message_count > 0 else "N/A")
            info.add_row("Focus Mode:",       "On" if self.focus_mode else "Off")
            info.add_row("Think Mode:",       "On" if self._think_mode else "Off")
            info.add_row("Deep Dive:",        "On" if self._deep_dive_active else "Off")
            info.add_row("State:",            self._rumi_state)
            console.print(Panel(info, title="[bold]Session Statistics[/bold]", border_style=C_GREEN, box=ROUNDED))
            console.print()

        elif cmd == "/science":
            self._show_science_help()

        elif cmd == "/discover":
            self.write_log("SYS: Dispatching discovery pipeline...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Run the autonomous scientific discovery pipeline on a topic of your choice. Ask me what topic to research.",),
                    daemon=True,
                ).start()

        elif cmd == "/hypothesize":
            self.write_log("SYS: Generating hypotheses...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Generate diverse research hypotheses using the tournament engine. What topic should I hypothesize about?",),
                    daemon=True,
                ).start()

        elif cmd == "/experiment":
            self.write_log("SYS: Experiment design mode...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Help me design a scientific experiment. What hypothesis should I test?",),
                    daemon=True,
                ).start()

        elif cmd == "/papers":
            self.write_log("SYS: Paper search mode...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Search for academic papers. Who or what topic should I search for?",),
                    daemon=True,
                ).start()

        elif cmd == "/review":
            self.write_log("SYS: Peer review mode...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Perform a peer review on a paper or scientific claim. Paste the text or describe what to review.",),
                    daemon=True,
                ).start()

        elif cmd == "/graph":
            self.write_log("SYS: Knowledge graph mode...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Show me the current knowledge graph stats and recent entries.",),
                    daemon=True,
                ).start()

        elif cmd == "/notebook":
            self.write_log("SYS: Lab notebook mode...")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=("Show my recent lab notebook entries and stats.",),
                    daemon=True,
                ).start()

        elif cmd == "/domains":
            self._show_domains()

        elif cmd == "/exit":
            self.write_log("SYS: Shutting down RUMI...")
            self._running = False
            os._exit(0)

        else:
            console.print(Text(f"  Unknown command: {cmd}", style=f"bold {C_RED}"))
            console.print(Text("  Type /help to see available commands.", style=f"dim {C_DIM}"))

    def _heartbeat_loop(self):
        """Background thread for thinking state animations."""
        dots = 0
        while self._running:
            if self._rumi_state in ("THINKING", "PROCESSING"):
                dots = (dots + 1) % 4
                # In a terminal without live display, we just let write_log handle it
                time.sleep(0.5)
            else:
                dots = 0
                time.sleep(1)

    # ── Public API ──────────────────────────────────────────────
    def write_log(self, text: str):
        """Display a formatted log message in the terminal.

        Handles prefixes:
          'You:'   → user message (blue panel)
          'RUMI:'  → AI response (cyan panel with markdown)
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
                console.print(Panel(
                    Text(content, style=C_WHITE),
                    title="[bold]◈ You[/bold]",
                    border_style=C_BLUE,
                    box=ROUNDED,
                    padding=(0, 1),
                ))

            elif tl.startswith("rumi:") or tl.startswith("ai:"):
                prefix_len = 5 if tl.startswith("rumi:") else 3
                content = text[prefix_len:].strip()

                # Attempt markdown rendering
                try:
                    body = Markdown(content)
                except Exception:
                    body = Text(content, style=C_CYAN)

                console.print(Panel(
                    body,
                    title=f"[bold {C_CYAN}]🔬 RUMI[/bold {C_CYAN}]",
                    border_style=C_CYAN,
                    box=ROUNDED,
                    padding=(0, 1),
                ))
                self.set_state("SPEAKING")

            elif tl.startswith("sys:"):
                content = text[4:].strip()
                color = C_YELLOW if "activated" in content or "deactivated" in content else C_DIM
                console.print(Text(f"  ⚙ {content}", style=f"italic {color}"))

            elif tl.startswith("err:") or tl.startswith("error:"):
                console.print(Text(f"  ✖ {text[4:].strip()}", style=f"bold {C_RED}"))

            else:
                console.print(Text(f"  {text}", style=C_WHITE))

    def set_state(self, state: str):
        """Update RUMI's state indicator."""
        self._rumi_state = state
        lut = {
            "MUTED":      "MUTED",
            "SPEAKING":   "SPEAKING",
            "THINKING":   "THINKING",
            "LISTENING":  "LISTENING",
            "PROCESSING": "PROCESSING",
        }
        self.status_text = lut.get(state, "ONLINE")

        if state == "THINKING":
            console.print(Text("  ⏳ RUMI is thinking...", style=f"italic {C_YELLOW}"))
        elif state == "SPEAKING":
            pass  # Response follows naturally
        elif state == "LISTENING":
            pass  # Quiet state

    def start_speaking(self):
        """Mark the start of speech output."""
        self.set_state("SPEAKING")

    def stop_speaking(self):
        """Mark the end of speech output."""
        if not self.muted:
            self.set_state("LISTENING")

    def show_toast(self, message: str, duration: float = 2.5):
        """Display a brief notification message."""
        console.print(Text(f"  ◈ {message}", style=f"bold {C_CYAN}"))

    def toggle_mute(self):
        """Toggle microphone mute state."""
        self.muted = not self.muted
        if self.muted:
            console.print(Text("  ⊘ Microphone muted", style=f"bold {C_RED}"))
        else:
            console.print(Text("  ◉ Microphone active", style=f"bold {C_GREEN}"))

    def feed_amplitude(self, amplitude: float):
        """Receive voice amplitude data (no-op in terminal mode)."""
        pass

    def wait_for_api_key(self):
        """Block until API keys are configured."""
        while not self._api_key_ready:
            time.sleep(0.1)

    def _show_science_help(self):
        """Show Scientist AI capabilities."""
        table = Table(
            title="RUMI Scientist AI — Capabilities",
            border_style=C_CYAN,
            box=ROUNDED,
            show_lines=True,
        )
        table.add_column("Module", style=f"bold {C_CYAN}")
        table.add_column("What It Does", style=C_WHITE)
        table.add_column("Example Prompt", style=f"dim {C_DIM}")

        capabilities = [
            ("Discovery Engine", "Full pipeline: idea → experiment → paper → review", "Discover new insights about quantum computing"),
            ("Tournament Hypotheses", "GFlowNet-style diverse generation + tournament selection", "Generate 10 hypotheses about neural scaling laws"),
            ("Knowledge Graph", "Build structured knowledge, find gaps, multi-hop reasoning", "Add transformer paper to knowledge graph and find gaps"),
            ("Novelty Checker", "Check if an idea is novel against existing literature", "Is this idea novel: using GFlowNets for protein design?"),
            ("Experiment Designer", "Design and run sandboxed experiments", "Design an experiment to test if attention is all you need"),
            ("Reproducibility", "Extract claims and verify published results", "Reproduce the claims in the Chinchilla scaling paper"),
            ("Active Experiment Selector", "Bayesian optimal experiment selection", "What experiment should I run next to test my hypotheses?"),
            ("Cross-Domain Connector", "Find analogies across scientific fields", "Find analogies between evolution and neural architecture search"),
            ("Peer Reviewer", "Automated peer review with scoring", "Review this paper section for methodological rigor"),
            ("Paper Generator", "Generate structured LaTeX manuscripts", "Write a paper draft about our findings on scaling laws"),
            ("Research Team", "Multi-agent debate with specialized roles", "Debate whether transformers will scale to AGI"),
            ("Feynman Reducer", "First-principles decomposition", "Explain backpropagation from first principles"),
            ("Cross Validator", "Statistical validation and reproducibility", "Validate these experimental results with bootstrap sampling"),
            ("Scientist Search", "Search papers from famous researchers", "Find papers by Yoshua Bengio about GFlowNets"),
            ("Lab Notebook", "Track experiments, observations, measurements", "Create a notebook entry for my scaling law experiment"),
        ]

        for name, desc, example in capabilities:
            table.add_row(name, desc, example)

        console.print()
        console.print(table)
        console.print()

    def _show_domains(self):
        """Show available scientific domains."""
        table = Table(
            title="Scientific Domains for Cross-Domain Analysis",
            border_style=C_PURPLE,
            box=ROUNDED,
        )
        table.add_column("Domain", style=f"bold {C_CYAN}")
        table.add_column("Core Concepts", style=C_WHITE)

        domains = [
            ("Physics", "energy, force, momentum, entropy, symmetry, conservation, field, wave"),
            ("Biology", "evolution, fitness, adaptation, selection, mutation, gene, organism"),
            ("Computer Science", "algorithm, complexity, abstraction, optimization, learning, network"),
            ("Economics", "utility, equilibrium, incentive, market, trade, game, strategy"),
            ("Chemistry", "bond, reaction, catalyst, equilibrium, kinetics, thermodynamics"),
            ("Mathematics", "proof, structure, mapping, invariant, convergence, topology"),
            ("Neuroscience", "neuron, synapse, plasticity, representation, learning, attention"),
            ("Ecology", "niche, competition, cooperation, diversity, stability, resilience"),
        ]

        for name, concepts in domains:
            table.add_row(name, concepts)

        console.print()
        console.print(table)
        console.print(Text("  Use: 'Find analogies between [concept] in [domain1] and [domain2]'", style=f"dim {C_DIM}"))
        console.print()

    # ── API Key Setup ───────────────────────────────────────────
    def _show_setup_ui(self):
        """Terminal-based first-time setup for API keys."""
        console.print()
        console.print(Rule(style=f"bold {C_PURPLE}"))
        console.print(Text("  FIRST BOOT — API KEY SETUP", style=f"bold {C_WHITE}"), justify="center")
        console.print(Rule(style=f"bold {C_PURPLE}"))
        console.print()

        detected = _detect_os()

        console.print(Text("  Enter your Gemini API key:", style=C_CYAN))
        console.print(Text("  (Get one at: https://aistudio.google.com/apikey)", style=f"dim {C_DIM}"))
        console.print()

        gemini_key = input("  🔑 ").strip()

        while not gemini_key:
            console.print(Text("  API key cannot be empty.", style=f"bold {C_RED}"))
            gemini_key = input("  🔑 ").strip()

        console.print()
        console.print(Text(f"  Your callsign (default: OPERATOR):", style=C_CYAN))
        user_name = input("  👤 ").strip().upper() or "OPERATOR"

        # Save config
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(API_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "gemini_api_key": gemini_key,
                "openai_api_key": "",
                "primary_provider": "gemini",
                "os_system": detected,
                "camera_index": 0,
                "user_name": user_name,
            }, f, indent=4)

        from brain import model_router as mr_module
        mr_module._router_instance = None

        self._api_key_ready = True
        self.set_state("LISTENING")

        console.print()
        console.print(Text(f"  ◈ RUMI online. Welcome, {user_name}.", style=f"bold {C_GREEN}"))
        console.print()
