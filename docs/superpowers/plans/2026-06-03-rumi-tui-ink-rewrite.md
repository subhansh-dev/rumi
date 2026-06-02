# RUMI TUI Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite RUMI's terminal UI using React Ink (TypeScript) with a Python JSON-RPC gateway, matching Hermes Agent's TUI quality while staying terminal-native.

**Architecture:** Client-server over stdin/stdout. A React Ink frontend (`ui-tui/`) renders the UI. A Python gateway (`rumi_gateway/`) wraps the existing `RumiLive` logic and communicates via JSON-RPC 2.0. The existing `ui.py` stays as classic CLI fallback.

**Tech Stack:** TypeScript, React Ink 4, Python 3.11+, asyncio, existing RUMI brain modules

---

## File Structure

```
rumi/
├── ui-tui/                          # NEW — React Ink TUI
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── entry.tsx                # Client entrypoint
│   │   ├── app.tsx                  # Root component
│   │   ├── theme.ts                 # Color constants
│   │   ├── gateway/
│   │   │   ├── client.ts            # JSON-RPC client (stdin/stdout)
│   │   │   └── types.ts             # Protocol message types
│   │   ├── components/
│   │   │   ├── banner.tsx           # Collapsible ▸/▾ header
│   │   │   ├── transcript.tsx       # Scrollable message history
│   │   │   ├── streaming.tsx        # Live assistant response
│   │   │   ├── toolTrail.tsx        # ├─ ✓ tool tree
│   │   │   ├── statusBar.tsx        # Bottom status bar
│   │   │   ├── inputArea.tsx        # Multiline input
│   │   │   ├── commandPalette.tsx   # Ctrl+K modal
│   │   │   ├── sessionSwitcher.tsx  # Ctrl+X modal
│   │   │   ├── discoveryPanel.tsx   # Pipeline progress
│   │   │   └── completionList.tsx   # Slash autocomplete
│   │   └── hooks/
│   │       ├── useGateway.ts        # Gateway connection hook
│   │       └── useTranscript.ts     # Transcript state hook
│   └── dist/
│       └── entry.js                 # Built bundle
│
├── rumi_gateway/                    # NEW — Python JSON-RPC server
│   ├── __init__.py
│   ├── server.py                    # JSON-RPC over stdin/stdout
│   ├── adapter.py                   # GatewayUI — adapts RumiLive to JSON-RPC
│   └── protocol.py                  # Message types
│
├── ui.py                            # UNCHANGED — classic CLI
├── main.py                          # MODIFIED — add --tui launch
└── rumi_launcher.py                 # MODIFIED — pass --tui flag
```

---

## Task 1: Gateway Protocol Types (Python)

**Files:**
- Create: `rumi_gateway/__init__.py`
- Create: `rumi_gateway/protocol.py`

- [ ] **Step 1: Create package init**

```python
# rumi_gateway/__init__.py
"""RUMI JSON-RPC Gateway — bridges Ink TUI to RumiLive."""
```

- [ ] **Step 2: Write protocol message types**

```python
# rumi_gateway/protocol.py
"""JSON-RPC 2.0 message types for RUMI gateway."""
from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class JsonRpcRequest:
    jsonrpc: str = "2.0"
    id: int | str = 0
    method: str = ""
    params: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> "JsonRpcRequest":
        obj = json.loads(data)
        return cls(
            jsonrpc=obj.get("jsonrpc", "2.0"),
            id=obj.get("id", 0),
            method=obj.get("method", ""),
            params=obj.get("params", {}),
        )


@dataclass
class JsonRpcResponse:
    jsonrpc: str = "2.0"
    id: int | str = 0
    result: Any = None
    error: Optional[dict] = None

    def to_json(self) -> str:
        d = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error:
            d["error"] = self.error
        else:
            d["result"] = self.result
        return json.dumps(d, ensure_ascii=False)


@dataclass
class JsonRpcEvent:
    jsonrpc: str = "2.0"
    method: str = ""
    params: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {"jsonrpc": self.jsonrpc, "method": self.method, "params": self.params},
            ensure_ascii=False,
        )


def send_message(msg: JsonRpcResponse | JsonRpcEvent) -> None:
    """Write a JSON-RPC message to stdout. Flush immediately."""
    sys.stdout.write(msg.to_json() + "\n")
    sys.stdout.flush()


def log_error(message: str) -> None:
    """Write a log line to stderr (kept out of protocol stream)."""
    sys.stderr.write(f"[gateway] {message}\n")
    sys.stderr.flush()
```

- [ ] **Step 3: Verify imports work**

Run: `cd C:\Users\Admin\Desktop\rumi && python -c "from rumi_gateway.protocol import JsonRpcRequest, JsonRpcEvent, send_message; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add rumi_gateway/
git commit -m "feat(gateway): add JSON-RPC protocol types"
```

---

## Task 2: Gateway Server (Python)

**Files:**
- Create: `rumi_gateway/server.py`

- [ ] **Step 1: Write the JSON-RPC server**

