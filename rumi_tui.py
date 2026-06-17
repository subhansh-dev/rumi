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
import os
import threading
import traceback
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
from textual.widgets import Input, RichLog, Rule, Static, Select
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel

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
        self._modes = {"think": False, "deep_dive": False, "domain": "", "iterate": False}

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

        # Phase 1: Core init
        st.update("\n  Initializing RUMI neural architecture...")
        await asyncio.sleep(0.3)

        # Phase 2: Actually test brain modules
        st.update("\n  Loading cognitive brain modules...")
        await asyncio.sleep(0.1)

        self._loaded_brain = []
        self._failed_brain = []
        brain_modules = [
            ("neural", "brain.neural_memory", "get_brain"),
            ("episodic", "brain.episodic_memory", "get_episodic_memory"),
            ("procedural", "brain.procedural_memory", "get_procedural_memory"),
            ("vector", "brain.vector_memory", "get_vector_memory"),
            ("active_inf", "brain.active_inference", "get_active_inference"),
            ("causal", "brain.causal_reasoner", "get_causal_reasoner"),
            ("neurosym", "brain.neurosymbolic_reasoner", "get_neurosymbolic_reasoner"),
            ("analogy", "brain.analogy_engine", "get_analogy_engine"),
            ("creative", "brain.creativity_engine", "get_creativity_engine"),
            ("intuition", "brain.intuition_engine", "get_intuition_engine"),
            ("narrative", "brain.narrative_intelligence", "get_narrative_intelligence"),
            ("self_model", "brain.self_model", "get_self_model"),
            ("aware", "brain.self_awareness", "get_self_awareness"),
            ("metacog", "brain.metacognitive_monitor", "get_metacognitive_monitor"),
            ("world", "brain.world_model", "get_world_model"),
            ("learn", "brain.learning", "get_learning_engine"),
            ("meta_learn", "brain.meta_learner", "get_meta_learner"),
            ("transfer", "brain.transfer_learning", "get_transfer_learning"),
            ("improve", "brain.self_improve_engine", "get_self_improve_engine"),
            ("discover", "brain.discovery_orchestrator", "get_discovery_orchestrator"),
            ("kg", "brain.associative_memory", "get_associative_memory"),
            ("tournament", "brain.module_competition", "get_module_competition"),
            ("xdomain", "brain.cognitive_integration", "get_cognitive_integration"),
            ("curiosity", "brain.curiosity", "get_curiosity_module"),
            ("hypothesis", "brain.hypothesis_engine", "get_hypothesis_engine"),
            ("reflexion", "brain.reflexion", "get_recursive_improver"),
            ("planner", "brain.autonomous_planner", "get_autonomous_planner"),
            ("dreaming", "brain.dreaming", "get_dreaming_system"),
            ("workspace", "brain.global_workspace", "get_global_workspace"),
            ("scientific", "brain.scientific_reasoning", "get_scientific_reasoning_loop"),
        ]

        for name, mod_path, factory_name in brain_modules:
            try:
                mod = __import__(mod_path, fromlist=[factory_name])
                factory = getattr(mod, factory_name)
                instance = factory()
                if instance is not None:
                    self._loaded_brain.append(name)
                else:
                    self._failed_brain.append(name)
            except Exception:
                self._failed_brain.append(name)
            await asyncio.sleep(0.02)  # yield to event loop

        loaded_count = len(self._loaded_brain)
        total_count = len(brain_modules)
        st.update(f"\n  Brain modules: {loaded_count}/{total_count} loaded")
        await asyncio.sleep(0.3)

        # Phase 3: LLM providers
        st.update("\n  Connecting to LLM providers...")
        await asyncio.sleep(0.1)
        try:
            from discovery.llm_client import get_status
            provider_status = get_status()
            healthy = sum(1 for v in provider_status.values() if v.get("healthy", False))
            total = len(provider_status)
            st.update(f"\n  LLM providers: {healthy}/{total} healthy")
        except Exception:
            st.update(f"\n  LLM providers: checking...")
        await asyncio.sleep(0.3)

        # Phase 4: Discovery pipeline
        st.update("\n  Discovery pipeline v2 ready")
        await asyncio.sleep(0.2)

        st.update(f"\n  All systems nominal — {loaded_count} brain modules online")
        await asyncio.sleep(0.3)

        # Show main UI
        self.query_one("#boot-overlay").display = False
        self.query_one("#main-container").display = True

        # Update BrainView with ACTUAL loaded modules
        self.query_one("#brain", BrainView).set_loaded(self._loaded_brain)

        # Welcome messages
        self._chat("system", f"[bold {CYAN}]RUMI Scientist AI v2.0[/] online")
        self._chat("system", f"{loaded_count}/{total_count} brain modules | 8 LLM providers | pipeline v2")
        if self._failed_brain:
            self._chat("system", f"[dim]Failed modules: {', '.join(self._failed_brain[:5])}{'...' if len(self._failed_brain) > 5 else ''}[/]")
        self._chat("system", "")
        self._chat("system", "[bold]Quick start:[/]")
        self._chat("system", "  [cyan]discover <topic>[/] — run full discovery pipeline")
        self._chat("system", "  [cyan]cause <question>[/] — run in cause mode (Newton Step)")
        self._chat("system", "  [cyan]/help[/] — show all commands")
        self._chat("system", "  Or just chat normally!")
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

        # Check for cause mode: "cause <question>" or "why does..."
        cause_match = re.match(r'(?:cause|reason|explain)\s+(.+)', text, re.IGNORECASE)
        if cause_match:
            cause_question = cause_match.group(1).strip()
            self.run_worker(self._run_discovery(cause_question, cause_mode=True), exclusive=True)
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
            self._chat("system", "[bold cyan]RUMI TUI Commands[/]")
            self._chat("system", "")
            self._chat("system", "[bold]Discovery:[/]")
            self._chat("system", "  [cyan]discover <topic>[/]     Run full discovery pipeline")
            self._chat("system", "  [cyan]cause <question>[/]     Run in cause mode (Newton Step)")
            self._chat("system", "  [cyan]/domain <d>[/]          Set domain (drug_discovery, physics, etc.)")
            self._chat("system", "  [cyan]/iterate[/]             Toggle iterative mode (2 passes)")
            self._chat("system", "")
            self._chat("system", "[bold]Brain Modules:[/]")
            self._chat("system", "  [cyan]/brain[/]               Show all brain module status")
            self._chat("system", "  [cyan]/curiosity[/]           Curiosity scan — top interests & queue")
            self._chat("system", "  [cyan]/evolve[/]              Self-improvement cycle")
            self._chat("system", "  [cyan]/dream[/]               Run dreaming system")
            self._chat("system", "  [cyan]/hypothesis[/]          Show hypothesis engine state")
            self._chat("system", "  [cyan]/memory[/]              Memory consolidation status")
            self._chat("system", "")
            self._chat("system", "[bold]Chat:[/]")
            self._chat("system", "  [cyan]/think[/]               Toggle think mode (show reasoning)")
            self._chat("system", "  [cyan]/dive[/]                Toggle deep dive mode")
            self._chat("system", "  [cyan]/status[/]              Show system status")
            self._chat("system", "  [cyan]/clear[/]               Clear chat")
            self._chat("system", "  [cyan]/quit[/]                Exit")
            self._chat("system", "")
            self._chat("system", "[dim]Just type anything for normal LLM chat.[/]")

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

        elif cmd == "/domain":
            if args:
                self._modes["domain"] = args.strip()
                self._chat("system", f"Domain set to: [bold]{args.strip()}[/]")
            else:
                d = self._modes.get("domain", "auto-detect")
                self._chat("system", f"Current domain: {d}")
                self._chat("system", "Available: drug_discovery, physics, space_astronomy, materials_science, chemistry, biology, general")

        elif cmd == "/iterate":
            self._modes["iterate"] = not self._modes.get("iterate", False)
            mode = "ON" if self._modes["iterate"] else "OFF"
            self._chat("system", f"Iterative mode: {mode} (2 passes with weakness analysis)")

        elif cmd == "/discover":
            if args:
                self.run_worker(self._run_discovery(args), exclusive=True)
            else:
                self._chat("system", "Usage: /discover <topic>")

        elif cmd == "/brain":
            self._chat("system", f"[bold]Brain Modules: {len(self._loaded_brain)}/{len(self._loaded_brain) + len(self._failed_brain)} loaded[/]")
            # Show loaded by group
            groups = {
                "Memory": ["neural", "episodic", "procedural", "vector", "associative"],
                "Reasoning": ["active_inf", "causal", "neurosym", "analogy", "hypothesis"],
                "Creative": ["creative", "intuition", "narrative", "dreaming"],
                "Awareness": ["self_model", "aware", "metacog", "world"],
                "Learning": ["learn", "meta_learn", "transfer", "improve"],
                "Science": ["discover", "tournament", "xdomain", "scientific", "curiosity"],
                "System": ["planner", "reflexion", "workspace"],
            }
            for group, mods in groups.items():
                loaded = [m for m in mods if m in self._loaded_brain]
                failed = [m for m in mods if m in self._failed_brain]
                status = f"[green]{len(loaded)}/{len(mods)}[/]" if not failed else f"[green]{len(loaded)}[/][red]/{len(mods)}[/]"
                self._chat("system", f"  {group:12s} {status}  {' '.join(['●' if m in self._loaded_brain else '○' for m in mods])}")

        elif cmd == "/curiosity":
            self._chat("system", "[bold]Running curiosity scan...[/]")
            self.run_worker(self._run_curiosity(), exclusive=True)

        elif cmd == "/evolve":
            self._chat("system", "[bold]Running self-improvement cycle...[/]")
            self.run_worker(self._run_evolve(), exclusive=True)

        elif cmd == "/dream":
            self.run_worker(self._run_dream(), exclusive=True)

        elif cmd == "/hypothesis":
            self.run_worker(self._run_hypothesis(), exclusive=True)

        elif cmd == "/memory":
            self.run_worker(self._run_memory(), exclusive=True)

        elif cmd == "/status":
            self._chat("system", "[bold]System Status[/]")
            self._chat("system", f"  Brain modules: {len(self._loaded_brain)} loaded, {len(self._failed_brain)} failed")
            self._chat("system", f"  Domain: {self._modes.get('domain', 'auto-detect')}")
            self._chat("system", f"  Iterative: {'ON' if self._modes.get('iterate') else 'OFF'}")
            self._chat("system", f"  Think mode: {'ON' if self._modes.get('think') else 'OFF'}")
            self._chat("system", f"  Deep dive: {'ON' if self._modes.get('deep_dive') else 'OFF'}")
            self._chat("system", f"  Conversation: {len(self._history)} messages")
            # LLM status
            try:
                from discovery.llm_client import get_status
                status = get_status()
                healthy = sum(1 for v in status.values() if v.get("healthy", False))
                self._chat("system", f"  LLM providers: {healthy}/{len(status)} healthy")
            except Exception:
                self._chat("system", f"  LLM providers: unable to check")

        elif cmd in ("/clear", "/cls"):
            self.query_one("#chat-log", RichLog).clear()
            self._chat("system", "Chat cleared")

        elif cmd in ("/quit", "/exit", "/q"):
            self.exit()

        else:
            self._chat("system", f"Unknown command: [red]{cmd}[/]. Type [cyan]/help[/] for commands.")

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

    async def _run_discovery(self, topic, cause_mode=False):
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

        domain = self._modes.get("domain", "")
        iterate = self._modes.get("iterate", False)

        mode_str = "cause" if cause_mode else "discover"
        domain_str = f" (domain: {domain})" if domain else ""
        iter_str = " [iterative]" if iterate else ""
        self._chat("assistant", f"Starting {mode_str}: [bold]{topic}[/]{domain_str}{iter_str}")
        self._history.append({"role": "assistant", "content": f"Starting {mode_str} on: {topic}"})

        # Real-time progress tracking via a shared queue
        output_queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        # Phase detection patterns for real-time updates
        phase_patterns = {
            "curious": r"Phase 0.*CURIOUS",
            "literature": r"Phase 1.*LITERATURE",
            "citation": r"Phase 1\.5.*CITATION",
            "kg": r"Phase 2.*KNOWLEDGE",
            "gaps": r"Phase 3.*GAP",
            "refine_lit": r"Phase 3\.5.*LITERATURE REFINEMENT",
            "anomalies": r"Phase 4.*ANOMALY",
            "missing_vars": r"Phase 5.*MISSING",
            "mechanisms": r"Phase 6.*MECHANISM",
            "predictions": r"Phase 7.*PREDICTION",
            "competition": r"Phase 8.*THEORY",
            "adversarial": r"Phase 8\.5.*ADVERSARIAL",
            "compute": r"Phase 9.*COMPUTATIONAL",
            "experiments": r"Phase 9\.5.*EXPERIMENT",
            "contradictions": r"Phase 10.*CONTRADICTION",
            "skeptic": r"Phase 11.*SKEPTIC",
            "scoring": r"Phase 12.*SCOR",
        }

        report = None
        captured_lines = []

        def _run():
            nonlocal report
            try:
                # Use a pipe-based approach for real-time output capture
                import subprocess
                import tempfile

                # Build command
                cmd_parts = [sys.executable, "-u", str(_root / "run_discovery.py")]
                if cause_mode:
                    cmd_parts.extend(["--cause", topic])
                else:
                    cmd_parts.append(topic)
                if domain:
                    cmd_parts.extend(["--domain", domain])
                if iterate:
                    cmd_parts.append("--iterate")
                cmd_parts.extend(["--mode", "full"])

                # Run with real-time output
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=str(_root),
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )

                for line in iter(process.stdout.readline, ''):
                    line = line.rstrip('\n')
                    if line:
                        captured_lines.append(line)
                        # Put line in queue for async pickup
                        asyncio.run_coroutine_threadsafe(
                            output_queue.put(("line", line)), loop
                        )

                process.wait()
                asyncio.run_coroutine_threadsafe(
                    output_queue.put(("done", process.returncode)), loop
                )

                # Load the report from the saved JSON
                data_dir = _root / "data"
                if data_dir.exists():
                    json_files = sorted(data_dir.glob("discovery_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
                    if json_files:
                        with open(json_files[0], "r", encoding="utf-8") as f:
                            report = json.load(f)

            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    output_queue.put(("error", str(e))), loop
                )

        # Start pipeline in thread
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        # Poll output queue and update UI in real-time
        current_phase = None
        while True:
            try:
                msg_type, msg_data = await asyncio.wait_for(output_queue.get(), timeout=1.0)

                if msg_type == "line":
                    line = msg_data.strip()
                    if not line:
                        continue

                    # Detect phase changes and update pipeline view
                    for phase_id, pattern in phase_patterns.items():
                        if re.search(pattern, line):
                            if current_phase:
                                pv.set_phase(current_phase, "done")
                            current_phase = phase_id
                            pv.set_phase(phase_id, "running")
                            dv.set_progress(pv.pct())

                    # Update agents based on phase
                    if "LITERATURE" in line:
                        av.set_agent("literature", "working", line[:40])
                    elif "KNOWLEDGE" in line:
                        av.set_agent("graph", "working", line[:40])
                    elif "GAP" in line:
                        av.set_agent("gap", "working", line[:40])
                    elif "MECHANISM" in line or "THEORY" in line:
                        av.set_agent("theory", "working", line[:40])
                    elif "SKEPTIC" in line:
                        av.set_agent("skeptic", "working", line[:40])
                    elif "EXPERIMENT" in line:
                        av.set_agent("experiment", "working", line[:40])

                    # Show important lines in chat (filter noise)
                    if any(kw in line for kw in [
                        "Phase", "Track", "Score", "Winner", "LOOP",
                        "papers", "entities", "mechanisms", "predictions",
                        "theories", "Score:", "grade", "TOTAL TIME",
                        "Report saved", "S2]", "domain", "error", "Error",
                        "Cooldown", "Pass", "Merged"
                    ]):
                        self._chat("system", line)

                elif msg_type == "done":
                    if current_phase:
                        pv.set_phase(current_phase, "done")
                    dv.set_progress(100)
                    for aid, _, _ in AGENTS:
                        av.set_agent(aid, "done")
                    break

                elif msg_type == "error":
                    self._chat("error", f"Pipeline error: {msg_data}")
                    for aid, _, _ in AGENTS:
                        av.set_agent(aid, "error")
                    break

            except asyncio.TimeoutError:
                # No output for 1s, just continue (pipeline still running)
                if not thread.is_alive():
                    break
                continue

        # Final report
        if report and "error" not in report:
            phases = report.get("phases", {})
            pv.mark_done_from_report(phases)
            dv.set_progress(pv.pct())
            dv.set_from_report(report)

            papers = phases.get("literature", {}).get("papers_found", 0)
            entities = phases.get("knowledge_graph", {}).get("entities", 0)
            gaps = len(phases.get("gap_detection", {}).get("top_gaps", []))
            anomalies = len(phases.get("anomaly_detection", {}).get("top_anomalies", []))
            score = phases.get("discovery_scoring", {}).get("discovery_score", 0)
            grade = phases.get("discovery_scoring", {}).get("grade", "N/A")
            winner = report.get("canonical_winner", {})
            winner_name = winner.get("name", "N/A")

            summary = f"Discovery complete!\n"
            summary += f"  Papers: {papers} | Entities: {entities} | Gaps: {gaps} | Anomalies: {anomalies}\n"
            summary += f"  Score: {score:.0f}/100 ({grade})\n"
            summary += f"  Winner: {winner_name[:60]}"
            self._chat("assistant", f"[bold {GREEN}]{summary}[/]")
            self._history.append({"role": "assistant", "content": summary})

            self._tokens += len(str(report)) // 4
            hd.add_tokens(len(str(report)) // 4)
        elif report and "error" in report:
            self._chat("error", f"Discovery failed: {report['error']}")
        else:
            # Try to find report from captured output
            self._chat("system", "[dim]Pipeline finished. Check data/ for report.[/]")

        hd.set_status("READY")
        self._busy = False

    # ── Curiosity scan ────────────────────────────────────────────

    async def _run_curiosity(self):
        """Run curiosity scan — show top curiosity items and queue."""
        try:
            from brain.curiosity import get_curiosity_module
            curiosity = get_curiosity_module()
            if curiosity:
                # Show stats
                stats = curiosity.get_stats()
                self._chat("tool", f"[bold]Curiosity Module[/] — {stats.get('queue_size', 0)} items in queue, {stats.get('total_surprises', 0)} surprises tracked")

                # Show top curiosity
                top = curiosity.get_top_curiosity()
                if top:
                    self._chat("system", f"  Top curiosity: {top}")

                # Show queue
                queue = curiosity.get_curiosity_queue()
                if queue:
                    self._chat("system", "  Queue:")
                    for i, item in enumerate(queue[:8]):
                        if isinstance(item, dict):
                            topic = item.get("topic", item.get("question", str(item)))
                            score = item.get("score", item.get("priority", "?"))
                            self._chat("system", f"    {i+1}. {topic[:70]} (score: {score})")
                        else:
                            self._chat("system", f"    {i+1}. {str(item)[:80]}")
                else:
                    self._chat("system", "  Curiosity queue is empty — run a discovery to populate it")

                # Show uninvestigated surprises
                surprises = curiosity.get_uninvestigated_surprises()
                if surprises:
                    self._chat("system", f"  Uninvestigated surprises: {len(surprises)}")
                    for s in surprises[:3]:
                        self._chat("system", f"    • {str(s)[:80]}")
            else:
                self._chat("error", "Curiosity module failed to initialize")
        except Exception as e:
            self._chat("error", f"Curiosity error: {e}")
            self._chat("system", f"  [dim]{traceback.format_exc()[-200:]}[/]")

    async def _run_evolve(self):
        """Run self-improvement cycle — show stats and run improvement."""
        try:
            from brain.self_improve_engine import get_self_improve_engine
            engine = get_self_improve_engine()
            if engine:
                stats = engine.get_stats()
                self._chat("tool", "[bold]Self-Improvement Engine[/]")
                for key, val in stats.items():
                    self._chat("system", f"  {key}: {val}")

                # Run improvement cycle
                self._chat("system", "  Running improvement cycle...")
                result = engine.run_improvement_cycle()
                if result:
                    self._chat("system", f"  Improvement result: {json.dumps(result, indent=2, default=str)[:500]}")
                else:
                    self._chat("system", "  No improvements needed right now")
            else:
                self._chat("error", "Self-improve engine failed to initialize")
        except Exception as e:
            self._chat("error", f"Evolve error: {e}")
            self._chat("system", f"  [dim]{traceback.format_exc()[-200:]}[/]")

    async def _run_dream(self):
        """Run dreaming system — process and consolidate memories."""
        try:
            from brain.dreaming import get_dreaming_system
            dreamer = get_dreaming_system()
            if dreamer:
                self._chat("tool", "[bold]Dreaming System[/]")
                result = dreamer.dream()
                if result:
                    self._chat("system", f"  Dream result: {json.dumps(result, indent=2, default=str)[:500]}")
                else:
                    self._chat("system", "  No dreams to process right now")
            else:
                self._chat("error", "Dreaming system failed to initialize")
        except Exception as e:
            self._chat("error", f"Dream error: {e}")

    async def _run_hypothesis(self):
        """Show hypothesis engine state."""
        try:
            from brain.hypothesis_engine import get_hypothesis_engine
            engine = get_hypothesis_engine()
            if engine:
                self._chat("tool", "[bold]Hypothesis Engine[/]")
                stats = engine.get_stats() if hasattr(engine, 'get_stats') else {}
                if stats:
                    for key, val in stats.items():
                        self._chat("system", f"  {key}: {val}")
                else:
                    # Try to list hypotheses
                    hypotheses = engine.hypotheses if hasattr(engine, 'hypotheses') else []
                    self._chat("system", f"  Active hypotheses: {len(hypotheses)}")
                    for h in hypotheses[:5]:
                        if isinstance(h, dict):
                            self._chat("system", f"    • {h.get('title', h.get('name', str(h)[:60]))}")
                        else:
                            self._chat("system", f"    • {str(h)[:60]}")
            else:
                self._chat("error", "Hypothesis engine failed to initialize")
        except Exception as e:
            self._chat("error", f"Hypothesis error: {e}")

    async def _run_memory(self):
        """Show memory consolidation status."""
        try:
            from brain.memory_consolidation import get_memory_consolidation
            consolidation = get_memory_consolidation()
            if consolidation:
                self._chat("tool", "[bold]Memory Consolidation[/]")
                stats = consolidation.get_stats() if hasattr(consolidation, 'get_stats') else {}
                if stats:
                    for key, val in stats.items():
                        self._chat("system", f"  {key}: {val}")
                else:
                    self._chat("system", f"  Status: {str(consolidation)[:200]}")
            else:
                self._chat("error", "Memory consolidation failed to initialize")
        except Exception as e:
            self._chat("error", f"Memory error: {e}")

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
