# Session Context — May 27, 2026

## Last Session Summary
- Focus: UI overhaul, voice toggle, personality injection, discovery progress indicators
- Persona: Fixed cutesy not taking effect — core/prompt.txt now references SOUL.md for personality, _build_config() injects active SOUL.md/RUMI.md into system prompt
- Voice: Added voice_enabled config option, setup now asks chat-only vs chat+voice (default: chat-only). All speech/audio guarded behind _voice_enabled flag.
- UI: Removed focus mode, mute command. Cleaned up startup (no animation flash). Added dark theme force via rich.theme. Discovery steps shown in toolbar and printed.
- Commands removed: /focus, /mute (and from help, tab-complete)
- Bugs: _workspace getattr fix applied, toggle_mute removed

## Open Issues
- /discover still not verified working — needs API quota to test
- The core/prompt.txt has a large SCIENTIST AI section appended (verify it's correct)

## Key Files Modified
- ui.py: RumiUI class — _show_startup, _handle_command, _get_toolbar, __init__, setup wizard
- main.py: _build_config, _run_discovery_pipeline, _on_discovery_command, speak(), __init__
- core/prompt.txt: Vibe section replaced to reference SOUL.md for personality