```python
# rumi_gateway/server.py
"""JSON-RPC server reading from stdin, dispatching to RumiLive."""
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

from rumi_gateway.protocol import (
    JsonRpcRequest, JsonRpcResponse, JsonRpcEvent,
    send_message, log_error,
)


class GatewayServer:
    """Reads JSON-RPC from stdin, manages session, writes events to stdout."""

    def __init__(self):
        self._running = True
        self._rumi = None  # RumiLive instance, set after init
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session_ready = False
        self._pending_responses: dict[int | str, asyncio.Future] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()

    def start(self):
        """Main entry — run the event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Start stdin reader
        self._loop.run_until_complete(self._run())

    async def _run(self):
        """Core loop: read stdin, process, emit events."""
        log_error("Gateway server starting")

        # Signal ready
        send_message(JsonRpcEvent(
            method="gateway.ready",
            params={"version": "3.0"},
        ))

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await self._loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while self._running:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=0.1)
                if not line:
                    break
                line = line.decode("utf-8").strip()
                if not line:
                    continue

                request = JsonRpcRequest.from_json(line)
                await self._handle_request(request)

            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError as e:
                log_error(f"Bad JSON: {e}")
            except Exception as e:
                log_error(f"Error: {e}")

    async def _handle_request(self, req: JsonRpcRequest):
        """Dispatch a JSON-RPC request."""
        method = req.method
        params = req.params

        try:
            if method == "session.create":
                await self._handle_session_create(req, params)
            elif method == "session.info":
                await self._handle_session_info(req)
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
        from ui import RumiUI

        ui = RumiUI.__new__(RumiUI)
        # Minimal init — skip boot sequence, set state
        ui._running = True
        ui._think_mode = False
        ui._deep_dive_active = False
        ui._rumi_state = "READY"
        ui._discovery_running = False
        ui._discovery_step = ""
        ui._total_tokens = 0
        ui._total_cost = 0.0
        ui._start_time = time.time()
        ui._message_count = 0

        # Import and create RumiLive
        # We need to defer this import to avoid circular imports
        sys.path.insert(0, str(_project_root))
        from main import RumiLive

        # Create a gateway adapter UI that sends events instead of rendering
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

        # Start the RumiLive run loop in background
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
            # Post to RumiLive's text handler
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

        if self._rumi and self._rumi.ui:
            self._loop.call_soon_threadsafe(
                self._rumi.ui._handle_command, full
            )

    def emit(self, method: str, params: dict):
        """Thread-safe method to emit an event to the frontend."""
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

        # Callbacks — set by RumiLive
        self.on_text_command = None
        self.on_discovery_command = None
        self.on_think_mode_toggle = None
        self.on_deep_dive_toggle = None
        self.on_idle_scan = None
        self._message_queue_count = 0

        # Stub subsystems
        self._timeline = _StubTimeline()
        self._pipeline = _StubPipeline()
        self._tool_calls = _StubToolCalls()
        self._graph_metrics = _StubGraphMetrics()
        self._activity_feed = _StubActivityFeed()

    def write_log(self, text: str):
        """Intercept output and emit as JSON-RPC events."""
        import re
        tl = text.lower().strip()

        # Skip internal noise
        if any(skip in tl for skip in ["[rumi]", "[episodic]", "[selfawareness]",
                                        "[coordinator]", "[dreaming]", "[vectormemory]",
                                        "[telegram]", "non-data parts", "[focus]"]):
            return

        # User input echo
        if tl.startswith("you:"):
            content = text[4:].strip()
            self._server.emit("user.message", {"content": content})

        # RUMI response
        elif tl.startswith("rumi:") or tl.startswith("ai:"):
            prefix_len = 5 if tl.startswith("rumi:") else 3
            content = text[prefix_len:].strip()
            content = re.sub(r'\*\*Thinking(?:\s*\(.*?\))?\*\*\s*', '', content).strip()
            content = re.sub(r'\*\*Reasoning\*\*\s*', '', content).strip()
            if content:
                self._server.emit("assistant.message", {"content": content})

        # System message
        elif tl.startswith("sys:"):
            content = text[4:].strip()
            self._server.emit("system.message", {"content": content})

        # Error
        elif tl.startswith("err:") or tl.startswith("error:"):
            err_msg = text[4:].strip()
            self._server.emit("error", {"message": err_msg})

        # Security
        elif tl.startswith("sec:"):
            sec_msg = text[4:].strip()
            self._server.emit("system.message", {"content": f"⚠ {sec_msg}"})

        # Discovery/rich output
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
        pass  # Gateway handles this differently

    def interrupt_requested(self):
        return self._interrupt_requested.is_set()

    def clear_interrupt(self):
        self._interrupt_requested.clear()

    def feed_amplitude(self, amplitude: float):
        pass


# ── Stub classes for subsystems the adapter doesn't need ──────────────

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
```

- [ ] **Step 2: Verify the module loads**

Run: `cd C:\Users\Admin\Desktop\rumi && python -c "from rumi_gateway.server import GatewayServer, GatewayAdapter; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add rumi_gateway/server.py
git commit -m "feat(gateway): JSON-RPC server with GatewayAdapter for RumiLive"
```

---

## Task 3: Ink Project Scaffold (TypeScript)

