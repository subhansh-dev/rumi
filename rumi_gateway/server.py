"""WebSocket JSON-RPC server dispatching to RumiLive."""
from __future__ import annotations
import asyncio
import json
import sys
import threading
import time
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    import websockets
    from websockets.server import serve as ws_serve
except ImportError:
    print("[gateway] websockets not installed. Run: pip install websockets", file=sys.stderr)
    sys.exit(1)

from rumi_gateway.protocol import (
    JsonRpcRequest, JsonRpcResponse, JsonRpcEvent,
    send_message, log_error, set_websocket,
)


class GatewayServer:
    """WebSocket server reading JSON-RPC from clients, dispatching to RumiLive."""

    def __init__(self, host: str = "127.0.0.1", port: int = 18789):
        self._host = host
        self._port = port
        self._running = True
        self._rumi = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session_ready = False
        self._event_queue: asyncio.Queue = asyncio.Queue()

    def start(self):
        """Main entry - run the event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._run())

    async def _run(self):
        """Core loop: start WebSocket server."""
        log_error(f"Gateway server starting on ws://{self._host}:{self._port}")

        async with ws_serve(self.handler, self._host, self._port):
            log_error("Gateway ready - waiting for Ink TUI connection")
            await asyncio.Future()  # run forever

    async def handler(self, websocket):
        """Handle a single WebSocket client connection."""
        set_websocket(websocket)
        log_error(f"Client connected: {websocket.remote_address}")

        send_message(JsonRpcEvent(
            method="gateway.ready",
            params={"version": "3.1"},
        ))

        try:
            async for message in websocket:
                line = message if isinstance(message, str) else message.decode("utf-8")
                line = line.strip()
                if not line:
                    continue

                try:
                    request = JsonRpcRequest.from_json(line)
                    await self._handle_request(request)
                except json.JSONDecodeError as e:
                    log_error(f"Bad JSON: {e}")
                except Exception as e:
                    log_error(f"Error: {e}")
        except websockets.ConnectionClosed:
            log_error("Client disconnected")
        finally:
            set_websocket(None)

    async def _handle_request(self, req: JsonRpcRequest):
        """Dispatch a JSON-RPC request."""
        method = req.method
        params = req.params

        try:
            if method == "session.create":
                await self._handle_session_create(req, params)
            elif method == "session.info":
                await self._handle_session_info(req)
            elif method == "session.list":
                await self._handle_session_list(req)
            elif method == "chat.send":
                await self._handle_chat_send(req, params)
            elif method == "chat.interrupt":
                await self._handle_chat_interrupt(req)
            elif method == "slash.execute":
                await self._handle_slash(req, params)
            else:
                send_message(JsonRpcResponse(
                    id=req.id,
                    error={"code": -32601, "message": f"Unknown method: {method}"},
                ))
        except Exception as e:
            log_error(f"Handler error for {method}: {e}")
            send_message(JsonRpcResponse(
                id=req.id,
                error={"code": -32603, "message": str(e)},
            ))

    async def _handle_session_create(self, req: JsonRpcRequest, params: dict):
        """Initialize RumiLive and start the session."""
        sys.path.insert(0, str(_project_root))
        from main import RumiLive

        adapter = GatewayAdapter(self)
        self._rumi = RumiLive(adapter)

        send_message(JsonRpcResponse(
            id=req.id,
            result={
                "session_id": f"rumi-{int(time.time())}",
                "model": "gemini-2.5-flash",
                "personality": "professional",
            },
        ))

        asyncio.ensure_future(self._run_rumi())

    async def _run_rumi(self):
        """Run RumiLive's async loop in background."""
        try:
            self._session_ready = True
            await self._rumi.run()
        except Exception as e:
            log_error(f"RumiLive error: {e}")
            send_message(JsonRpcEvent(
                method="error",
                params={"code": -1, "message": str(e)},
            ))

    async def _handle_session_info(self, req: JsonRpcRequest):
        """Return current session metadata."""
        send_message(JsonRpcResponse(
            id=req.id,
            result={
                "model": "gemini-2.5-flash",
                "personality": "professional",
                "uptime": int(time.time() - self._rumi._start_time) if self._rumi else 0,
                "tokens": self._rumi.ui._total_tokens if self._rumi else 0,
                "cost": self._rumi.ui._total_cost if self._rumi else 0,
            },
        ))

    async def _handle_session_list(self, req: JsonRpcRequest):
        """Return available sessions."""
        send_message(JsonRpcResponse(
            id=req.id,
            result={
                "sessions": [
                    {
                        "id": f"rumi-{int(time.time())}",
                        "title": "Current Session",
                        "model": "gemini-2.5-flash",
                        "messages": 0,
                    }
                ],
            },
        ))

    async def _handle_chat_send(self, req: JsonRpcRequest, params: dict):
        """Send a user message to RumiLive."""
        content = params.get("content", "")
        if not content:
            send_message(JsonRpcResponse(
                id=req.id, error={"code": -32602, "message": "Missing content"},
            ))
            return

        send_message(JsonRpcResponse(id=req.id, result={"status": "queued"}))

        if self._rumi:
            self._loop.call_soon_threadsafe(
                self._rumi._on_text_command, content
            )

    async def _handle_chat_interrupt(self, req: JsonRpcRequest):
        """Interrupt the current turn."""
        if self._rumi and self._rumi.ui:
            self._rumi.ui._interrupt_requested.set()
        send_message(JsonRpcResponse(id=req.id, result={"status": "interrupted"}))

    async def _handle_slash(self, req: JsonRpcRequest, params: dict):
        """Execute a slash command."""
        command = params.get("command", "")
        args = params.get("args", "")
        full = f"/{command} {args}".strip() if args else f"/{command}"

        send_message(JsonRpcResponse(id=req.id, result={"status": "executing"}))

        if self._rumi:
            self._loop.call_soon_threadsafe(
                self._rumi.ui.handle_command, full
            )

    def emit(self, method: str, params: dict):
        """Thread-safe method to emit an event to the frontend."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                send_message, JsonRpcEvent(method=method, params=params)
            )
        else:
            send_message(JsonRpcEvent(method=method, params=params))


class GatewayAdapter:
    """Drop-in replacement for RumiUI that emits JSON-RPC events."""

    def __init__(self, server: GatewayServer):
        self._server = server
        self._running = True
        self._think_mode = False
        self._deep_dive_active = False
        self._rumi_state = "READY"
        self.status_text = "READY"
        self._start_time = time.time()
        self._personality = "professional"
        self._discovery_running = False
        self._discovery_step = ""
        self._discovery_topic = ""
        self._total_tokens = 0
        self._total_cost = 0.0
        self._last_latency = 0.0
        self._message_count = 0
        self._interrupt_requested = threading.Event()
        self._is_busy = False

        self.on_text_command = None
        self.on_discovery_command = None
        self.on_think_mode_toggle = None
        self.on_deep_dive_toggle = None
        self.on_idle_scan = None
        self._message_queue_count = 0

        self._timeline = _StubTimeline()
        self._pipeline = _StubPipeline()
        self._tool_calls = _StubToolCalls()
        self._graph_metrics = _StubGraphMetrics()
        self._activity_feed = _StubActivityFeed()

    def handle_command(self, cmd: str):
        """Dispatch slash commands."""
        cmd_lower = cmd.lower().strip()

        if cmd_lower == "/help":
            self._server.emit("system.message", {
                "content": "Commands: /help, /clear, /think, /dive, /status, "
                           "/stats, /timeline, /discover <topic>, /grounded <topic>, /quit",
            })
        elif cmd_lower == "/think":
            self._think_mode = not self._think_mode
            state = "ON" if self._think_mode else "OFF"
            self._server.emit("state.update", {
                "state": f"THINK {state}", "think_mode": self._think_mode,
            })
        elif cmd_lower == "/dive":
            self._deep_dive_active = not self._deep_dive_active
            state = "ON" if self._deep_dive_active else "OFF"
            self._server.emit("state.update", {
                "state": f"DIVE {state}", "deep_dive": self._deep_dive_active,
            })
        elif cmd_lower.startswith("/discover "):
            topic = cmd_lower[len("/discover "):].strip()
            if self.on_discovery_command:
                threading.Thread(
                    target=self.on_discovery_command,
                    args=("discover", topic), daemon=True,
                ).start()
        elif cmd_lower.startswith("/grounded "):
            topic = cmd_lower[len("/grounded "):].strip()
            if self.on_discovery_command:
                threading.Thread(
                    target=self.on_discovery_command,
                    args=("grounded", topic), daemon=True,
                ).start()
        elif cmd_lower == "/status":
            self._server.emit("status.info", {
                "state": self._rumi_state,
                "tokens": self._total_tokens,
                "cost": self._total_cost,
            })
        elif cmd_lower == "/quit":
            self._server.emit("session.ending", {})
        else:
            self._server.emit("system.message", {
                "content": f"Unknown command: {cmd_lower}",
            })

    def write_log(self, text: str):
        """Intercept output and emit as JSON-RPC events."""
        import re
        tl = text.lower().strip()

        if any(skip in tl for skip in ["[rumi]", "[episodic]", "[selfawareness]",
                                        "[coordinator]", "[dreaming]", "[vectormemory]",
                                        "[telegram]", "non-data parts", "[focus]"]):
            return

        if tl.startswith("you:"):
            content = text[4:].strip()
            self._server.emit("user.message", {"content": content})
        elif tl.startswith("rumi:") or tl.startswith("ai:"):
            prefix_len = 5 if tl.startswith("rumi:") else 3
            content = text[prefix_len:].strip()
            content = re.sub(r'\*\*Thinking(?:\s*\(.*?\))?\*\*\s*', '', content).strip()
            content = re.sub(r'\*\*Reasoning\*\*\s*', '', content).strip()
            if content:
                self._server.emit("assistant.message", {"content": content})
        elif tl.startswith("sys:"):
            content = text[4:].strip()
            self._server.emit("system.message", {"content": content})
        elif tl.startswith("err:") or tl.startswith("error:"):
            err_msg = text[4:].strip()
            self._server.emit("error", {"message": err_msg})
        elif tl.startswith("sec:"):
            sec_msg = text[4:].strip()
            self._server.emit("system.message", {"content": f"⚠ {sec_msg}"})
        else:
            clean = re.sub(r'\[/?\w+(?: \w+=[^\]]+)*\]', '', text).strip()
            if clean:
                self._server.emit("assistant.message", {"content": clean})

    def set_state(self, state: str):
        self._rumi_state = state
        self.status_text = state
        self._is_busy = state in ("THINKING", "PROCESSING", "SPEAKING")
        self._server.emit("state.update", {"state": state})

    def set_discovery_step(self, step: str):
        self._discovery_step = step
        pct = self._pipeline.get_progress_pct()
        self._server.emit("discovery.phase", {
            "phase": step, "progress": pct, "topic": self._discovery_topic,
        })

    def set_discovery_done(self):
        self._discovery_running = False
        self._discovery_step = ""
        self._server.emit("discovery.done", {
            "papers": self._graph_metrics.papers,
            "entities": self._graph_metrics.entities,
            "edges": self._graph_metrics.edges,
        })

    def show_thinking(self, message: str = ""):
        self._server.emit("thinking.start", {"verb": message or "thinking"})

    def show_done(self, message: str = ""):
        self._server.emit("thinking.done", {})

    def show_tool_call(self, name: str, query: str = ""):
        self._server.emit("tool.start", {"name": name, "query": query})

    def complete_tool_call(self, name: str, result: str = ""):
        self._server.emit("tool.complete", {"name": name, "result": result})

    def update_tokens(self, tokens: int, cost: float = 0.0, latency: float = 0.0):
        self._total_tokens += tokens
        self._total_cost += cost
        if latency > 0:
            self._last_latency = latency
        self._server.emit("metrics.update", {
            "tokens": self._total_tokens,
            "cost": self._total_cost,
            "latency": latency,
        })

    def update_graph_metrics(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self._graph_metrics, k):
                setattr(self._graph_metrics, k, v)
        snap = self._graph_metrics.snapshot()
        self._server.emit("graph.update", snap)

    def show_toast(self, message: str, duration: float = 2.5):
        self._server.emit("system.message", {"content": message})

    def wait_for_api_key(self):
        pass

    def interrupt_requested(self):
        return self._interrupt_requested.is_set()

    def clear_interrupt(self):
        self._interrupt_requested.clear()

    def feed_amplitude(self, amplitude: float):
        pass


class _StubTimeline:
    def add(self, *a, **kw): pass
    def get_events(self, last_n=20): return []
    def clear(self): pass
    def count(self): return 0

class _StubPipeline:
    PHASES = []
    def reset(self): pass
    def start_phase(self, *a): pass
    def complete_phase(self, *a): pass
    def error_phase(self, *a): pass
    def all_done(self): return True
    def get_display(self): return []
    def get_progress_pct(self): return 0

class _StubToolCalls:
    def start(self, *a, **kw): pass
    def complete(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def get_recent(self, n=10): return []

class _StubGraphMetrics:
    def __init__(self):
        self.nodes = 0; self.edges = 0; self.clusters = 0
        self.contradictions = 0; self.novelty_candidates = 0
        self.papers = 0; self.entities = 0; self.relationships = 0
    def update(self, **kw):
        for k, v in kw.items():
            if hasattr(self, k): setattr(self, k, v)
    def snapshot(self):
        return {k: getattr(self, k) for k in [
            "nodes","edges","clusters","contradictions",
            "novelty_candidates","papers","entities","relationships",
        ]}

class _StubActivityFeed:
    def add(self, *a, **kw): pass
    def get_recent(self, n=10): return []
    def clear(self): pass
