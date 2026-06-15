#!/usr/bin/env python3
"""
rumi_tui.py -- RUMI Scientist AI Textual TUI
Full smart chat with LLM, discovery pipeline, modes, brain modules.

Usage: python rumi_tui.py [--demo]
"""

import asyncio
import contextlib
import concurrent.futures
import io
import json
import sys
import time
import re
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Input, RichLog, Rule, Static
from rich.text import Text
from rich.markdown import Markdown

# ── Colors ────────────────────────────────────────────────────────
CYAN     = "#00E5FF"
GREEN    = "#00E676"
AMBER    = "#FFD740"
RED      = "#FF1744"
PURPLE   = "#B388FF"
PINK     = "#FF80AB"
DIM      = "#6B7D8E"
DIMMER   = "#3A4A58"
BG       = "#060A10"
BORDER   = "#1A2635"

RUMI_LOGO = r"""
[bold #00E5FF]  ██████╗ ██╗   ██╗███╗   ███╗██╗
  ██╔══██╗██║   ██║████╗ ████║██║
  ██████╔╝██║   ██║██╔████╔██║██║
  ██╔══██╗██║   ██║██║╚██╔╝██║██║
  ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║
  ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝[/]

  [dim]Research Unified Machine Intelligence -- v2.0[/]"""

# ── System prompt for chat ────────────────────────────────────────
SYSTEM_PROMPT = """You are RUMI (Research Unified Machine Intelligence), an autonomous AI scientist.
You are direct, analytical, and scientifically rigorous. You think step by step.
You can discuss any topic but excel at scientific research, hypothesis generation,
and knowledge synthesis. Keep responses concise unless depth is requested.
When the user asks you to discover, research, or investigate a scientific topic,
respond with [DISCOVERY:<topic>] to trigger the discovery pipeline."""

# ── Discovery intent detection ────────────────────────────────────
_DISCOVERY_PATTERNS = [
    r'(?:run|do|start|begin|launch)\s+(?:a\s+)?(?:full|deep|complete)?\s*(?:discovery|pipeline|research|analysis)\s+(?:on|about|for)?\s*(.+)',
    r'(?:discover|investigate|explore|analyze|study)\s+(.+)',
    r'(?:what\s+(?:do|does|can)\s+(?:we|you|I)\s+know\s+about)\s+(.+)',
    r'(?:tell\s+me\s+(?:everything|all)\s+about)\s+(.+)',
]

# ── Pipeline phases ──────────────────────────────────────────────
PHASES = [
    ("curious",       "Curious Questioning",  "curious_questioning"),
    ("literature",    "Literature Search",     "literature"),
    ("citation",      "Citation Network",      "citation_network"),
    ("kg",            "Knowledge Graph",       "knowledge_graph"),
    ("gaps",          "Gap Detection",         "gap_detection"),
    ("refine_lit",    "Literature Refinement", "literature_refinement"),
    ("anomalies",     "Anomaly Detection",     "anomaly_detection"),
    ("missing_vars",  "Missing Variables",     "missing_variables"),
    ("mechanisms",    "Mechanism Generation",  "mechanism_generation"),
    ("predictions",   "Prediction Engine",     "prediction_engine"),
    ("competition",   "Theory Competition",    "theory_competition"),
    ("adversarial",   "Adversarial Test",      "adversarial_test"),
    ("compute",       "Computational Verify",  "computational_verification"),
    ("experiments",   "Experiment Planning",   "experimental_validation"),
    ("contradictions","Contradiction Mining",  "contradictions"),
    ("skeptic",       "Skeptic Review",        "skeptic_review"),
    ("scoring",       "Discovery Scoring",     "discovery_scoring"),
]

AGENTS = [
    ("literature", "Literature",  CYAN),
    ("graph",      "Graph Build", PURPLE),
    ("gap",        "Gap Detect",  AMBER),
    ("theory",     "Theory Gen",  GREEN),
    ("skeptic",    "Skeptic",     RED),
    ("experiment", "Experiment",  PINK),
]


def _detect_discovery(text):
    """Check if user text is a discovery request."""
    text_lower = text.lower().strip()
    for pattern in _DISCOVERY_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            return m.group(1).strip()
    return None