**Files:**
- Create: `ui-tui/package.json`
- Create: `ui-tui/tsconfig.json`
- Create: `ui-tui/src/entry.tsx`
- Create: `ui-tui/src/theme.ts`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "rumi-tui",
  "version": "3.0.0",
  "description": "RUMI Terminal UI — React Ink, Hermes Agent style",
  "main": "dist/entry.js",
  "scripts": {
    "build": "tsc && node esbuild.config.mjs",
    "dev": "tsc --watch",
    "start": "node dist/entry.js"
  },
  "dependencies": {
    "ink": "^4.1.0",
    "ink-text-input": "^5.0.1",
    "ink-spinner": "^4.0.3",
    "react": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.4.0",
    "esbuild": "^0.20.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 3: Create theme.ts with Hermes color palette**

```typescript
// ui-tui/src/theme.ts
// Hermes Agent color palette — warm dark theme

export const theme = {
  bg: {
    deep: '#0d1117',
    secondary: '#161b22',
    panel: '#1c2128',
    element: '#21262d',
    hover: '#30363d',
    input: '#0d1117',
  },
  txt: {
    bright: '#f0f6fc',
    primary: '#c9d1d9',
    secondary: '#8b949e',
    muted: '#484f58',
    dim: '#30363d',
  },
  accent: {
    cyan: '#39d353',
    blue: '#58a6ff',
    green: '#39d353',
    amber: '#d29922',
    red: '#f85149',
    purple: '#bc8cff',
    teal: '#39d353',
    pink: '#f778ba',
  },
  border: {
    subtle: '#21262d',
    normal: '#30363d',
    active: '#58a6ff',
  },
} as const;

export type Theme = typeof theme;
```

- [ ] **Step 4: Create entry.tsx (minimal, just renders "RUMI TUI")**

```typescript
// ui-tui/src/entry.tsx
import React from 'react';
import { render, Text, Box } from 'ink';

const App: React.FC = () => {
  return (
    <Box flexDirection="column" padding={1}>
      <Text color={theme.accent.blue} bold>
        RUMI TUI v3.0
      </Text>
      <Text color={theme.txt.secondary}>
        Hermes Agent Style — Coming soon
      </Text>
    </Box>
  );
};

import { theme } from './theme';

render(<App />);
```

- [ ] **Step 5: Install dependencies and verify build**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npm install && npx tsc --noEmit`
Expected: Compiles with no errors (may have warnings, that's fine)

- [ ] **Step 6: Commit**

```bash
git add ui-tui/
git commit -m "feat(ui-tui): scaffold Ink project with theme and entry point"
```

---

## Task 4: Gateway Client (TypeScript)

**Files:**
- Create: `ui-tui/src/gateway/types.ts`
- Create: `ui-tui/src/gateway/client.ts`

- [ ] **Step 1: Write protocol types**

```typescript
// ui-tui/src/gateway/types.ts

export interface JsonRpcRequest {
  jsonrpc: '2.0';
  id: number | string;
  method: string;
  params: Record<string, unknown>;
}

export interface JsonRpcResponse {
  jsonrpc: '2.0';
  id: number | string;
  result?: unknown;
  error?: { code: number; message: string };
}

export interface JsonRpcEvent {
  jsonrpc: '2.0';
  method: string;
  params: Record<string, unknown>;
}

// Event payloads from gateway
export interface GatewayReadyEvent {
  version: string;
}

export interface SessionInfo {
  session_id: string;
  model: string;
  personality: string;
}

export interface AssistantMessageEvent {
  content: string;
}

export interface ToolStartEvent {
  name: string;
  query: string;
}

export interface ToolCompleteEvent {
  name: string;
  result: string;
  elapsed?: number;
}

export interface DiscoveryPhaseEvent {
  phase: string;
  progress: number;
  topic: string;
}

export interface MetricsUpdateEvent {
  tokens: number;
  cost: number;
  latency: number;
}

export interface GraphUpdateEvent {
  nodes: number;
  edges: number;
  clusters: number;
  papers: number;
  entities: number;
  relationships: number;
}

export interface StateUpdateEvent {
  state: string;
}

export type GatewayEventType =
  | 'gateway.ready'
  | 'assistant.message'
  | 'assistant.stream'
  | 'assistant.done'
  | 'user.message'
  | 'system.message'
  | 'tool.start'
  | 'tool.complete'
  | 'tool.error'
  | 'discovery.phase'
  | 'discovery.done'
  | 'metrics.update'
  | 'graph.update'
  | 'state.update'
  | 'thinking.start'
  | 'thinking.done'
  | 'error';
```

- [ ] **Step 2: Write the gateway client**

```typescript
// ui-tui/src/gateway/client.ts
import * as readline from 'readline';
import { JsonRpcRequest, JsonRpcResponse, JsonRpcEvent, GatewayEventType } from './types';

type EventHandler = (method: string, params: Record<string, unknown>) => void;

let _nextId = 1;

export class GatewayClient {
  private pending = new Map<number | string, {
    resolve: (result: unknown) => void;
    reject: (error: Error) => void;
  }>();
  private handlers: EventHandler[] = [];
  private rl: readline.Interface;

  constructor() {
    // Read from stdin line by line
    this.rl = readline.createInterface({
      input: process.stdin,
      terminal: false,
    });

    this.rl.on('line', (line: string) => {
      this.handleLine(line.trim());
    });

    this.rl.on('close', () => {
      this.emit('gateway.close', {});
    });
  }

  private handleLine(line: string) {
    if (!line) return;

    let msg: JsonRpcResponse | JsonRpcEvent;
    try {
      msg = JSON.parse(line);
    } catch {
      return; // Protocol noise — ignore
    }

    // Response (has id) or Event (has method, no id)
    if ('id' in msg && msg.id !== undefined) {
      const resp = msg as JsonRpcResponse;
      const pending = this.pending.get(resp.id);
      if (pending) {
        this.pending.delete(resp.id);
        if (resp.error) {
          pending.reject(new Error(resp.error.message));
        } else {
          pending.resolve(resp.result);
        }
      }
    } else if ('method' in msg) {
      const evt = msg as JsonRpcEvent;
      this.emit(evt.method, evt.params);
    }
  }

  private emit(method: string, params: Record<string, unknown>) {
    for (const handler of this.handlers) {
      handler(method, params);
    }
  }

  onEvent(handler: EventHandler) {
    this.handlers.push(handler);
  }

  async send(method: string, params: Record<string, unknown> = {}): Promise<unknown> {
    const id = _nextId++;
    const request: JsonRpcRequest = {
      jsonrpc: '2.0',
      id,
      method,
      params,
    };

    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      process.stdout.write(JSON.stringify(request) + '\n');
    });
  }

  emitLocal(method: string, params: Record<string, unknown>) {
    // Emit an event locally (for UI-only events like Ctrl+K)
    this.emit(method, params);
  }

  destroy() {
    this.rl.close();
  }
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add ui-tui/src/gateway/
git commit -m "feat(ui-tui): JSON-RPC gateway client with event handling"
```

---

## Task 5: Transcript Component

**Files:**
- Create: `ui-tui/src/hooks/useTranscript.ts`
- Create: `ui-tui/src/components/transcript.tsx`
- Create: `ui-tui/src/components/streaming.tsx`

- [ ] **Step 1: Write the transcript hook**

```typescript
// ui-tui/src/hooks/useTranscript.ts
import { useState, useCallback } from 'react';

export interface TranscriptEntry {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'error';
  content: string;
  timestamp: number;
}

export function useTranscript() {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [streamingContent, setStreamingContent] = useState('');

  const addUserMessage = useCallback((content: string) => {
    setEntries(prev => [...prev, {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: Date.now(),
    }]);
  }, []);

  const addAssistantMessage = useCallback((content: string) => {
    setStreamingContent('');
    setEntries(prev => [...prev, {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content,
      timestamp: Date.now(),
    }]);
  }, []);

  const appendStream = useCallback((delta: string) => {
    setStreamingContent(prev => prev + delta);
  }, []);

  const addSystemMessage = useCallback((content: string) => {
    setEntries(prev => [...prev, {
      id: `system-${Date.now()}`,
      role: 'system',
      content,
      timestamp: Date.now(),
    }]);
  }, []);

  const addErrorMessage = useCallback((content: string) => {
    setEntries(prev => [...prev, {
      id: `error-${Date.now()}`,
      role: 'error',
      content,
      timestamp: Date.now(),
    }]);
  }, []);

  const clear = useCallback(() => {
    setEntries([]);
    setStreamingContent('');
  }, []);

  return {
    entries,
    streamingContent,
    addUserMessage,
    addAssistantMessage,
    appendStream,
    addSystemMessage,
    addErrorMessage,
    clear,
  };
}
```

- [ ] **Step 2: Write the transcript component**

```typescript
// ui-tui/src/components/transcript.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';
import { TranscriptEntry } from '../hooks/useTranscript';

interface TranscriptProps {
  entries: TranscriptEntry[];
  maxHeight?: number;
}

export const Transcript: React.FC<TranscriptProps> = ({ entries, maxHeight = 50 }) => {
  // Show last N entries that fit
  const visible = entries.slice(-maxHeight);

  return (
    <Box flexDirection="column" flexShrink={1}>
      {visible.map(entry => (
        <TranscriptLine key={entry.id} entry={entry} />
      ))}
    </Box>
  );
};

