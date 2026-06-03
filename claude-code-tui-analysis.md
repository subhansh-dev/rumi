# Claude Code TUI — Complete Visual & Interaction Analysis

## 1. Architecture Overview

Claude Code is a **React-based TUI** built on a deeply customized fork of **Ink** (a React renderer for terminals). It's not a simple CLI — it's a full React application where `<Box>` and `<Text>` replace `<div>` and `<span>`, and Yoga (Flexbox) replaces CSS for layout.

**Rendering Pipeline (6 stages):**
```
JSX → React Reconciler → Ink DOM → Yoga Layout → Screen Buffer → Double-Buffered Diff → ANSI stdout
```

- **140+ components** in `src/components/`
- **85 React Hooks** in `src/hooks/`
- **40+ files** in the custom `src/ink/` rendering engine
- Uses React 19 concurrent mode with a custom reconciler

---

## 2. Layout Structure

```
┌─────────────────────────────────────────────┐
│  [Scrollable Message History Area]           │
│                                             │
│  User messages (white text)                 │
│  Assistant responses (white, Markdown)      │
│  Tool call blocks (hot pink borders)        │
│  Permission dialogs (lavender borders)      │
│  Diff views (green/red tinted)              │
│                                             │
├─────────────────────────────────────────────┤
│  [Status Bar] — persistent bottom line      │
├─────────────────────────────────────────────┤
│  [Input Area] — dashed ASCII border         │
│  > _ (cursor)                               │
└─────────────────────────────────────────────┘
```

- **Min terminal width**: 80 columns
- **Ideal terminal width**: 120 columns
- **Fullscreen mode**: Uses alternate terminal buffer (ANSI escape), enables mouse scrolling
- Virtual scrolling renders only messages near viewport (overscan: 80 lines above/below)

---

## 3. Color Palette

### Primary Colors (Dark Theme)

| Role | Hex | ANSI 256 | Usage |
|------|-----|----------|-------|
| Background | `#1a1a1a` | 234 | Terminal dark bg |
| Foreground | `#ffffff` | 15 | AI response text, default |
| **Primary (Terracotta)** | `#d77757` | 173 | Brand accent — spinner, thinking, accents |
| **Secondary (Hot Pink)** | `#fd5db1` | 206 | Tool/bash call borders |
| **Accent (Lavender)** | `#b1b9f9` | 147 | Permission dialogs |
| Success | `#4eba65` | 71 | Green — completion, checkmarks |
| Warning | `#ffc107` | 220 | Amber — caution |
| Error | `#ff6b80` | 204 | Soft red-pink — errors |
| Muted | `#888888` | 245 | Input borders, inactive |
| Surface | `#373737` | 237 | User message background |

### Claude-Specific / Shimmer Colors

| Name | Hex | Usage |
|------|-----|-------|
| Claude shimmer | `#eb9f7f` | Lighter terracotta for spinner animation |
| Auto-accept mode | `#af87ff` | Purple — YOLO mode |
| Diff added bg | `#225c2b` | Green tint for added lines |
| Diff removed bg | `#7a2936` | Red tint for removed lines |
| Subtle | `#505050` | Dark gray separators |
| Inactive | `#999999` | Gray disabled elements |

### Theme System

6 built-in themes + custom themes via JSON files in `~/.claude/themes/`:
- `dark` (default), `light`, `dark-daltonized`, `light-daltonized`, `dark-ansi`, `light-ansi`
- Auto mode detects terminal background via `$COLORFGBG` or OSC 11 query
- Color tokens are customizable: `claude`, `text`, `error`, `success`, `diffAdded`, `diffRemoved`, `planMode`, `autoAccept`, etc.
- Shimmer variants: `claude`/`claudeShimmer`, `warning`/`warningShimmer`, etc.

---

## 4. Typography

