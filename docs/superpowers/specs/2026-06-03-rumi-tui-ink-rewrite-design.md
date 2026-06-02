# RUMI TUI Rewrite — Ink/React + Python Gateway

**Date:** 2026-06-03
**Status:** Approved
**Approach:** Full React Ink rewrite with Python JSON-RPC gateway

## Goal

Rewrite RUMI's terminal UI to match Hermes Agent's TUI quality — alternate-screen rendering, non-blocking input, modal overlays, collapsible sections, mouse support, and streaming tool trails — while staying terminal-native.

## Architecture

### Client-Server over stdin/stdout

```
┌─────────────────────────────────────────────────┐
│  Terminal                                        │
│  ┌───────────────────┐    ┌───────────────────┐  │
│  │  ui-tui/          │    │  Python process    │  │
│  │  React Ink App    │◄──►│  (Gateway)         │  │
│  │  (TypeScript)     │JSON│  Wraps RumiLive    │  │
│  │                   │RPC │  Manages sessions   │  │
│  └───────────────────┘    └───────────────────┘  │
│         stdin/stdout                             │
└─────────────────────────────────────────────────┘
```

- `ui-tui/` — React Ink TypeScript frontend
- `rumi_gateway/` — Python JSON-RPC server wrapping existing `main.py` / `RumiLive` logic
- `ui.py` stays as classic CLI fallback (`rumi` without `--tui`)
- Launch: `rumi --tui` spawns `node ui-tui/dist/entry.js`, gateway runs in-process

### Why React Ink

- Same framework as Hermes Agent's TUI
- `Static` component for scrollable transcript without flicker
- Built-in mouse support, focus management, paste handling
- TypeScript for type safety
- Alternate-screen rendering (no scrollback clutter)

## Screen Layout

```
┌──────────────────────────────────────────────────────────┐
│ ▸ RUMI v3.0 · Gemini 2.5 Flash · 17 domains · 48 modules │  Collapsible banner
├──────────────────────────────────────────────────────────┤
│                                                          │
│  User: What are the gaps in quantum error correction?    │  Transcript
│                                                          │
│  ╭─ RUMI ──────────────────────────────────────────╮    │
│  │ Based on my analysis of 23 recent papers...      │    │
│  │ ...                                              │    │
│  ╰─────────────────────────────────────────────────╯    │
│                                                          │
│  ├─ ✓ searching arxiv (2.1s)                           │  Tool trail
│  ├─ ✓ extracting entities (0.8s)                       │
│  └─ ✓ knowledge graph update (1.2s)                    │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ ● ready │ Gemini 2.5 │ 12.4K tok │ 00:14:22 │ think   │  Status bar
├──────────────────────────────────────────────────────────┤
│ ❯                                                       │  Input (non-blocking)
└──────────────────────────────────────────────────────────┘
```

## Components

| Component | File | Purpose |
|-----------|------|---------|
| `App` | `app.tsx` | Root — state management, event routing, gateway connection |
| `Banner` | `components/banner.tsx` | Collapsible ▸/▾ sections (tools, skills, config) |
| `Transcript` | `components/transcript.tsx` | Scrollable message history with Ink `Static` |
| `StreamingRow` | `components/streaming.tsx` | Live assistant response as tokens arrive |
| `ToolTrail` | `components/toolTrail.tsx` | Tree display: ├─ ✓ tool name (duration) |
| `StatusBar` | `components/statusBar.tsx` | Model, tokens, cost, uptime, mode badges |
| `InputArea` | `components/inputArea.tsx` | Multiline input with slash autocomplete |
| `CommandPalette` | `components/commandPalette.tsx` | Modal overlay (Ctrl+K) |
| `SessionSwitcher` | `components/sessionSwitcher.tsx` | Modal overlay (Ctrl+X) |
| `DiscoveryPanel` | `components/discoveryPanel.tsx` | Pipeline progress with phase indicators |
| `CompletionList` | `components/completionList.tsx` | Floating slash-command autocomplete |

### Key state managed at App level