const TranscriptLine: React.FC<{ entry: TranscriptEntry }> = ({ entry }) => {
  switch (entry.role) {
    case 'user':
      return (
        <Box marginBottom={1}>
          <Text color={theme.accent.blue} bold>{'> '}</Text>
          <Text color={theme.txt.primary}>{entry.content}</Text>
        </Box>
      );

    case 'assistant':
      return (
        <Box flexDirection="column" marginBottom={1} paddingLeft={1}>
          <Text color={theme.accent.blue}>
            {'╭─ RUMI ' + '─'.repeat(Math.max(0, 50)) + '╮'}
          </Text>
          <Text color={theme.txt.primary} wrap="wrap">
            {'│ '}{entry.content}
          </Text>
          <Text color={theme.accent.blue}>
            {'╰' + '─'.repeat(52) + '╯'}
          </Text>
        </Box>
      );

    case 'system':
      return (
        <Box>
          <Text color={theme.txt.muted} italic>{'  '}{entry.content}</Text>
        </Box>
      );

    case 'error':
      return (
        <Box>
          <Text color={theme.accent.red}>{'  ✗ '}{entry.content}</Text>
        </Box>
      );

    default:
      return null;
  }
};
```

- [ ] **Step 3: Write the streaming component**

```typescript
// ui-tui/src/components/streaming.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface StreamingProps {
  content: string;
  isActive: boolean;
}

export const Streaming: React.FC<StreamingProps> = ({ content, isActive }) => {
  if (!isActive && !content) return null;

  return (
    <Box flexDirection="column" marginBottom={1} paddingLeft={1}>
      <Text color={theme.accent.blue}>
        {'╭─ RUMI ' + '─'.repeat(50) + '╮'}
      </Text>
      <Text color={theme.txt.primary} wrap="wrap">
        {'│ '}{content}
        {isActive && <Text color={theme.accent.green}>{'▍'}</Text>}
      </Text>
      {!isActive && content && (
        <Text color={theme.accent.blue}>
          {'╰' + '─'.repeat(52) + '╯'}
        </Text>
      )}
    </Box>
  );
};
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add ui-tui/src/hooks/useTranscript.ts ui-tui/src/components/transcript.tsx ui-tui/src/components/streaming.tsx
git commit -m "feat(ui-tui): transcript and streaming components"
```

---

## Task 6: Tool Trail Component

**Files:**
- Create: `ui-tui/src/components/toolTrail.tsx`

- [ ] **Step 1: Write the tool trail component**

```typescript
// ui-tui/src/components/toolTrail.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

export interface ToolCall {
  id: string;
  name: string;
  query: string;
  status: 'running' | 'done' | 'error';
  elapsed?: number;
  isLast: boolean;
}

interface ToolTrailProps {
  tools: ToolCall[];
}

export const ToolTrail: React.FC<ToolTrailProps> = ({ tools }) => {
  if (tools.length === 0) return null;

  return (
    <Box flexDirection="column" paddingLeft={1}>
      {tools.map(tool => (
        <ToolLine key={tool.id} tool={tool} />
      ))}
    </Box>
  );
};

const ToolLine: React.FC<{ tool: ToolCall }> = ({ tool }) => {
  const prefix = tool.isLast ? '└─' : '├─';
  const icon = tool.status === 'done' ? '✓' : tool.status === 'error' ? '✗' : '○';
  const iconColor = tool.status === 'done'
    ? theme.accent.green
    : tool.status === 'error'
    ? theme.accent.red
    : theme.accent.amber;

  const elapsedStr = tool.elapsed != null ? ` (${tool.elapsed.toFixed(1)}s)` : '';

  return (
    <Box>
      <Text color={theme.txt.muted}>{prefix} </Text>
      <Text color={iconColor} bold>{icon} </Text>
      <Text color={theme.accent.blue} bold>{tool.name}</Text>
      {tool.query && (
        <Text color={theme.txt.secondary}> {tool.query.slice(0, 40)}</Text>
      )}
      <Text color={theme.txt.muted}>{elapsedStr}</Text>
    </Box>
  );
};
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add ui-tui/src/components/toolTrail.tsx
git commit -m "feat(ui-tui): tool trail component with tree display"
```

---

## Task 7: Status Bar Component

**Files:**
- Create: `ui-tui/src/components/statusBar.tsx`

- [ ] **Step 1: Write the status bar**

```typescript
// ui-tui/src/components/statusBar.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface StatusBarProps {
  state: string;
  model: string;
  tokens: number;
  cost: number;
  uptime: number;
  thinkMode: boolean;
  diveMode: boolean;
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

export const StatusBar: React.FC<StatusBarProps> = ({
  state, model, tokens, cost, uptime, thinkMode, diveMode,
}) => {
  const stateColor = state === 'READY' || state === 'IDLE'
    ? theme.accent.green
    : state === 'THINKING' || state === 'PROCESSING'
    ? theme.accent.amber
    : theme.txt.secondary;

  const stateLabel = state === 'THINKING' ? 'thinking…'
    : state === 'PROCESSING' ? 'running…'
    : state === 'SPEAKING' ? 'speaking…'
    : 'ready';

  return (
    <Box
      flexDirection="row"
      paddingX={1}
      borderTop={true}
      borderColor={theme.border.normal}
    >
      <Text color={stateColor} bold>{'● '}{stateLabel}</Text>
      <Text color={theme.border.normal}>{' │ '}</Text>
      <Text color={theme.accent.blue}>{model}</Text>
      <Text color={theme.border.normal}>{' │ '}</Text>
      <Text color={theme.txt.secondary}>{formatTokens(tokens)} tok</Text>
      <Text color={theme.border.normal}>{' │ '}</Text>
      <Text color={theme.txt.secondary}>{formatUptime(uptime)}</Text>
      {cost > 0 && (
        <>
          <Text color={theme.border.normal}>{' │ '}</Text>
          <Text color={theme.accent.green}>{'$'}{cost.toFixed(4)}</Text>
        </>
      )}
      {thinkMode && (
        <>
          <Text color={theme.border.normal}>{' │ '}</Text>
          <Text color={theme.accent.purple}>{'think'}</Text>
        </>
      )}
      {diveMode && (
        <>
          <Text color={theme.border.normal}>{' │ '}</Text>
          <Text color={theme.accent.cyan}>{'dive'}</Text>
        </>
      )}
    </Box>
  );
};
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add ui-tui/src/components/statusBar.tsx
git commit -m "feat(ui-tui): status bar with model, tokens, uptime, mode badges"
```

---

## Task 8: Banner Component (Collapsible)

**Files:**
- Create: `ui-tui/src/components/banner.tsx`

- [ ] **Step 1: Write the banner component**

```typescript
// ui-tui/src/components/banner.tsx
import React, { useState } from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface BannerSection {
  title: string;
  content: string[];
  defaultOpen?: boolean;
}

interface BannerProps {
  version: string;
  model: string;
  domains: number;
  modules: number;
  sections?: BannerSection[];
}