- **No figlet/ASCII art headers** — clean text only
- **Body**: Plain terminal monospaced font
- **Emphasis**: `bold` for headers, `dim` for metadata
- **Code**: Syntax-highlighted via `cli-highlight` (async loaded via Suspense)
- **Text hierarchy**:
  - H1: BOLD + Terracotta
  - Body: White (#ffffff)
  - Code: Syntax highlighted
  - User input: `>` prefix on Surface bg
  - Caption: Muted + dim (token counts, timestamps)
  - Thinking: Terracotta + shimmer

---

## 5. Borders & Box Drawing

### Input Box — Dashed ASCII (SIGNATURE STYLE)

```
- - - - - - - - - - - - - - - -
| > your message here_          |
- - - - - - - - - - - - - - - -
```

- Uses **plain ASCII dashes** (`-`) and pipe (`|`), NOT Unicode box-drawing
- Border color: Muted gray (`#888888`), shimmers between `#888888` and `#A6A6A6`
- This is deliberate — casual, not corporate

### Tool Call Block — Hot Pink Unicode

```
┌─ Read: src/config.ts ─────────────────┐
│                                        │
│  1 │ export function parseConfig() {   │
│  2 │   const raw = readFileSync(path); │
│                                        │
└────────────────────────────────────────┘
```

- Hot pink (`#fd5db1`) border — visually pops
- Tool name + file path in header
- Background: `rgb(65,60,65)` for bash output

### Permission Dialog — Lavender

```
┌─ Allow Bash: npm test? ────────────┐
│                                     │
│  [Y]es  [N]o  [A]lways             │
│                                     │
└─────────────────────────────────────┘
```

- Lavender (`#b1b9f9`) borders
- Key letters highlighted in bold

---

## 6. Components — Detailed Breakdown

### 6.1 Thinking/Reasoning Indicator

```
  ✳ Percolating...
```

**Spinner characters**: `· → ✢ → ✳ → ✶ → ✻ → ✽ → ✻ → ✶ → ✳ → ✢ → · ...` (reverse-mirror cycle)

- **120ms per frame**, rendered in terracotta with shimmer to `#eb9f7f`
- Paired with **random whimsical verb** from ~184 options:
  "Cogitating...", "Percolating...", "Shenaniganing...", "Moonwalking...", "Ruminating...", "Cogitating...", "Masticating...", "Fluffinating...", etc.
- This is a signature personality element — never generic "Loading..."

### 6.2 Thinking/Extended Thinking Display

When verbose mode is on (`Ctrl+O`):
```
⏺ Thinking…
  Let me analyze the authentication flow. The user wants to add
  JWT refresh tokens. I'll need to modify the middleware first,
  then update the token service...

  [thinking continues in real-time as gray italic text]
```

- Gray italic text, streamed in real-time above actual output
- Toggle with `Ctrl+O` (verbose) or `Alt+T` (extended thinking)
- When off, shows only "Thinking…" indicator

### 6.3 User Prompt

```
- - - - - - - - - - - - - - - - -
|  > What does this function do?  |
- - - - - - - - - - - - - - - - -
```

- `>` prefix, dashed ASCII border, Surface background
- Multi-line support: `\` + Enter, Shift+Enter, or Option+Enter
- Paste detection: >10,000 chars collapses to `[Pasted text]` placeholder
- Vim mode available (`/vim`) with NORMAL/INSERT/VISUAL modes
- Autocomplete for file paths with Tab and `@` references

### 6.4 AI Response (Streaming)

```
  This function parses the configuration file and returns
  a structured object. Here's what each part does:
```

- **White text** on terminal default background
- **No border, no prefix** — clean content-forward
- Markdown rendered with syntax highlighting
- Streaming: tokens appear as received from API (no animation delay)
- Code blocks use `cli-highlight` for syntax coloring

### 6.5 Tool Call Block

```
  ┌─ Read: src/config.ts ─────────────────┐
  │                                        │
  │  1 │ export function parseConfig() {   │
  │  2 │   const raw = readFileSync(path); │
  │  3 │   return JSON.parse(raw);         │
  │                                        │
  └────────────────────────────────────────┘
```

- **Hot pink** (`#fd5db1`) border — tool name + file path in header
- Code with syntax highlighting inside
- In terminal, collapsed to one-line summaries by default: `Read 3 files`, `Edited 2 files`, `Ran bash command`
- Verbose mode shows full content

**Tool states**: pending → running → completed/failed
- `ToolUseLoader`: blinking black circle `●` during execution
- Success: green `✓`
- Error: red `✗`

### 6.6 Diff View

```
  ┌─ Edit: src/app.ts ─────────────────────┐
  │                                         │
  │  - const old = getValue();              │
  │  + const result = getNewValue();        │
  │  + logger.info('Updated');              │
  │                                         │
  └─────────────────────────────────────────┘
```

- Added lines: `+` prefix, `#225c2b` background tint
- Removed lines: `-` prefix, `#7a2936` background tint
- Word-level diff highlighting available
- Uses `Suspense` + `use()` for async diff data loading
- Line numbers displayed

### 6.7 Permission Prompt

```
┌─ Allow Edit to src/app.ts? ────┐
│                                 │
│  [Y]es  [N]o  [A]lways         │
│                                 │
└─────────────────────────────────┘
```

- Lavender (`#b1b9f9`) border
- Tool-specific: Bash, FileEdit, FileWrite, PowerShell, WebFetch, etc. (12+ tool types)
- Shows command with syntax highlighting, working directory
- Options: allow once / allow for session / deny
- Keyboard shortcuts: `y` to allow, `n` to deny

### 6.8 Status Bar (Bottom)

Default format:
```
Opus · 12.4K tokens · $0.04 · 3.2s · normal
```

Highly customizable via `~/.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
}
```

Claude Code pipes JSON to the script's stdin with fields:
- `.model.display_name` — "Opus 4.6 (1M context)"
- `.workspace.current_dir` — "/home/user/project"
- `.context_window.used_percentage` — 0-100
- `.rate_limits.five_hour.used_percentage` — 5h rolling window
- `.rate_limits.seven_day.used_percentage` — weekly limit

Custom status lines can show:
- Git branch (with remote icon)
- Context window progress bar (color-coded: cyan < 75%, yellow 75-90%, red > 90%)
- Token usage (input/output/cached)
- Session cost ($)
- Rate limits
- Model name
- Session duration

### 6.9 Buddy/Companion System (Easter Egg)

- Deterministically generated ASCII character per user (seeded PRNG `mulberry32`)
- Stats: Attack, Defense, etc. with rarities (Common → Legendary)
- Renders with idle animations (blinking, fidgeting)
- Speech bubbles, petting mechanic (heart animation)
- Only visible during specific dates or internal builds

---

## 7. Icons & Indicators

| Purpose | Icon | ASCII Fallback |
|---------|------|----------------|
| Success | `✓` | `+` |
| Error | `✗` | `x` |
| Warning | `⚠` | `!` |
| Thinking | `· ✢ ✳ ✶ ✻ ✽` | `*` |
| Prompt | `>` | `>` |
| Running | `▸` | `>` |
| Bullet | `•` | `-` |
| Black circle (in-progress) | `●` | `*` |

---

## 8. Animation & Motion

### Thinking Spinner
- 6-frame reverse-mirror cycle: `· → ✢ → ✳ → ✶ → ✻ → ✽ → ✻ → ✶ → ✳ → ✢ → ·`
- 120ms per frame
- Terracotta color with shimmer gradient
- Coordinated with Ink's frame scheduling (no `setInterval` — uses `useAnimationFrame`)

### Input Border Shimmer
- Dashed border shimmers between `#888888` and `#A6A6A6`
- Subtle, gentle animation

### Streaming Text
- Tokens appear character-by-character as received from API
- No artificial delay or animation

### Tool Use Loader
- Blinking black circle `●` during execution
- Uses `useBlink` hook with `requestAnimationFrame`

### No Animated Transitions
- Content flows naturally between states
- Tool blocks appear with distinct hot pink border (no slide-in)

---

## 9. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Cancel generation / interrupt |
| `Ctrl+D` | Exit Claude Code |
| `Ctrl+L` | Clear screen |
| `Ctrl+R` | Reverse search history |
| `Ctrl+O` | Toggle verbose output (shows thinking) |
| `Ctrl+T` | Toggle task list |
| `Ctrl+B` | Send task to background |
| `Ctrl+F` | Kill background agents (press twice) |
| `Shift+Tab` | Cycle modes (Normal → Auto-Accept → Plan) |
| `Alt+T` | Toggle extended thinking |
| `Alt+P` | Switch model |
| `Esc, Esc` | Rewind to previous checkpoint (undo) |
| `Tab` | Autocomplete file paths |
| `\` + Enter | New line (multiline input) |
| `Ctrl+G` | Open in external editor |

---

## 10. Three Operating Modes

1. **Normal Mode** (default): Claude asks permission before modifying files/running commands
2. **Auto-Accept Mode** (`Shift+Tab` once): Auto-approves file edits, still prompts for commands
3. **Plan Mode** (`Shift+Tab` twice): Read-only — Claude can only read files and think
4. **Danger Mode** (`--dangerously-skip-permissions`): No prompts at all

---

## 11. Error Display

- Error messages use `#ff6b80` (soft red-pink) color
- Tool failures show red `✗` indicator
- Permission denials show clear feedback
- Notification system with desktop notifications / terminal bell
- Double-press `Ctrl+F` confirmation for killing background agents

---

## 12. Boot/Startup Sequence

```
> claude

  ╔══════════════════════════════════════╗
  ║         Claude Code                 ║
  ║    Your AI coding assistant         ║
  ╚══════════════════════════════════════╝

  [Logo/display name in terracotta]
  [Mode indicator]
  [Input box with dashed border]
```

- Startup shows model name, mode, and context
- No heavy animation on boot
- `/theme` picker available immediately

---

## 13. Message Rendering System

### Message Types & Routing

| Message Type | Component | Rendering |
|-------------|-----------|-----------|
| User text | `UserTextMessage` | White text on Surface bg |
| User image | `UserImageMessage` | Image attachment |
| Assistant text | `AssistantTextMessage` → `Markdown` | White, Markdown rendered |
| Assistant tool call | `AssistantToolUseMessage` | Tool-specific renderer |
| Tool result | `UserToolResultMessage` | Collapsed/expanded |
| Assistant thinking | `AssistantThinkingMessage` | Gray italic (verbose mode) |
| System message | `SystemTextMessage` | Dimmed |
| Collapsed groups | `CollapsedReadSearchContent` | Summary line |
| Grouped tool calls | `GroupedToolUseContent` | Stacked |

### Markdown Rendering
- Uses `marked` library for lexing
- Fast path: regex checks for Markdown syntax before parsing (skips 3ms lexer for plain text)
- LRU token cache (500 entries) — content hashes as keys
- Tables use React `<MarkdownTable>` for Flexbox alignment
- Code blocks use `cli-highlight` (async via Suspense)

---

## 14. Performance Optimizations

- **Double buffering + frame diffing**: Only changed cells written to terminal
- **Blit optimization**: Unchanged regions copied from previous frame
- **CharPool string interning**: Characters mapped to integer IDs for fast comparison
- **Virtual scrolling**: Only viewport messages mounted (overscan: 80 lines)
- **Progressive mounting**: Max 25 new items per frame during rapid scroll
- **Scroll quantization**: 40-line steps to reduce React commits
- **Markdown token LRU cache**: Avoids re-parsing immutable content
- **Lazy syntax highlighting**: `cli-highlight` loaded via Suspense

---

## 15. Fullscreen Mode

- Uses ANSI alternate screen buffer (`?1049h`/`?1049l`)
- Enables mouse scrolling and text selection
- Content height forced to equal terminal row count
- Toggle with `/tui fullscreen` or `CLAUDE_CODE_NO_FLICKER=1`
- Background fills for user messages, bash entries, memory entries

---

## 16. Design Principles Summary

### Do
- Use **terracotta** (`#d77757`) as primary brand accent — warm, distinctive
- Use **dashed ASCII borders** for input (NOT Unicode box-drawing)
- Use **hot pink** for tool call borders — makes them pop
- Use **whimsical, playful language** for loading states (never "Loading...")
- Keep response text **pure white** — readability is paramount
- Content-forward, minimal chrome

### Don't
- Don't use cold/corporate blues — Claude Code is warm
- Don't use Unicode box-drawing for input area — dashed ASCII is the signature
- Don't over-border — most content flows without frames
- Don't colorize AI response body text — white for trust
- Don't use generic "Loading..." — the random verbs are part of the personality

---

## 17. Subagent Colors

Each subagent gets a unique color from:
red, blue, green, yellow, purple, orange, pink, cyan

Tokens: `<color>_FOR_SUBAGENTS_ONLY` in theme config.

---

## 18. Special Keywords

- `ultrathink` and `ultraplan` in prompt input render with **seven-color rainbow gradient**
- Token names: `rainbow_<color>` + `rainbow_<color>_shimmer` (red, orange, yellow, green, blue, indigo, violet)

---

## 19. Key Source Files (from leaked source)

| Area | Path |
|------|------|
| Rendering engine | `src/ink/` (40+ files) |
| Reconciler | `src/ink/reconciler.ts` |
| Layout engine | `src/ink/layout/` |
| Screen buffer | `src/ink/screen.ts` |
| Frame diffing | `src/ink/log-update.ts` |
| DOM abstraction | `src/ink/dom.ts` |
| Style system | `src/ink/styles.ts` |
| Components | `src/components/` (144 files) |
| Messages | `src/components/Messages.tsx`, `Message.tsx` |
| Permissions | `src/components/permissions/` (~30 files) |
| Diffs | `src/components/StructuredDiff/` |
| Input | `src/components/PromptInput/` |
| Spinner | `src/components/Spinner/` |
| Hooks | `src/hooks/` (85 hooks) |
| State | `src/state/AppState.ts` |
| Theme | `src/utils/theme.ts` |
| Buddy system | `src/buddy/CompanionSprite.tsx`, `companion.ts` |
| App root | `src/App.tsx` |

---

## 20. Summary: What Makes Claude Code's TUI Distinctive

1. **Warm terracotta accent** — not cold blue, not generic green
2. **Dashed ASCII input border** — casual, approachable, signature look
3. **Hot pink tool borders** — tools visually pop from conversation
4. **Whimsical thinking verbs** — personality in every loading state
5. **Clean white response text** — trust and readability
6. **React + Ink architecture** — declarative UI, 140+ components, 85 hooks
7. **Performance**: double buffering, string interning, virtual scrolling, blit optimization
8. **Minimal chrome** — content flows naturally, borders only where needed
9. **Customizable everything** — themes, status lines, keybindings, spinner verbs
10. **The buddy system** — Easter egg ASCII companion with stats and rarity