# ══════════════════════════════════════════════════════════════════
# WIDGETS
# ══════════════════════════════════════════════════════════════════

class HeaderBar(Static):
    CSS = "HeaderBar { width: 100%; height: 1; background: #101820; padding: 0 2; }"
    def __init__(self, **kw):
        super().__init__(**kw)
        self._start = time.time()
        self._tokens = 0
        self._status = "READY"
        self._mode = ""
        self._provider = ""

    def add_tokens(self, n): self._tokens += n; self.refresh()
    def set_status(self, s): self._status = s; self.refresh()
    def set_mode(self, m): self._mode = m; self.refresh()
    def set_provider(self, p): self._provider = p; self.refresh()

    def render(self) -> Text:
        e = int(time.time() - self._start)
        up = f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"
        t = Text()
        t.append(" RUMI ", style=f"bold {CYAN}")
        t.append("  ", style=DIMMER)
        t.append(up, style=DIM)
        t.append("   ", style=DIMMER)
        t.append(f"{self._tokens:,} tok", style=DIM)
        t.append("   ", style=DIMMER)
        t.append(self._status, style=GREEN if self._status == "READY" else AMBER)
        if self._mode:
            t.append("   ", style=DIMMER)
            t.append(self._mode, style=PURPLE)
        if self._provider:
            t.append("   ", style=DIMMER)
            t.append(self._provider, style=DIM)
        return t


class PanelHeader(Static):
    CSS = "PanelHeader { width: 100%; height: 1; background: #0C1218; padding: 0 2; }"
    def __init__(self, text, color=CYAN, **kw):
        super().__init__(**kw)
        self._text = text; self._color = color
    def render(self) -> Text:
        return Text(self._text, style=f"bold {self._color}")


class PipelineView(Static):
    CSS = "PipelineView { width: 100%; height: auto; padding: 1 2; }"
    def __init__(self, **kw):
        super().__init__(**kw)
        self._st = {p[0]: "pending" for p in PHASES}

    def set_phase(self, pid, st):
        if pid in self._st: self._st[pid] = st; self.refresh()

    def mark_done_from_report(self, report_phases):
        key_map = {p[2]: p[0] for p in PHASES}
        for k in report_phases:
            if k in key_map: self._st[key_map[k]] = "done"
        self.refresh()

    def reset(self):
        for k in self._st: self._st[k] = "pending"
        self.refresh()

    def pct(self):
        d = sum(1 for v in self._st.values() if v == "done")
        return int(d / len(self._st) * 100) if self._st else 0

    def render(self) -> Text:
        t = Text()
        for pid, label, _ in PHASES:
            s = self._st.get(pid, "pending")
            if s == "done":
                t.append("  [X] ", style=GREEN); t.append(f"{label}\n", style=GREEN)
            elif s == "running":
                t.append("  [~] ", style=CYAN); t.append(f"{label}", style=f"bold {CYAN}"); t.append("  <<\n", style=CYAN)
            elif s == "error":
                t.append("  [!] ", style=RED); t.append(f"{label}\n", style=RED)
            else:
                t.append("  [ ] ", style=DIMMER); t.append(f"{label}\n", style=DIMMER)
        return t


class AgentView(Static):
    CSS = "AgentView { width: 100%; height: auto; padding: 1 2; }"
    def __init__(self, **kw):
        super().__init__(**kw)
        self._st = {a: "idle" for a, _, _ in AGENTS}
        self._msg = {a: "" for a, _, _ in AGENTS}
        self._prog = {a: 0 for a, _, _ in AGENTS}
        self._tick = 0

    def set_agent(self, aid, st, msg="", prog=0):
        self._st[aid] = st
        if msg: self._msg[aid] = msg
        self._prog[aid] = prog; self.refresh()

    def reset(self):
        for a in self._st: self._st[a] = "idle"; self._msg[a] = ""; self._prog[a] = 0
        self.refresh()

    def render(self) -> Text:
        self._tick += 1; t = Text()
        for aid, name, color in AGENTS:
            s = self._st.get(aid, "idle"); p = self._prog.get(aid, 0)
            if s == "working":
                dot = "\u25cf" if self._tick % 2 else "\u25cb"
                t.append(f"  {dot} ", style=color); t.append(f"{name:14s}", style=f"bold {color}")
                if p > 0:
                    bw = 14; filled = int(bw * p / 100)
                    bar = "\u2588" * filled + "\u2591" * (bw - filled)
                    t.append(f" {bar} {p:3d}%", style=color)
                t.append("\n")
            elif s == "done":
                t.append(f"  \u25cf ", style=GREEN); t.append(f"{name:14s}", style=GREEN); t.append(" done\n", style=DIMMER)
            elif s == "error":
                t.append(f"  \u2716 ", style=RED); t.append(f"{name:14s}", style=RED); t.append(" error\n", style=RED)
            else:
                t.append(f"  \u25cb ", style=DIMMER); t.append(f"{name}\n", style=DIMMER)
        return t