export const Banner: React.FC<BannerProps> = ({
  version, model, domains, modules, sections = [],
}) => {
  const [openSections, setOpenSections] = useState<Set<number>>(() => {
    const open = new Set<number>();
    sections.forEach((s, i) => { if (s.defaultOpen) open.add(i); });
    return open;
  });

  const toggle = (idx: number) => {
    setOpenSections(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <Box flexDirection="column" paddingX={1} paddingBottom={1}>
      <Box>
        <Text color={theme.accent.blue} bold>{'RUMI'}</Text>
        <Text color={theme.txt.muted}>{` v${version} · `}</Text>
        <Text color={theme.txt.secondary}>{model}</Text>
        <Text color={theme.txt.muted}>{` · ${domains} domains · ${modules} modules`}</Text>
      </Box>

      {sections.map((section, idx) => {
        const isOpen = openSections.has(idx);
        const chevron = isOpen ? '▾' : '▸';
        return (
          <Box key={idx} paddingLeft={1}>
            <Text
              color={theme.txt.muted}
              onPress={() => toggle(idx)}
            >
              {chevron}{' '}{section.title}
            </Text>
            {isOpen && section.content.map((line, li) => (
              <Text key={li} color={theme.txt.secondary} paddingLeft={3}>
                {line}
              </Text>
            ))}
          </Box>
        );
      })}
    </Box>
  );
};
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add ui-tui/src/components/banner.tsx
git commit -m "feat(ui-tui): collapsible banner with ▸/▾ chevrons"
```

---

## Task 9: Input Area with Slash Autocomplete

**Files:**
- Create: `ui-tui/src/components/inputArea.tsx`
- Create: `ui-tui/src/components/completionList.tsx`

- [ ] **Step 1: Write the completion list**

```typescript
// ui-tui/src/components/completionList.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface CompletionItem {
  label: string;
  description: string;
}

interface CompletionListProps {
  items: CompletionItem[];
  selectedIndex: number;
  visible: boolean;
}

const SLASH_COMMANDS: CompletionItem[] = [
  { label: '/discover', description: 'Full discovery pipeline' },
  { label: '/search', description: 'Search papers' },
  { label: '/hypothesize', description: 'Generate hypotheses' },
  { label: '/experiment', description: 'Design experiment' },
  { label: '/review', description: 'Peer review' },
  { label: '/graph', description: 'Knowledge graph stats' },
  { label: '/dashboard', description: 'Discovery dashboard' },
  { label: '/domains', description: 'List 17 domains' },
  { label: '/status', description: 'System status' },
  { label: '/stats', description: 'Session stats' },
  { label: '/timeline', description: 'Session timeline' },
  { label: '/think', description: 'Toggle think mode' },
  { label: '/dive', description: 'Toggle deep dive' },
  { label: '/personality', description: 'Switch personality' },
  { label: '/clear', description: 'Clear screen' },
  { label: '/help', description: 'Show help' },
  { label: '/exit', description: 'Shut down' },
];

export { SLASH_COMMANDS };

export const CompletionList: React.FC<CompletionListProps> = ({
  items, selectedIndex, visible,
}) => {
  if (!visible || items.length === 0) return null;

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={theme.border.normal} paddingX={1}>
      {items.map((item, idx) => (
        <Box key={item.label}>
          <Text
            color={idx === selectedIndex ? theme.accent.blue : theme.txt.secondary}
            bold={idx === selectedIndex}
          >
            {item.label}
          </Text>
          <Text color={theme.txt.muted}>{'  '}{item.description}</Text>
        </Box>
      ))}
    </Box>
  );
};
```

- [ ] **Step 2: Write the input area**

```typescript
// ui-tui/src/components/inputArea.tsx
import React, { useState, useCallback } from 'react';
import { Box, Text, useInput } from 'ink';
import TextInput from 'ink-text-input';
import { theme } from '../theme';
import { CompletionList, SLASH_COMMANDS } from './completionList';

interface InputAreaProps {
  onSubmit: (value: string) => void;
  isBusy: boolean;
}

export const InputArea: React.FC<InputAreaProps> = ({ onSubmit, isBusy }) => {
  const [value, setValue] = useState('');
  const [showCompletions, setShowCompletions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);

  const filtered = value.startsWith('/')
    ? SLASH_COMMANDS.filter(c => c.label.startsWith(value))
    : [];

  const handleSubmit = (val: string) => {
    const trimmed = val.trim();
    if (!trimmed) return;

    if (showCompletions && filtered.length > 0) {
      // Accept selected completion
      setValue(filtered[selectedIndex].label + ' ');
      setShowCompletions(false);
      return;
    }

    setHistory(prev => [...prev, trimmed]);
    setHistoryIdx(-1);
    setValue('');
    setShowCompletions(false);
    onSubmit(trimmed);
  };

  const handleChange = (val: string) => {
    setValue(val);
    if (val.startsWith('/') && val.length > 0) {
      setShowCompletions(true);
      setSelectedIndex(0);
    } else {
      setShowCompletions(false);
    }
  };

  return (
    <Box flexDirection="column">
      <CompletionList
        items={filtered}
        selectedIndex={selectedIndex}
        visible={showCompletions}
      />
      <Box flexDirection="row">
        <Text color={theme.accent.blue} bold>{'> '}</Text>
        <TextInput
          value={value}
          onChange={handleChange}
          onSubmit={handleSubmit}
          placeholder={isBusy ? 'queuing...' : 'ask RUMI anything...'}
          focusColor={theme.txt.primary}
        />
      </Box>
    </Box>
  );
};
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add ui-tui/src/components/inputArea.tsx ui-tui/src/components/completionList.tsx
git commit -m "feat(ui-tui): input area with slash command autocomplete"
```

---

## Task 10: Command Palette (Ctrl+K Modal)

**Files:**
- Create: `ui-tui/src/components/commandPalette.tsx`

- [ ] **Step 1: Write the command palette**

```typescript
// ui-tui/src/components/commandPalette.tsx
import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import { theme } from '../theme';

interface PaletteItem {
  key: string;
  label: string;
  command: string;
}

const PALETTE_ITEMS: PaletteItem[] = [
  { key: 'discover', label: 'Run Discovery Pipeline', command: '/discover ' },
  { key: 'search', label: 'Search Papers', command: '/search ' },
  { key: 'hypothesize', label: 'Generate Hypotheses', command: '/hypothesize ' },
  { key: 'experiment', label: 'Design Experiment', command: '/experiment' },
  { key: 'review', label: 'Peer Review', command: '/review' },
  { key: 'graph', label: 'Knowledge Graph', command: '/graph' },
  { key: 'domains', label: 'List Domains', command: '/domains' },
  { key: 'status', label: 'System Status', command: '/status' },
  { key: 'timeline', label: 'Session Timeline', command: '/timeline' },
  { key: 'clear', label: 'Clear Screen', command: '/clear' },
  { key: 'think', label: 'Toggle Think Mode', command: '/think' },
  { key: 'dive', label: 'Toggle Deep Dive', command: '/dive' },
  { key: 'dashboard', label: 'Discovery Dashboard', command: '/dashboard' },
  { key: 'personality', label: 'Switch Personality', command: '/personality' },
];

