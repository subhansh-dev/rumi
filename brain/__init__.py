# brain package — Rumi's neural memory system

# Global Workspace (Thalamus) — unified consciousness
try:
    from brain.global_workspace import get_global_workspace, GlobalWorkspace, WorkspaceParticipant
    from brain.workspace_events import EventType as WsEventType, WorkspaceEvent
    from brain.workspace_context import inject_workspace_context, generate_workspace_context
except ImportError:
    pass

# Self-Modification Engine — safe codebase analysis and evolution tracking
try:
    from brain.self_modifier import get_self_modifier, SelfModifier
except ImportError:
    pass

# Hypothesis Engine — scientific research hypothesis generation and tracking
try:
    from brain.hypothesis_engine import get_hypothesis_engine, Hypothesis, HypothesisEngine
    _hypothesis_engine_ok = True
except ImportError:
    _hypothesis_engine_ok = False

# Voice Modulator — Text-to-speech with multiple backends
try:
    from brain.voice_modulator import get_voice_modulator
    _voice_modulator_ok = True
except ImportError:
    _voice_modulator_ok = False

# Cyber Reasoning — Security vulnerability analysis and CVE search
try:
    from brain.cyber_reasoning import get_cyber_reasoner
    _cyber_reasoning_ok = True
except ImportError:
    _cyber_reasoning_ok = False