class BrainView(Static):
    CSS = "BrainView { width: 100%; height: auto; padding: 1 2; }"
    GROUPS = {
        "Memory":    ["neural", "episodic", "procedural", "vector"],
        "Reasoning": ["active_inf", "causal", "neurosym", "analogy"],
        "Creative":  ["creative", "intuition", "narrative"],
        "Awareness": ["self_model", "aware", "metacog", "world"],
        "Learning":  ["learn", "meta_learn", "transfer", "improve"],
        "Science":   ["discover", "kg", "tournament", "xdomain"],
    }
    def __init__(self, **kw):
        super().__init__(**kw); self._loaded = set()
    def set_loaded(self, mods): self._loaded = set(mods); self.refresh()
    def render(self) -> Text:
        t = Text()
        for group, mods in self.GROUPS.items():
            t.append(f"  {group:12s}", style=f"bold {PURPLE}")
            for m in mods:
                t.append(" \u25cf" if m in self._loaded else " \u25cb", style=GREEN if m in self._loaded else DIMMER)
            t.append("\n")
        return t


class DiscoveryView(Static):
    CSS = "DiscoveryView { width: 100%; height: auto; padding: 1 2; }"
    def __init__(self, **kw):
        super().__init__(**kw)
        self._topic = ""; self._pct = 0
        self._papers = 0; self._entities = 0; self._gaps = 0
        self._anomalies = 0; self._score = 0.0; self._grade = ""

    def set_topic(self, v): self._topic = v; self.refresh()
    def set_progress(self, v): self._pct = v; self.refresh()

    def set_from_report(self, report):
        phases = report.get("phases", {})
        self._papers = phases.get("literature", {}).get("papers_found", 0)
        self._entities = phases.get("knowledge_graph", {}).get("entities", 0)
        self._gaps = len(phases.get("gap_detection", {}).get("top_gaps", []))
        self._anomalies = len(phases.get("anomaly_detection", {}).get("top_anomalies", []))
        self._score = phases.get("discovery_scoring", {}).get("discovery_score", 0)
        self._grade = phases.get("discovery_scoring", {}).get("grade", "")
        self.refresh()

    def render(self) -> Text:
        t = Text(); bw = 28; filled = int(bw * self._pct / 100)
        bar = "\u2588" * filled + "\u2591" * (bw - filled)
        t.append("\n")
        t.append("  +", style=BORDER); t.append("=" * 46, style=BORDER); t.append("+\n", style=BORDER)
        t.append("  | ", style=BORDER); t.append("DISCOVERY ENGINE", style=f"bold {CYAN}")
        t.append(" " * 31, style=BG); t.append("|\n", style=BORDER)
        t.append("  | ", style=BORDER); t.append("-" * 46, style=BORDER); t.append("|\n", style=BORDER)
        if self._topic:
            topic_trunc = self._topic[:40]; pad = 41 - len(topic_trunc)
            t.append("  | ", style=BORDER); t.append("Topic: ", style=DIM); t.append(topic_trunc, style=AMBER)
            t.append(" " * max(pad, 1), style=BG); t.append("|\n", style=BORDER)
            t.append("  | ", style=BORDER); t.append(f" [{bar}] {self._pct:3d}%", style=CYAN)
            pad2 = 49 - len(f" [{bar}] {self._pct:3d}%"); t.append(" " * max(pad2, 1), style=BG); t.append("|\n", style=BORDER)
            stats = f" {self._papers} papers  {self._entities} entities  {self._gaps} gaps  {self._anomalies} anomalies"
            t.append("  | ", style=BORDER); t.append(stats, style=DIM)
            pad3 = 47 - len(stats); t.append(" " * max(pad3, 1), style=BG); t.append("|\n", style=BORDER)
            if self._score > 0:
                score_str = f" Score: {self._score:.0f}/100 ({self._grade})"
                t.append("  | ", style=BORDER); t.append(score_str, style=GREEN if self._score > 50 else AMBER)
                pad4 = 47 - len(score_str); t.append(" " * max(pad4, 1), style=BG); t.append("|\n", style=BORDER)
        else:
            t.append("  | ", style=BORDER); t.append("No active discovery", style=DIMMER)
            t.append(" " * 27, style=BG); t.append("|\n", style=BORDER)
            t.append("  | ", style=BORDER); t.append("Type anything to chat, or 'discover X'", style=DIMMER)
            t.append(" " * 6, style=BG); t.append("|\n", style=BORDER)
        t.append("  +", style=BORDER); t.append("-" * 46, style=BORDER); t.append("+\n", style=BORDER)
        return t