interface CommandPaletteProps {
  visible: boolean;
  onSelect: (command: string) => void;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  visible, onSelect, onClose,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  useInput((input, key) => {
    if (!visible) return;

    if (key.escape) {
      onClose();
    } else if (key.upArrow) {
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : PALETTE_ITEMS.length - 1));
    } else if (key.downArrow) {
      setSelectedIndex(prev => (prev < PALETTE_ITEMS.length - 1 ? prev + 1 : 0));
    } else if (key.return) {
      onSelect(PALETTE_ITEMS[selectedIndex].command);
    }
  });

  if (!visible) return null;

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.accent.blue}
      padding={1}
      position="absolute"
      width="60%"
    >
      <Text color={theme.accent.blue} bold>{' (^_^)? Commands'}</Text>
      <Text color={theme.txt.muted}>{' ─'.repeat(25)}</Text>
      {PALETTE_ITEMS.map((item, idx) => (
        <Box key={item.key}>
          <Text
            color={idx === selectedIndex ? theme.accent.blue : theme.txt.primary}
            bold={idx === selectedIndex}
          >
            {idx === selectedIndex ? ' ❯ ' : '   '}
          </Text>
          <Text color={idx === selectedIndex ? theme.txt.bright : theme.txt.primary}>
            {item.label}
          </Text>
          <Text color={theme.txt.muted}>{'  '}{item.command}</Text>
        </Box>
      ))}
      <Text color={theme.txt.muted}>{' ─'.repeat(25)}</Text>
      <Text color={theme.txt.muted}>{' ↑↓ navigate · Enter select · Esc close'}</Text>
    </Box>
  );
};
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add ui-tui/src/components/commandPalette.tsx
git commit -m "feat(ui-tui): command palette modal (Ctrl+K)"
```

---

## Task 11: Discovery Panel

**Files:**
- Create: `ui-tui/src/components/discoveryPanel.tsx`

- [ ] **Step 1: Write the discovery panel**

```typescript
// ui-tui/src/components/discoveryPanel.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface DiscoveryPanelProps {
  topic: string;
  progress: number;
  phase: string;
  papers: number;
  entities: number;
  edges: number;
  isActive: boolean;
}

function makeProgressBar(pct: number, width: number = 10): string {
  const filled = Math.round((pct / 100) * width);
  const empty = width - filled;
  return '[' + '█'.repeat(filled) + '░'.repeat(empty) + '] ' + pct + '%';
}

function progressColor(pct: number): string {
  if (pct < 50) return theme.accent.green;
  if (pct < 80) return theme.accent.amber;
  return theme.accent.blue;
}

export const DiscoveryPanel: React.FC<DiscoveryPanelProps> = ({
  topic, progress, phase, papers, entities, edges, isActive,
}) => {
  if (!isActive && progress === 0) return null;

  return (
    <Box flexDirection="column" paddingX={1} paddingBottom={1}>
      <Text color={theme.accent.purple} bold>
        {'Discovery: '}{topic.slice(0, 60)}
      </Text>
      <Box>
        <Text color={progressColor(progress)}>
          {'  '}{makeProgressBar(progress)}
        </Text>
        <Text color={theme.txt.secondary}>{'  '}{papers} papers</Text>
        <Text color={theme.txt.secondary}>{'  '}{entities} entities</Text>
        <Text color={theme.txt.secondary}>{'  '}{edges} edges</Text>
      </Box>
      {phase && (
        <Text color={theme.txt.muted}>{'  '}{phase}</Text>
      )}
    </Box>
  );
};
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add ui-tui/src/components/discoveryPanel.tsx
git commit -m "feat(ui-tui): discovery pipeline progress panel"
```

---

## Task 12: Session Switcher (Ctrl+X Modal)

**Files:**
- Create: `ui-tui/src/components/sessionSwitcher.tsx`

- [ ] **Step 1: Write the session switcher**

```typescript
// ui-tui/src/components/sessionSwitcher.tsx
import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import { theme } from '../theme';

interface Session {
  id: string;
  title: string;
  model: string;
  messages: number;
}

interface SessionSwitcherProps {
  sessions: Session[];
  visible: boolean;
  onSelect: (sessionId: string) => void;
  onNew: () => void;
  onClose: () => void;
}

export const SessionSwitcher: React.FC<SessionSwitcherProps> = ({
  sessions, visible, onSelect, onNew, onClose,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  useInput((input, key) => {
    if (!visible) return;

    if (key.escape) {
      onClose();
    } else if (key.upArrow) {
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : sessions.length));
    } else if (key.downArrow) {
      setSelectedIndex(prev => (prev < sessions.length ? prev + 1 : 0));
    } else if (key.return) {
      if (selectedIndex === sessions.length) {
        onNew();
      } else if (sessions[selectedIndex]) {
        onSelect(sessions[selectedIndex].id);
      }
    } else if (input === 'd') {
      // Ctrl+D would be caught by parent
    }
  });

  if (!visible) return null;

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.accent.blue}
      padding={1}
      position="absolute"
      width="70%"
    >
      <Text color={theme.accent.blue} bold>{' Sessions'}</Text>
      <Text color={theme.txt.muted}>{' ─'.repeat(30)}</Text>

      {sessions.map((session, idx) => (
        <Box key={session.id}>
          <Text
            color={idx === selectedIndex ? theme.accent.blue : theme.txt.primary}
            bold={idx === selectedIndex}
          >
            {idx === selectedIndex ? ' ❯ ' : '   '}
          </Text>
          <Text color={theme.txt.primary}>{session.title || session.id}</Text>
          <Text color={theme.txt.muted}>{'  '}{session.model} · {session.messages} msgs</Text>
        </Box>
      ))}

      <Box>
        <Text
          color={selectedIndex === sessions.length ? theme.accent.blue : theme.txt.secondary}
          bold={selectedIndex === sessions.length}
        >
          {selectedIndex === sessions.length ? ' ❯ ' : '   '}
        </Text>
        <Text color={theme.accent.green}>{'+ New Session'}</Text>
      </Box>

      <Text color={theme.txt.muted}>{' ─'.repeat(30)}</Text>
      <Text color={theme.txt.muted}>{' ↑↓ navigate · Enter select · Esc close'}</Text>
    </Box>
  );
};
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add ui-tui/src/components/sessionSwitcher.tsx
git commit -m "feat(ui-tui): session switcher modal (Ctrl+X)"
```

---

## Task 13: Main App Component (Wire Everything)

**Files:**
- Create: `ui-tui/src/hooks/useGateway.ts`
- Modify: `ui-tui/src/app.tsx`
- Modify: `ui-tui/src/entry.tsx`

- [ ] **Step 1: Write the gateway hook**

```typescript
// ui-tui/src/hooks/useGateway.ts
import { useEffect, useState, useCallback, useRef } from 'react';
import { GatewayClient } from '../gateway/client';
import { useTranscript } from './useTranscript';
import { ToolCall } from '../components/toolTrail';