- `transcript` — array of user/assistant messages
- `streaming` — current assistant response being built
- `toolCalls` — active and recent tool calls with timing
- `queuedMessages` — messages queued while agent is busy
- `sessionInfo` — model, tokens, cost, uptime
- `discoveryState` — pipeline phase, progress %, topic
- `overlay` — which modal is open (none, palette, switcher, model-picker)
- `modeFlags` — think, dive, auto-discover

## Gateway Protocol (JSON-RPC 2.0)

stdout = JSON only. stderr = logs (protocol noise filtered out).

### Methods (Frontend → Gateway)

| Method | Params | Purpose |
|--------|--------|---------|
| `session.create` | `{model?, personality?}` | Start new session |
| `session.resume` | `{session_id}` | Resume previous session |
| `session.info` | `{}` | Get session metadata |
| `chat.send` | `{content}` | Send user message |
| `chat.interrupt` | `{}` | Cancel current turn |
| `chat.history` | `{limit}` | Get message history |
| `slash.execute` | `{command, args}` | Execute slash command |

### Events (Gateway → Frontend)

| Event | Params | Purpose |
|-------|--------|---------|
| `assistant.stream` | `{delta, turn_id}` | Streaming response chunk |
| `assistant.done` | `{turn_id, tokens, cost}` | Response complete |
| `tool.start` | `{name, query, id}` | Tool call began |
| `tool.complete` | `{name, elapsed, id}` | Tool call finished |
| `tool.error` | `{name, error, id}` | Tool call failed |
| `discovery.phase` | `{phase, progress, topic}` | Pipeline phase update |
| `discovery.done` | `{papers, entities, edges}` | Pipeline complete |
| `metrics.update` | `{tokens, cost, latency}` | Token/cost update |
| `graph.update` | `{nodes, edges, clusters}` | Knowledge graph update |
| `error` | `{code, message}` | Error occurred |
| `session.info` | `{model, personality, uptime}` | Session metadata |

### Example flow

```
→ {"jsonrpc":"2.0","id":1,"method":"chat.send","params":{"content":"What are quantum error correction gaps?"}}
← {"jsonrpc":"2.0","method":"assistant.stream","params":{"delta":"Based on","turn_id":"abc123"}}
← {"jsonrpc":"2.0","method":"tool.start","params":{"name":"search","query":"quantum error correction arxiv","id":"t1"}}
← {"jsonrpc":"2.0","method":"tool.complete","params":{"name":"search","elapsed":2.1,"id":"t1"}}
← {"jsonrpc":"2.0","method":"assistant.stream","params":{"delta":" my analysis of 23 papers..."}}
← {"jsonrpc":"2.0","method":"assistant.done","params":{"turn_id":"abc123","tokens":1240,"cost":0.003}}
← {"jsonrpc":"2.0","method":"metrics.update","params":{"tokens":12440,"cost":0.042}}
```

## Visual Design

### Color Palette

```css
/* Backgrounds */
--bg-deep:      #0d1117;
--bg-secondary: #161b22;
--bg-panel:     #1c2128;
--bg-element:   #21262d;
--bg-input:     #0d1117;

/* Text */
--txt-bright:    #f0f6fc;
--txt-primary:   #c9d1d9;
--txt-secondary: #8b949e;
--txt-muted:     #484f58;

/* Accents */
--accent-cyan:   #39d353;
--accent-blue:   #58a6ff;
--accent-green:  #39d353;
--accent-amber:  #d29922;
--accent-red:    #f85149;
--accent-purple: #bc8cff;
```

### Typography & Symbols

- Prompt: `❯` (U+276F) bold cyan
- Kaomoji: 15 rotating faces with thinking verbs (2.5s tick)
- Tool trail: `├─ ✓` / `└─ ✓` with elapsed time
- Response boxes: `╭─╮` / `╰─╯` in accent blue
- Progress bars: `[████░░░░░░] 40%` with color thresholds

### Status Bar Format

```
 ● ready │ Gemini 2.5 │ 12,440 tok │ $0.042 │ 00:14:22 │ think │ dive
```

### Busy Indicator

15 rotating kaomoji faces (`(◔_versed)`, `(¬‿¬)`, etc.) with verbs (`pondering`, `contemplating`, etc.) every 2.5s during agent work.

## Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Escape` | Interrupt current turn |
| `Ctrl+K` | Command palette (modal) |
| `Ctrl+X` | Session switcher (modal) |
| `Ctrl+L` | Clear screen |
| `Ctrl+C` | Quit |
| `Up/Down` | Navigate input history |
| `Tab` | Accept autocomplete suggestion |
| Mouse scroll | Scroll transcript |
| Mouse drag | Select text |

## Slash Commands (all from existing UI)

Discovery: `/discover`, `/search`, `/hypothesize`, `/experiment`, `/review`, `/graph`, `/dashboard`, `/discoveries`, `/enrich`, `/contradictions`, `/generate`, `/simulate`, `/debate`, `/continuous`, `/transfer`, `/curiosity`, `/evolve`, `/consistency`

System: `/help`, `/clear`, `/status`, `/stats`, `/timeline`, `/science`, `/domains`, `/domain`, `/personality`, `/think`, `/dive`, `/model`, `/exit`

## File Structure

```
rumi/
├── ui-tui/                    # NEW — React Ink TUI
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── entry.tsx          # Client entrypoint
│   │   ├── app.tsx            # Root component
│   │   ├── gateway/
│   │   │   ├── client.ts      # JSON-RPC client (stdin/stdout)
│   │   │   └── types.ts       # Protocol types
│   │   ├── components/
│   │   │   ├── banner.tsx
│   │   │   ├── transcript.tsx
│   │   │   ├── streaming.tsx
│   │   │   ├── toolTrail.tsx
│   │   │   ├── statusBar.tsx
│   │   │   ├── inputArea.tsx
│   │   │   ├── commandPalette.tsx
│   │   │   ├── sessionSwitcher.tsx
│   │   │   ├── discoveryPanel.tsx
│   │   │   └── completionList.tsx
│   │   ├── hooks/
│   │   │   ├── useGateway.ts
│   │   │   ├── useTranscript.ts
│   │   │   └── useSession.ts
│   │   └── theme.ts           # Color constants
│   └── dist/
│       └── entry.js           # Built bundle
│
├── rumi_gateway/              # NEW — Python JSON-RPC server
│   ├── __init__.py
│   ├── server.py              # JSON-RPC server (stdin/stdout)
│   ├── session.py             # Session management (wraps RumiLive)
│   └── protocol.py            # Message types and serialization
│
├── ui.py                      # UNCHANGED — classic CLI fallback
├── main.py                    # MODIFIED — add --tui flag to launch ui-tui
├── rumi_launcher.py           # MODIFIED — pass --tui through
└── requirements.txt           # UNCHANGED (gateway uses existing deps)
```

## Implementation Order

1. **Gateway skeleton** — `rumi_gateway/server.py` with JSON-RPC over stdin/stdout, basic `session.create` / `chat.send` / `assistant.stream` flow
2. **Ink app scaffold** — `ui-tui/` with App, StatusBar, InputArea, Transcript rendering
3. **Streaming** — Wire `assistant.stream` events to live transcript rendering
4. **Tool trail** — `tool.start` / `tool.complete` events render as tree
5. **Banner** — Collapsible sections with ▸/▾
6. **Command palette** — Ctrl+K modal overlay with slash commands
7. **Session switcher** — Ctrl+X modal
8. **Discovery panel** — Pipeline progress visualization
9. **Slash command autocomplete** — Floating completion list
10. **Mouse support** — Scroll, select, click
11. **Integration** — Wire to existing `main.py` / `RumiLive`, add `--tui` flag
12. **Polish** — Kaomoji indicator, light-terminal detection, paste handling

## Verification

1. `rumi --tui` launches the Ink TUI in alternate-screen mode
2. Streaming responses appear token-by-token
3. Tool calls render with tree drawing and timing
4. Ctrl+K opens command palette overlay
5. Ctrl+X opens session switcher
6. Escape interrupts a running turn
7. `/discover <topic>` shows pipeline progress panel
8. Status bar shows model, tokens, cost, uptime in real-time
9. Quitting restores previous terminal state (no scrollback clutter)
10. `rumi` (without --tui) still launches classic Rich CLI