# ══════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════

class RumiTUI(App):
    CSS = """
    Screen { background: #060A10; color: #E0E6ED; }

    #boot-overlay {
        width: 100%; height: 100%; background: #060A10;
        align: center middle; content-align: center middle;
    }
    #boot-logo { width: auto; height: auto; text-align: center; }
    #boot-status { width: auto; height: auto; text-align: center; margin-top: 1; }

    #main-container { width: 100%; height: 100%; layout: horizontal; }

    #left-panel { width: 2fr; height: 100%; background: #060A10; }
    #right-panel { width: 3fr; height: 100%; background: #060A10; layout: vertical; }

    #chat-log { width: 100%; height: 1fr; background: #060A10; border: heavy #1A2635; padding: 0 1; }
    #input-bar { width: 100%; height: auto; padding: 0 1 1 1; }
    #hint { height: 1; color: #3A4A58; padding: 0 1; }
    #chat-input { width: 100%; background: #0C1218; border: heavy #1A2635; color: #E0E6ED; }
    #chat-input:focus { border: heavy #00E5FF; }
    .divider { color: #1A2635; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, demo=False):
        super().__init__()
        self.demo = demo
        self._tokens = 0
        self._busy = False
        self._cancel = asyncio.Event()
        self._history = []  # conversation history
        self._modes = {"think": False, "deep_dive": False}

    def compose(self) -> ComposeResult:
        yield Container(
            Static(RUMI_LOGO, id="boot-logo"),
            Static("", id="boot-status"),
            id="boot-overlay",
        )
        with Horizontal(id="main-container"):
            with VerticalScroll(id="left-panel"):
                yield HeaderBar(id="header")
                yield PanelHeader("  PIPELINE", CYAN)
                yield PipelineView(id="pipeline")
                yield Rule(line_style="heavy", classes="divider")
                yield PanelHeader("  AGENTS", PURPLE)
                yield AgentView(id="agents")
                yield Rule(line_style="heavy", classes="divider")
                yield PanelHeader("  BRAIN MODULES", AMBER)
                yield BrainView(id="brain")
            with Vertical(id="right-panel"):
                yield DiscoveryView(id="discovery")
                yield Rule(line_style="heavy", classes="divider")
                yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
                with Vertical(id="input-bar"):
                    yield Static("  [dim]Ctrl+L clear  Esc cancel  /help for commands[/]", id="hint")
                    yield Input(placeholder="Ask Rumi anything...", id="chat-input")

    # ── Lifecycle ─────────────────────────────────────────────────

    async def on_mount(self):
        self.query_one("#main-container").display = False
        self.run_worker(self._boot(), exclusive=True)
        self.set_interval(0.5, lambda: self.query_one("#agents", AgentView).refresh())

    async def _boot(self):
        st = self.query_one("#boot-status", Static)
        lines = [
            ("Initializing RUMI neural architecture...", 0.3),
            ("Loading 60+ cognitive brain modules...", 0.3),
            ("Connecting to LLM providers...", 0.2),
            ("  [green]*[/] Groq (3)  [green]*[/] Gemini (4)  [green]*[/] Cerebras (6)  [green]*[/] NVIDIA", 0.3),
            ("  [green]*[/] Kimi K2.6  [green]*[/] GLM 5.1  [green]*[/] Fireworks  [green]*[/] Xiaomi MiMo", 0.2),
            ("17 scientific domains loaded", 0.2),
            ("Discovery pipeline v2 ready", 0.2),
            ("All systems nominal", 0.3),
        ]
        for line, delay in lines:
            st.update(f"\n  {line}")
            await asyncio.sleep(delay)

        self.query_one("#boot-overlay").display = False
        self.query_one("#main-container").display = True

        self.query_one("#brain", BrainView).set_loaded([
            "neural", "episodic", "procedural", "vector",
            "active_inf", "causal", "neurosym", "analogy",
            "creative", "intuition", "narrative",
            "self_model", "aware", "metacog", "world",
            "learn", "meta_learn", "transfer", "improve",
            "discover", "kg", "tournament", "xdomain",
        ])

        self._chat("system", "RUMI Scientist AI v2.0 online")
        self._chat("system", "60+ modules | 8 LLM providers | pipeline v2")
        self._chat("system", "Type anything to chat. 'discover X' for pipeline. /help for commands.")
        self.query_one("#chat-input").focus()

        if self.demo:
            await asyncio.sleep(1.5)
            await self._handle_input("What is the Casimir effect and how does it relate to negative energy density?")

    # ── Chat display ──────────────────────────────────────────────

    def _chat(self, role, content):
        try:
            log = self.query_one("#chat-log", RichLog)
        except Exception:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        colors = {"user": CYAN, "assistant": "#E0E6ED", "tool": AMBER, "system": DIM, "error": RED}
        glyphs = {"user": ">", "assistant": "*", "tool": "~", "system": "#", "error": "!"}
        c = colors.get(role, DIM); g = glyphs.get(role, "-")
        msg = Text()
        msg.append(f" {ts} ", style=DIMMER)
        msg.append(f"{g} ", style=c)
        if role == "user":
            msg.append(content, style=f"bold {c}")
        elif role in ("system", "error"):
            msg.append(content, style=c)
        else:
            # Try to render as markdown
            try:
                log.write(msg)
                md = Markdown(content)
                log.write(md)
                return
            except Exception:
                msg.append(content)
        log.write(msg)

    # ── Input handling ────────────────────────────────────────────

    async def on_input_submitted(self, event):
        q = event.value.strip()
        if not q: return
        event.input.value = ""
        await self._handle_input(q)

    async def _handle_input(self, text):
        self._chat("user", text)

        # Commands
        if text.startswith("/"):
            await self._handle_command(text)
            return

        # Check for discovery intent
        discovery_topic = _detect_discovery(text)
        if discovery_topic:
            self.run_worker(self._run_discovery(discovery_topic), exclusive=True)
            return

        # Normal LLM chat
        self.run_worker(self._llm_chat(text), exclusive=True)

    # ── Commands ──────────────────────────────────────────────────

    async def _handle_command(self, text):
        parts = text.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("/help", "/h", "/?"):
            self._chat("system", "[bold]RUMI TUI Commands[/]")
            self._chat("system", "  /help           Show this help")
            self._chat("system", "  /think          Toggle think mode")
            self._chat("system", "  /dive           Toggle deep dive mode")
            self._chat("system", "  /discover TOPIC Run discovery pipeline")
            self._chat("system", "  /curiosity      Run curiosity scan")
            self._chat("system", "  /evolve         Show evolution status")
            self._chat("system", "  /clear          Clear chat")
            self._chat("system", "  /quit           Exit")
            self._chat("system", "")
            self._chat("system", "Just type anything for normal chat.")
            self._chat("system", "'discover X' or 'research X' triggers pipeline.")

        elif cmd == "/think":
            self._modes["think"] = not self._modes["think"]
            mode = "ON" if self._modes["think"] else "OFF"
            self._chat("system", f"Think mode: {mode}")
            self.query_one("#header", HeaderBar).set_mode(
                "think" if self._modes["think"] else "")

        elif cmd == "/dive":
            self._modes["deep_dive"] = not self._modes["deep_dive"]
            mode = "ON" if self._modes["deep_dive"] else "OFF"
            self._chat("system", f"Deep dive mode: {mode}")
            self.query_one("#header", HeaderBar).set_mode(
                "dive" if self._modes["deep_dive"] else "")

        elif cmd == "/discover":
            if args:
                self.run_worker(self._run_discovery(args), exclusive=True)
            else:
                self._chat("system", "Usage: /discover <topic>")

        elif cmd == "/curiosity":
            self._chat("system", "Running curiosity scan...")
            self.run_worker(self._run_curiosity(), exclusive=True)

        elif cmd == "/evolve":
            self._chat("system", "Checking evolution status...")
            self.run_worker(self._run_evolve(), exclusive=True)

        elif cmd in ("/clear", "/cls"):
            self.query_one("#chat-log", RichLog).clear()
            self._chat("system", "Chat cleared")

        elif cmd in ("/quit", "/exit", "/q"):
            self.exit()

        else:
            self._chat("system", f"Unknown command: {cmd}. Type /help")

    # ── LLM Chat (real) ───────────────────────────────────────────

    async def _llm_chat(self, user_msg):
        if self._busy:
            self._chat("system", "Busy... wait or press Esc")
            return

        self._busy = True
        hd = self.query_one("#header", HeaderBar)
        hd.set_status("THINKING")

        # Build prompt with history
        self._history.append({"role": "user", "content": user_msg})

        # Build full prompt with system + history
        prompt_parts = [SYSTEM_PROMPT]
        for msg in self._history[-10:]:  # last 10 messages
            role = msg["role"].upper()
            prompt_parts.append(f"{role}: {msg['content']}")
        prompt_parts.append("ASSISTANT:")
        full_prompt = "\n".join(prompt_parts)

        # Add mode instructions
        if self._modes["think"]:
            full_prompt = "[THINK MODE: Show your reasoning step by step]\n" + full_prompt
        if self._modes["deep_dive"]:
            full_prompt = "[DEEP DIVE: Be thorough, cite sources, be comprehensive]\n" + full_prompt

        # Call LLM in thread
        loop = asyncio.get_event_loop()
        response = None

        # Show immediate feedback
        self._chat("system", "Thinking...")

        def _call():
            try:
                from discovery.llm_client import call
                # Try cerebras first (fastest), then groq, then gemini
                for provider in ["cerebras", "groq", "gemini"]:
                    try:
                        result = call(full_prompt, max_tokens=4096, temperature=0.3, provider=provider)
                        if result:
                            return result
                    except Exception:
                        continue
                return "[All LLM providers failed - check API keys]"
            except Exception as e:
                return f"[Error: {e}]"

        try:
            response = await loop.run_in_executor(
                concurrent.futures.ThreadPoolExecutor(max_workers=1), _call)
        except Exception as e:
            response = f"[Error: {e}]"

        if response:
            # Check if response contains discovery trigger
            if "[DISCOVERY:" in response:
                topic_match = re.search(r'\[DISCOVERY:(.+?)\]', response)
                if topic_match:
                    topic = topic_match.group(1).strip()
                    response = re.sub(r'\[DISCOVERY:.+?\]', '', response).strip()
                    if response:
                        self._chat("assistant", response)
                    self._history.append({"role": "assistant", "content": response})
                    self.run_worker(self._run_discovery(topic), exclusive=True)
                    self._busy = False
                    hd.set_status("READY")
                    return

            self._chat("assistant", response)
            self._history.append({"role": "assistant", "content": response})
            self._tokens += len(response) // 4
            hd.add_tokens(len(response) // 4)
        else:
            self._chat("error", "No response from LLM providers")
            self._history.append({"role": "assistant", "content": "[no response]"})

        hd.set_status("READY")
        self._busy = False

    # ── Discovery Pipeline (real) ─────────────────────────────────

    async def _run_discovery(self, topic):
        if self._busy:
            self._chat("system", "Busy... wait or press Esc")
            return

        self._busy = True
        hd = self.query_one("#header", HeaderBar)
        dv = self.query_one("#discovery", DiscoveryView)
        pv = self.query_one("#pipeline", PipelineView)
        av = self.query_one("#agents", AgentView)

        dv.set_topic(topic); dv.set_progress(0)
        pv.reset(); av.reset()
        hd.set_status("DISCOVERING")

        for aid, _, _ in AGENTS:
            av.set_agent(aid, "working", "waiting...")

        self._chat("assistant", f"Starting discovery: [bold]{topic}[/]")
        self._history.append({"role": "assistant", "content": f"Starting discovery on: {topic}"})

        loop = asyncio.get_event_loop()
        captured = io.StringIO()
        report = None

        def _run():
            try:
                from discovery.discovery_pipeline_v2 import run_discovery_pipeline
                with contextlib.redirect_stdout(captured):
                    return run_discovery_pipeline(topic, domain="", mode="full")
            except Exception as e:
                return {"error": str(e)}

        try:
            report = await loop.run_in_executor(
                concurrent.futures.ThreadPoolExecutor(max_workers=1), _run)
        except Exception as e:
            report = {"error": str(e)}

        # Stream output
        output = captured.getvalue()
        if output:
            for line in output.split("\n"):
                line = line.strip()
                if line:
                    self._chat("system", line)

        if report and "error" not in report:
            phases = report.get("phases", {})
            pv.mark_done_from_report(phases)
            dv.set_progress(pv.pct())
            dv.set_from_report(report)

            for aid, _, _ in AGENTS:
                av.set_agent(aid, "done")

            papers = phases.get("literature", {}).get("papers_found", 0)
            entities = phases.get("knowledge_graph", {}).get("entities", 0)
            gaps = len(phases.get("gap_detection", {}).get("top_gaps", []))
            anomalies = len(phases.get("anomaly_detection", {}).get("top_anomalies", []))
            score = phases.get("discovery_scoring", {}).get("discovery_score", 0)
            grade = phases.get("discovery_scoring", {}).get("grade", "N/A")

            summary = f"Discovery complete: {papers} papers, {entities} entities, {gaps} gaps, {anomalies} anomalies, score {score:.0f}/100 ({grade})"
            self._chat("assistant", f"[bold {GREEN}]{summary}[/]")
            self._history.append({"role": "assistant", "content": summary})

            self._tokens += len(str(report)) // 4
            hd.add_tokens(len(str(report)) // 4)
        else:
            err = report.get("error", "Unknown") if report else "No report"
            self._chat("error", f"Discovery failed: {err}")
            for aid, _, _ in AGENTS:
                av.set_agent(aid, "error")

        hd.set_status("READY")
        self._busy = False

    # ── Curiosity scan ────────────────────────────────────────────

    async def _run_curiosity(self):
        try:
            from brain.curiosity import get_curiosity_module
            curiosity = get_curiosity_module()
            if curiosity:
                queue = curiosity.get_queue()
                if queue:
                    for item in queue[:5]:
                        self._chat("system", f"  {item}")
                else:
                    self._chat("system", "Curiosity queue is empty")
            else:
                self._chat("system", "Curiosity module not loaded")
        except Exception as e:
            self._chat("error", f"Curiosity error: {e}")

    async def _run_evolve(self):
        try:
            from brain.self_improve_engine import get_self_improve_engine
            engine = get_self_improve_engine()
            if engine:
                status = engine.get_status()
                self._chat("system", f"Evolution: {json.dumps(status, indent=2)}")
            else:
                self._chat("system", "Self-improve engine not loaded")
        except Exception as e:
            self._chat("error", f"Evolve error: {e}")

    async def action_quit(self): self.exit()
    async def action_clear(self):
        self.query_one("#chat-log", RichLog).clear()
        self._chat("system", "Chat cleared")
    async def action_cancel(self):
        if self._busy: self._cancel.set(); self._chat("system", "Cancelled")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    args = p.parse_args()
    RumiTUI(demo=args.demo).run()

if __name__ == "__main__":
    main()