export function useGateway() {
  const clientRef = useRef<GatewayClient | null>(null);
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState('READY');
  const [model] = useState('Gemini 2.5');
  const [tokens, setTokens] = useState(0);
  const [cost, setCost] = useState(0);
  const [uptime, setUptime] = useState(0);
  const [thinkMode, setThinkMode] = useState(false);
  const [diveMode, setDiveMode] = useState(false);
  const [tools, setTools] = useState<ToolCall[]>([]);
  const [discovery, setDiscovery] = useState({
    topic: '', progress: 0, phase: '', isActive: false,
    papers: 0, entities: 0, edges: 0,
  });
  const transcript = useTranscript();

  useEffect(() => {
    const client = new GatewayClient();
    clientRef.current = client;

    client.onEvent((method, params) => {
      switch (method) {
        case 'gateway.ready':
          setConnected(true);
          // Auto-create session
          client.send('session.create', {});
          break;

        case 'assistant.message':
          transcript.addAssistantMessage(params.content as string);
          break;

        case 'assistant.stream':
          transcript.appendStream(params.delta as string);
          break;

        case 'assistant.done':
          transcript.addAssistantMessage(transcript.streamingContent);
          if (params.tokens) setTokens(t => t + (params.tokens as number));
          if (params.cost) setCost(c => c + (params.cost as number));
          break;

        case 'user.message':
          transcript.addUserMessage(params.content as string);
          break;

        case 'system.message':
          transcript.addSystemMessage(params.content as string);
          break;

        case 'tool.start':
          setTools(prev => [...prev, {
            id: `tool-${Date.now()}`,
            name: params.name as string,
            query: params.query as string,
            status: 'running',
            isLast: true,
          }]);
          break;

        case 'tool.complete':
          setTools(prev => prev.map(t =>
            t.status === 'running' && t.name === params.name
              ? { ...t, status: 'done' as const, elapsed: params.elapsed as number }
              : { ...t, isLast: false }
          ));
          break;

        case 'discovery.phase':
          setDiscovery(prev => ({
            ...prev,
            phase: params.phase as string,
            progress: params.progress as number,
            topic: params.topic as string,
            isActive: true,
          }));
          break;

        case 'discovery.done':
          setDiscovery(prev => ({
            ...prev,
            isActive: false,
            papers: params.papers as number,
            entities: params.entities as number,
            edges: params.edges as number,
          }));
          break;

        case 'metrics.update':
          setTokens(params.tokens as number);
          setCost(params.cost as number);
          break;

        case 'state.update':
          setState(params.state as string);
          break;

        case 'thinking.start':
          setState('THINKING');
          break;

        case 'thinking.done':
          setState('IDLE');
          break;

        case 'error':
          transcript.addErrorMessage(params.message as string);
          break;
      }
    });

    // Uptime ticker
    const interval = setInterval(() => {
      setUptime(prev => prev + 1);
    }, 1000);

    return () => {
      clearInterval(interval);
      client.destroy();
    };
  }, []);

  const sendMessage = useCallback((content: string) => {
    transcript.addUserMessage(content);
    clientRef.current?.send('chat.send', { content });
  }, []);

  const interrupt = useCallback(() => {
    clientRef.current?.send('chat.interrupt', {});
  }, []);

  const executeSlash = useCallback((command: string) => {
    // Parse "/discover topic" into command + args
    const parts = command.slice(1).split(' ');
    const cmd = parts[0];
    const args = parts.slice(1).join(' ');
    clientRef.current?.send('slash.execute', { command: cmd, args });
  }, []);

  return {
    connected, state, model, tokens, cost, uptime,
    thinkMode, diveMode, tools, discovery,
    transcript, sendMessage, interrupt, executeSlash,
  };
}
```

- [ ] **Step 2: Write the main app.tsx**

```typescript
// ui-tui/src/app.tsx
import React, { useState, useCallback } from 'react';
import { Box, Text, useInput } from 'ink';
import { theme } from './theme';
import { useGateway } from './hooks/useGateway';
import { Banner } from './components/banner';
import { Transcript } from './components/transcript';
import { Streaming } from './components/streaming';
import { ToolTrail, ToolCall } from './components/toolTrail';
import { StatusBar } from './components/statusBar';
import { InputArea } from './components/inputArea';
import { CommandPalette } from './components/commandPalette';
import { SessionSwitcher } from './components/sessionSwitcher';
import { DiscoveryPanel } from './components/discoveryPanel';

export const App: React.FC = () => {
  const gw = useGateway();
  const [showPalette, setShowPalette] = useState(false);
  const [showSwitcher, setShowSwitcher] = useState(false);

  useInput((input, key) => {
    if (key.ctrl && input === 'k') {
      setShowPalette(prev => !prev);
      setShowSwitcher(false);
    } else if (key.ctrl && input === 'x') {
      setShowSwitcher(prev => !prev);
      setShowPalette(false);
    } else if (key.ctrl && input === 'l') {
      gw.transcript.clear();
    } else if (key.escape) {
      if (showPalette) setShowPalette(false);
      else if (showSwitcher) setShowSwitcher(false);
      else gw.interrupt();
    }
  });

  const handleInput = useCallback((value: string) => {
    if (value.startsWith('/')) {
      gw.executeSlash(value);
    } else {
      gw.sendMessage(value);
    }
  }, [gw]);

  const handleSlashFromPalette = useCallback((command: string) => {
    setShowPalette(false);
    gw.executeSlash(command);
  }, [gw]);

  return (
    <Box flexDirection="column" height="100%">
      {/* Collapsible Banner */}
      <Banner
        version="3.0"
        model={gw.model}
        domains={17}
        modules={48}
        sections={[
          {
            title: 'Tools',
            content: ['search, discover, hypothesize, experiment, review, graph'],
            defaultOpen: true,
          },
          {
            title: 'Skills',
            content: ['discovery_engine, knowledge_graph, novelty_checker'],
            defaultOpen: false,
          },
        ]}
      />

      {/* Discovery Panel (when active) */}
      <DiscoveryPanel
        topic={gw.discovery.topic}
        progress={gw.discovery.progress}
        phase={gw.discovery.phase}
        papers={gw.discovery.papers}
        entities={gw.discovery.entities}
        edges={gw.discovery.edges}
        isActive={gw.discovery.isActive}
      />

      {/* Main transcript area */}
      <Box flexDirection="column" flexShrink={1} overflow="hidden">
        <Transcript entries={gw.transcript.entries} />
        <Streaming
          content={gw.transcript.streamingContent}
          isActive={gw.state === 'THINKING' || gw.state === 'PROCESSING'}
        />
        <ToolTrail tools={gw.tools} />
      </Box>

      {/* Status Bar */}
      <StatusBar
        state={gw.state}
        model={gw.model}
        tokens={gw.tokens}
        cost={gw.cost}
        uptime={gw.uptime}
        thinkMode={gw.thinkMode}
        diveMode={gw.diveMode}
      />

      {/* Input Area */}
      <InputArea onSubmit={handleInput} isBusy={gw.state !== 'READY' && gw.state !== 'IDLE'} />

      {/* Modal Overlays */}
      <CommandPalette
        visible={showPalette}
        onSelect={handleSlashFromPalette}
        onClose={() => setShowPalette(false)}
      />
      <SessionSwitcher
        sessions={[]}
        visible={showSwitcher}
        onSelect={() => {}}
        onNew={() => setShowSwitcher(false)}
        onClose={() => setShowSwitcher(false)}
      />
    </Box>
  );
};
```

- [ ] **Step 3: Update entry.tsx**

```typescript
// ui-tui/src/entry.tsx
import React from 'react';
import { render } from 'ink';
import { App } from './app';

render(<App />);
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add ui-tui/src/
git commit -m "feat(ui-tui): wire all components into main App with gateway hook"
```

---

## Task 14: Build & Bundle

**Files:**
- Create: `ui-tui/esbuild.config.mjs`
- Modify: `ui-tui/package.json` (add build script)

- [ ] **Step 1: Create esbuild config**

```javascript
// ui-tui/esbuild.config.mjs
import { build } from 'esbuild';

await build({
  entryPoints: ['src/entry.tsx'],
  bundle: true,
  platform: 'node',
  target: 'node20',
  outfile: 'dist/entry.js',
  external: [],
  banner: {
    js: '#!/usr/bin/env node',
  },
});
```

- [ ] **Step 2: Install deps and build**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && npm install && npm run build`
Expected: `dist/entry.js` created, no errors

- [ ] **Step 3: Verify the bundle runs**

Run: `cd C:\Users\Admin\Desktop\rumi\ui-tui && echo '{"jsonrpc":"2.0","method":"gateway.ready","params":{"version":"3.0"}}' | node dist/entry.js`
Expected: React Ink renders (may error without gateway, but should not crash on import)

- [ ] **Step 4: Commit**

```bash
git add ui-tui/
git commit -m "feat(ui-tui): esbuild bundle, project builds successfully"
```

---

## Task 15: Integration with main.py

**Files:**
- Modify: `rumi_launcher.py`
- Modify: `main.py` (add --tui flag detection)

- [ ] **Step 1: Check rumi_launcher.py**

```python
# rumi_launcher.py — read current content first
```

Run: `cd C:\Users\Admin\Desktop\rumi && python rumi_launcher.py --help 2>&1 || true`
This tells us what the launcher currently does.

- [ ] **Step 2: Add --tui flag to launcher**

After reading the file, modify it to detect `--tui` and spawn the Ink TUI:

```python
# At the top of main() or entry point, add:
import sys
import subprocess

if '--tui' in sys.argv:
    ui_tui_path = Path(__file__).parent / 'ui-tui' / 'dist' / 'entry.js'
    if ui_tui_path.exists():
        gateway_path = Path(__file__).parent / 'rumi_gateway' / 'server.py'
        # Launch gateway as stdin/stdout pipe
        proc = subprocess.Popen(
            [sys.executable, str(gateway_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
        )
        # Then launch Ink TUI connected to gateway's stdout/stdin
        subprocess.run(['node', str(ui_tui_path)])
        proc.wait()
        sys.exit(0)
    else:
        print("[RUMI] ui-tui not built. Run: cd ui-tui && npm run build")
        print("[RUMI] Falling back to classic CLI.")
```

- [ ] **Step 3: Add gateway entry point**

```python
# rumi_gateway/__main__.py
from rumi_gateway.server import GatewayServer

if __name__ == '__main__':
    server = GatewayServer()
    server.start()
```

- [ ] **Step 4: Test the integration**

Run: `cd C:\Users\Admin\Desktop\rumi && python rumi_launcher.py --tui`
Expected: Ink TUI renders in alternate screen, gateway connects, banner shows

- [ ] **Step 5: Commit**

```bash
git add rumi_launcher.py rumi_gateway/__main__.py
git commit -m "feat: wire --tui flag to launch Ink TUI via gateway"
```

---

## Task 16: Polish & Final Touches

- [ ] **Step 1: Add kaomoji thinking indicator to streaming**

In `app.tsx`, import the kaomoji list and show the current face while thinking:

```typescript
const KAOMOJI = [
  '(｡•́︿•̀｡)', '(◔_versed)', '(¬‿¬)', '( •_•)>⌐■-■', '(⌐■_■)',
  '(´･_･`)', '◉_◉', '(°ロ°)', '( ˘⌣˘)♡', 'ヽ(>∀<☆)☆',
  '٩(๑❛ᴗ❛๑)۶', '(⊙_⊙)', '(¬_¬)', '( ͡° ͜ʖ ͡°)', 'ಠ_ಠ',
];
```

Show the current face rotating every 2.5s in the StatusBar when state is THINKING.

- [ ] **Step 2: Test alternate-screen mode**

Run: `cd C:\Users\Admin\Desktop\rumi && python rumi_launcher.py --tui`
Press Ctrl+C to quit. Verify terminal restores previous state (no scrollback clutter).

- [ ] **Step 3: Test all keybindings**

- Ctrl+K opens command palette
- Ctrl+X opens session switcher
- Escape interrupts
- Ctrl+L clears
- Up/Down navigates history
- Tab accepts autocomplete

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: RUMI TUI v3.0 — Ink/React rewrite complete"
```

---

## Verification Checklist

1. `rumi --tui` launches Ink TUI in alternate-screen
2. Streaming responses appear token-by-token with box-drawing
3. Tool calls render as `├─ ✓ name (2.1s)` tree
4. Ctrl+K opens command palette modal
5. Ctrl+X opens session switcher modal
6. Escape interrupts running turns
7. `/discover <topic>` shows pipeline progress panel
8. Status bar shows `● ready │ Gemini 2.5 │ 12.4K tok │ 00:14:22 │ think`
9. Quitting restores previous terminal state
10. `rumi` (no flag) still launches classic Rich CLI
11. Kaomoji faces rotate during thinking
12. Slash autocomplete shows floating list
