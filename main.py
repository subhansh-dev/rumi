# -- coding: utf-8 --
"""
main.py — RUMI Scientist AI (v2.0)

Autonomous Cognitive AI for Scientific Research & Software Engineering.
- 60+ cognitive brain modules (memory, learning, reasoning, consciousness)
- Terminal-native interface (Rich + prompt_toolkit)
- Gemini 2.5 Flash primary model with multi-model routing
"""
import asyncio
import json
import os
import re
import struct
import sys
import threading
import time
import traceback
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from discovery.domains import DOMAINS, get_domain, entity_types_list, build_detect_prompt, entity_colors, DOMAIN_ALIAS_MAP, list_domains

import sounddevice as sd
from google import genai
from google.genai import types

def _is_ws_dead_error(err_str: str) -> bool:
    """Detect WebSocket dead errors (e.g., 1006, 1011, closed)."""
    return any(k in err_str for k in (
        "1006", "1011", "closed", "not connected",
        "connection reset", "broken pipe",
    ))

try:
    from ui import RumiUI
except Exception as e:
    print(f"[RUMI] UI import failed: {e}", flush=True)
    raise

# ── Brain module imports (all wrapped) ────────────────────────────────
_brain_neural_memory_ok = False
try:
    from brain.neural_memory import (
        load_memory, update_memory, format_memory_for_prompt, get_brain,
    )
    _brain_neural_memory_ok = True
except Exception as e:
    print(f"[RUMI] brain.neural_memory: {e}", flush=True)
    load_memory = update_memory = format_memory_for_prompt = get_brain = None

_brain_learning_ok = False
try:
    from brain.learning import (
        get_learning_engine, init_learnings_file, EventType,
    )
    _brain_learning_ok = True
except Exception as e:
    print(f"[RUMI] brain.learning: {e}", flush=True)
    get_learning_engine = init_learnings_file = EventType = None

_brain_self_model_ok = False
try:
    from brain.self_model import get_self_model
    _brain_self_model_ok = True
except Exception as e:
    print(f"[RUMI] brain.self_model: {e}", flush=True)
    get_self_model = None

_brain_active_inference_ok = False
try:
    from brain.active_inference import get_active_inference
    _brain_active_inference_ok = True
except Exception as e:
    print(f"[RUMI] brain.active_inference: {e}", flush=True)
    get_active_inference = None

_brain_dreaming_ok = False
try:
    from brain.dreaming import get_dreaming_system
    _brain_dreaming_ok = True
except Exception as e:
    print(f"[RUMI] brain.dreaming: {e}", flush=True)
    get_dreaming_system = None

_brain_curiosity_ok = False
try:
    from brain.curiosity import get_curiosity_module
    _brain_curiosity_ok = True
except Exception as e:
    print(f"[RUMI] brain.curiosity: {e}", flush=True)
    get_curiosity_module = None

_brain_self_awareness_ok = False
try:
    from brain.self_awareness import get_self_awareness, CognitiveEvent
    _brain_self_awareness_ok = True
except Exception as e:
    print(f"[RUMI] brain.self_awareness: {e}", flush=True)
    get_self_awareness = CognitiveEvent = None

_brain_coordinator_ok = False
try:
    from brain.memory_coordinator import get_memory_coordinator
    _brain_coordinator_ok = True
except Exception as e:
    print(f"[RUMI] brain.memory_coordinator: {e}", flush=True)
    get_memory_coordinator = None

_brain_procedural_ok = False
try:
    from brain.procedural_memory import get_procedural_memory
    _brain_procedural_ok = True
except Exception as e:
    print(f"[RUMI] brain.procedural_memory: {e}", flush=True)
    get_procedural_memory = None

_brain_episodic_ok = False
try:
    from brain.episodic_memory import get_episodic_memory
    _brain_episodic_ok = True
except Exception as e:
    print(f"[RUMI] brain.episodic_memory: {e}", flush=True)
    get_episodic_memory = None

_brain_vector_ok = False
try:
    from brain.vector_memory import get_vector_memory
    _brain_vector_ok = True
except Exception as e:
    print(f"[RUMI] brain.vector_memory: {e}", flush=True)
    get_vector_memory = None

# ── Global Workspace (Thalamus) ───────────────────────────────────────
_brain_workspace_ok = False
try:
    from brain.global_workspace import get_global_workspace, GlobalWorkspace
    from brain.workspace_events import EventType as WsEventType, WorkspaceEvent
    from brain.workspace_context import inject_workspace_context
    from brain.workspace_adapters import (
        SelfAwarenessAdapter, LearningAdapter, ActiveInferenceAdapter,
        CuriosityAdapter, DreamingAdapter, SelfModelAdapter,
        NeuralMemoryAdapter, EpisodicMemoryAdapter, ProceduralMemoryAdapter,
        MetaCognitionAdapter, MemoryCoordinatorAdapter,
    )
    _brain_workspace_ok = True

    _brain_proactive_ok = False
    try:
        from brain.proactive_engine import get_proactive_engine
        _brain_proactive_ok = True
    except Exception as e:
        print(f"[RUMI] brain.proactive_engine: {e}", flush=True)
        get_proactive_engine = None

    _brain_agi_orch_ok = False
    try:
        from brain.agi_orchestrator import get_agi_orchestrator
        _brain_agi_orch_ok = True
    except Exception as e:
        print(f"[RUMI] brain.agi_orchestrator: {e}", flush=True)
        get_agi_orchestrator = None
except Exception as e:
    print(f"[RUMI] brain.global_workspace: {e}", flush=True)
    get_global_workspace = GlobalWorkspace = None
    WsEventType = WorkspaceEvent = inject_workspace_context = None
    SelfAwarenessAdapter = LearningAdapter = ActiveInferenceAdapter = None
    CuriosityAdapter = DreamingAdapter = SelfModelAdapter = None
    NeuralMemoryAdapter = EpisodicMemoryAdapter = ProceduralMemoryAdapter = None
    MetaCognitionAdapter = MemoryCoordinatorAdapter = None

_telegram_ok = False
try:
    from rumi_telegram_patch import TelegramBridge
    _telegram_ok = True
except Exception as e:
    print(f"[RUMI] TelegramBridge: {e}", flush=True)
    TelegramBridge = None

# ── Action imports ────────────────────────────────────────────────────
def _safe_action_import(module_path, names):
    try:
        mod = __import__(module_path, fromlist=[names] if isinstance(names, str) else names)
        if isinstance(names, str):
            return getattr(mod, names), True
        return {n: getattr(mod, n) for n in names}, True
    except Exception as e:
        print(f"[RUMI] {module_path}: {e}", flush=True)
        return None, False

open_app = None
weather_action = None
send_message = None
reminder = None
computer_settings = None
screen_process, _ = _safe_action_import("actions.screen_processor", "screen_process")
youtube_video = None
desktop_control, _ = _safe_action_import("actions.desktop", "desktop_control")
browser_control, _ = _safe_action_import("actions.browser_control", "browser_control")
file_controller, _ = _safe_action_import("actions.file_controller", "file_controller")
dev_agent, _ = _safe_action_import("actions.dev_agent", "dev_agent")
web_search_action, _ = _safe_action_import("actions.web_search", "web_search")
computer_control, _ = _safe_action_import("actions.computer_control", "computer_control")
web_research, _ = _safe_action_import("actions.web_research", "web_research")
agency_agent_action, _ = _safe_action_import("actions.agency_agent", "agency_agent")
agency_list_agents = None
research_pipeline, _ = _safe_action_import("actions.research_pipeline", "research_pipeline")

_brain_self_modifier_ok = False
try:
    from brain.self_modifier import get_self_modifier
    _brain_self_modifier_ok = True
except Exception as e:
    print(f"[RUMI] brain.self_modifier: {e}", flush=True)
    get_self_modifier = None

# ── Disconnected cognitive module imports ──────────────────────────────
_brain_analogy_ok = False
try:
    from brain.analogy_engine import get_analogy_engine
    _brain_analogy_ok = True
except Exception as e:
    print(f"[RUMI] brain.analogy_engine: {e}", flush=True)
    get_analogy_engine = None

_brain_causal_ok = False
try:
    from brain.causal_reasoner import get_causal_reasoner
    _brain_causal_ok = True
except Exception as e:
    print(f"[RUMI] brain.causal_reasoner: {e}", flush=True)
    get_causal_reasoner = None

_brain_creativity_ok = False
try:
    from brain.creativity_engine import get_creativity_engine
    _brain_creativity_ok = True
except Exception as e:
    print(f"[RUMI] brain.creativity_engine: {e}", flush=True)
    get_creativity_engine = None

_brain_meta_learner_ok = False
try:
    from brain.meta_learner import get_meta_learner
    _brain_meta_learner_ok = True
except Exception as e:
    print(f"[RUMI] brain.meta_learner: {e}", flush=True)
    get_meta_learner = None

_brain_module_competition_ok = False
try:
    from brain.module_competition import get_module_competition
    _brain_module_competition_ok = True
except Exception as e:
    print(f"[RUMI] brain.module_competition: {e}", flush=True)
    get_module_competition = None

_brain_neurosymbolic_ok = False
try:
    from brain.neurosymbolic_reasoner import get_neurosymbolic_reasoner
    _brain_neurosymbolic_ok = True
except Exception as e:
    print(f"[RUMI] brain.neurosymbolic_reasoner: {e}", flush=True)
    get_neurosymbolic_reasoner = None

_brain_narrative_ok = False
try:
    from brain.narrative_intelligence import get_narrative_intelligence
    _brain_narrative_ok = True
except Exception as e:
    print(f"[RUMI] brain.narrative_intelligence: {e}", flush=True)
    get_narrative_intelligence = None

# Scientist AI Modules
try:
    from scientist.discovery_engine import get_discovery_engine
    _scientist_discovery_ok = True
except Exception as e:
    print(f"[RUMI] scientist.discovery_engine: {e}", flush=True)
    get_discovery_engine = None
    _scientist_discovery_ok = False

try:
    from scientist.novelty_checker import get_novelty_checker
    _scientist_novelty_ok = True
except Exception as e:
    print(f"[RUMI] scientist.novelty_checker: {e}", flush=True)
    get_novelty_checker = None
    _scientist_novelty_ok = False

try:
    from scientist.experiment_designer import get_experiment_designer
    _scientist_experiment_ok = True
except Exception as e:
    print(f"[RUMI] scientist.experiment_designer: {e}", flush=True)
    get_experiment_designer = None
    _scientist_experiment_ok = False

try:
    from scientist.paper_generator import get_paper_generator
    _scientist_paper_ok = True
except Exception as e:
    print(f"[RUMI] scientist.paper_generator: {e}", flush=True)
    get_paper_generator = None
    _scientist_paper_ok = False

try:
    from scientist.peer_reviewer import get_peer_reviewer
    _scientist_review_ok = True
except Exception as e:
    print(f"[RUMI] scientist.peer_reviewer: {e}", flush=True)
    get_peer_reviewer = None
    _scientist_review_ok = False

try:
    from scientist.feynman_reducer import get_feynman_reducer
    _scientist_feynman_ok = True
except Exception as e:
    print(f"[RUMI] scientist.feynman_reducer: {e}", flush=True)
    get_feynman_reducer = None
    _scientist_feynman_ok = False

try:
    from scientist.cross_validator import get_cross_validator
    _scientist_validate_ok = True
except Exception as e:
    print(f"[RUMI] scientist.cross_validator: {e}", flush=True)
    get_cross_validator = None
    _scientist_validate_ok = False

try:
    from scientist.research_team import get_research_team
    _scientist_team_ok = True
except Exception as e:
    print(f"[RUMI] scientist.research_team: {e}", flush=True)
    get_research_team = None
    _scientist_team_ok = False

try:
    from scientist.scientist_search import get_scientist_search
    _scientist_search_ok = True
except Exception as e:
    print(f"[RUMI] scientist.scientist_search: {e}", flush=True)
    get_scientist_search = None
    _scientist_search_ok = False

# New Scientist v2 modules
try:
    from scientist.tournament_hypothesis import get_tournament_engine
    _scientist_tournament_ok = True
except Exception as e:
    print(f"[RUMI] scientist.tournament_hypothesis: {e}", flush=True)
    get_tournament_engine = None
    _scientist_tournament_ok = False

try:
    from scientist.knowledge_graph import get_knowledge_graph
    _scientist_kg_ok = True
except Exception as e:
    print(f"[RUMI] scientist.knowledge_graph: {e}", flush=True)
    get_knowledge_graph = None
    _scientist_kg_ok = False

try:
    from scientist.reproducibility_engine import get_reproducibility_engine
    _scientist_repro_ok = True
except Exception as e:
    print(f"[RUMI] scientist.reproducibility_engine: {e}", flush=True)
    get_reproducibility_engine = None
    _scientist_repro_ok = False

try:
    from scientist.active_experiment_selector import get_experiment_selector
    _scientist_aes_ok = True
except Exception as e:
    print(f"[RUMI] scientist.active_experiment_selector: {e}", flush=True)
    get_experiment_selector = None
    _scientist_aes_ok = False

try:
    from scientist.cross_domain_connector import get_cross_domain_connector
    _scientist_cdc_ok = True
except Exception as e:
    print(f"[RUMI] scientist.cross_domain_connector: {e}", flush=True)
    get_cross_domain_connector = None
    _scientist_cdc_ok = False

try:
    from scientist.lab_notebook import get_lab_notebook
    _scientist_notebook_ok = True
except Exception as e:
    print(f"[RUMI] scientist.lab_notebook: {e}", flush=True)
    get_lab_notebook = None
    _scientist_notebook_ok = False

_brain_world_model_ok = False
try:
    from brain.world_model import get_world_model
    _brain_world_model_ok = True
except Exception as e:
    print(f"[RUMI] brain.world_model: {e}", flush=True)
    get_world_model = None

_brain_enhanced_wm_ok = False
try:
    from brain.enhanced_world_model import get_enhanced_world_model
    _brain_enhanced_wm_ok = True
except Exception as e:
    print(f"[RUMI] brain.enhanced_world_model: {e}", flush=True)
    get_enhanced_world_model = None

_brain_hierarchical_aif_ok = False
try:
    from brain.hierarchical_active_inference import get_hierarchical_aif
    _brain_hierarchical_aif_ok = True
except Exception as e:
    print(f"[RUMI] brain.hierarchical_active_inference: {e}", flush=True)
    get_hierarchical_aif = None

_brain_integrated_info_ok = False
try:
    from brain.integrated_info import get_integrated_info
    _brain_integrated_info_ok = True
except Exception as e:
    print(f"[RUMI] brain.integrated_info: {e}", flush=True)
    get_integrated_info = None

_brain_transfer_learning_ok = False
try:
    from brain.transfer_learning import get_transfer_learning
    _brain_transfer_learning_ok = True
except Exception as e:
    print(f"[RUMI] brain.transfer_learning: {e}", flush=True)
    get_transfer_learning = None

_brain_self_improve_ok = False
try:
    from brain.self_improve_engine import get_self_improve_engine
    _brain_self_improve_ok = True
except Exception as e:
    print(f"[RUMI] brain.self_improve_engine: {e}", flush=True)
    get_self_improve_engine = None

_brain_findings_bus_ok = False
try:
    from brain.findings_bus import get_findings_bus
    _brain_findings_bus_ok = True
except Exception as e:
    print(f"[RUMI] brain.findings_bus: {e}", flush=True)
    get_findings_bus = None

_brain_model_router_ok = False
try:
    from brain.model_router import get_model_router
    _brain_model_router_ok = True
except Exception as e:
    print(f"[RUMI] brain.model_router: {e}", flush=True)
    get_model_router = None

_brain_intuition_ok = False
try:
    from brain.intuition_engine import get_intuition_engine
    _brain_intuition_ok = True
except Exception as e:
    print(f"[RUMI] brain.intuition_engine: {e}", flush=True)
    get_intuition_engine = None

_brain_metacognitive_ok = False
try:
    from brain.metacognitive_monitor import get_metacognitive_monitor
    _brain_metacognitive_ok = True
except Exception as e:
    print(f"[RUMI] brain.metacognitive_monitor: {e}", flush=True)
    get_metacognitive_monitor = None

_brain_cognitive_integration_ok = False
try:
    from brain.cognitive_integration import get_cognitive_integration
    _brain_cognitive_integration_ok = True
except Exception as e:
    print(f"[RUMI] brain.cognitive_integration: {e}", flush=True)
    get_cognitive_integration = None

_brain_cognitive_load_ok = False
try:
    from brain.cognitive_load import get_cognitive_load_manager
    _brain_cognitive_load_ok = True
except Exception as e:
    print(f"[RUMI] brain.cognitive_load: {e}", flush=True)
    get_cognitive_load_manager = None

_agi_multi_agent_ok = False
try:
    from brain.multi_agent_orchestrator import get_multi_agent_orchestrator
    _agi_multi_agent_ok = True
except Exception as e:
    print(f"[RUMI] brain.multi_agent_orchestrator: {e}", flush=True)
    get_multi_agent_orchestrator = None

_agi_goal_ok = False
try:
    from brain.goal_engine import get_goal_engine
    _agi_goal_ok = True
except Exception as e:
    print(f"[RUMI] brain.goal_engine: {e}", flush=True)
    get_goal_engine = None

_agi_motivation_ok = False
try:
    from brain.intrinsic_motivation import get_intrinsic_motivation
    _agi_motivation_ok = True
except Exception as e:
    print(f"[RUMI] brain.intrinsic_motivation: {e}", flush=True)
    get_intrinsic_motivation = None

_agi_planner_ok = False
try:
    from brain.autonomous_planner import get_autonomous_planner
    _agi_planner_ok = True
except Exception as e:
    print(f"[RUMI] brain.autonomous_planner: {e}", flush=True)
    get_autonomous_planner = None

_agi_mem_consolidation_ok = False
try:
    from brain.memory_consolidation import get_memory_consolidation
    _agi_mem_consolidation_ok = True
except Exception as e:
    print(f"[RUMI] brain.memory_consolidation: {e}", flush=True)
    get_memory_consolidation = None

_agi_associative_ok = False
try:
    from brain.associative_memory import get_associative_memory
    _agi_associative_ok = True
except Exception as e:
    print(f"[RUMI] brain.associative_memory: {e}", flush=True)
    get_associative_memory = None

_agi_predictive_ok = False
try:
    from brain.predictive_memory import get_predictive_memory
    _agi_predictive_ok = True
except Exception as e:
    print(f"[RUMI] brain.predictive_memory: {e}", flush=True)
    get_predictive_memory = None

_agi_tom_ok = False
try:
    from brain.theory_of_mind import get_theory_of_mind
    _agi_tom_ok = True
except Exception as e:
    print(f"[RUMI] brain.theory_of_mind: {e}", flush=True)
    get_theory_of_mind = None

_agi_abstraction_ok = False
try:
    from brain.abstraction_engine import get_abstraction_engine
    _agi_abstraction_ok = True
except Exception as e:
    print(f"[RUMI] brain.abstraction_engine: {e}", flush=True)
    get_abstraction_engine = None

_agi_introspection_ok = False
try:
    from brain.introspection_engine import get_introspection_engine
    _agi_introspection_ok = True
except Exception as e:
    print(f"[RUMI] brain.introspection_engine: {e}", flush=True)
    get_introspection_engine = None

_agi_world_sim_ok = False
try:
    from brain.world_simulation import get_world_simulation
    _agi_world_sim_ok = True
except Exception as e:
    print(f"[RUMI] brain.world_simulation: {e}", flush=True)
    get_world_simulation = None

_verification_ok = False
try:
    from actions.verification import (
        is_window_focused, ensure_window_focused, verify_app_opened,
        verify_message_sent_in_chat, vision_query, screenshot_as_part,
        ActionVerifier,
    )
    _verification_ok = True
except Exception as e:
    print(f"[RUMI] verification module: {e}", flush=True)

_thinking_loop_ok = False
try:
    from thinking_loop import think as thinking_loop_think
    from thinking_loop import reflect_on_outcome as thinking_loop_reflect
    _thinking_loop_ok = True
except Exception as e:
    print(f"[RUMI] thinking_loop: {e}", flush=True)

_ai_pipeline_ok = False
try:
    from actions.ai_pipeline import (
        summarize_text, analyze_sentiment, extract_entities,
        translate_text, process_document,
    )
    _ai_pipeline_ok = True
except Exception:
    pass

_integrations_ok = False
try:
    from brain.integrations import (
        analyze_data, query_data, generate_chart,
        integration_status, get_system_dashboard,
    )
    _integrations_ok = True
except Exception:
    pass

# ── Security imports ──────────────────────────────────────────────────
_security_ok = False
try:
    from security import (
        get_permission_manager, get_audit_logger, get_config_validator,
        get_lock_state, RiskTier, Decision,
    )
    from security.audit_logger import redact_params
    from security.config_validator import ConfigValidationError
    _security_ok = True
except Exception as e:
    print(f"[RUMI] Security: {e}", flush=True)

_rate_limiter_available = False
try:
    from security.tools_guard import get_rate_limiter
    _rate_limiter_available = True
except ImportError:
    pass

if not _security_ok:
    print("[RUMI] Security module not available — using permissive fallback", flush=True)
    class _FakePermMgr:
        def check_tool(self, *a, **kw): return "allow", "no security module"
        def get_risk_tier(self, *a, **kw): return 0
        def shutdown(self): pass
    class _FakeAudit:
        def log(self, **kw): pass
        def shutdown(self): pass
    class _FakeLockState:
        def check_and_log(self, *a, **kw): return True, ""
    class _FakeDecision:
        ALLOW = "allow"
        DENY = "deny"
        ASK = "ask"
    get_permission_manager = lambda: _FakePermMgr()
    get_audit_logger = lambda: _FakeAudit()
    get_lock_state = lambda: _FakeLockState()
    Decision = _FakeDecision()
    RiskTier = type('RiskTier', (), {'HIGH': 2, 'MEDIUM': 1, 'LOW': 0})()
    redact_params = lambda x: x
    class ConfigValidationError(Exception): pass
    def get_config_validator():
        class _V:
            def load(self, p): pass
            def validate(self): return []
            def get_api_key(self): return ""
        return _V()

# ── Optional imports ──────────────────────────────────────────────────
# ── Cyber features gated behind config flag (disabled by default) ──
_cyber_enabled = False
try:
    _cfg_data = json.loads((BASE_DIR / "config" / "api_keys.json").read_text(encoding="utf-8"))
    _cyber_enabled = bool(_cfg_data.get("cyber_enabled", False))
except Exception:
    pass

# ── Cyber authorization (consent gate for live operations) ──
_cyber_auth_manager = None
if _cyber_enabled:
    try:
        from cyber.authorization import (
            get_auth_manager as _get_auth_manager,
            grant_consent as _grant_consent,
            is_live_operation as _is_live_op,
            CONSENT_PHRASE as _CONSENT_PHRASE,
        )
        _cyber_auth_manager = _get_auth_manager()
    except ImportError:
        pass

if _cyber_enabled:
    try:
        from actions.security_tools import security_tools
        _security_tools_available = True
    except ImportError:
        _security_tools_available = False
else:
    _security_tools_available = False

try:
    from agent.task_queue import get_queue, TaskPriority
    _task_queue_available = True
except ImportError:
    _task_queue_available = False

try:
    from gesture_music_system.main import GestureMusicSystem
    _gesture_available = True
except ImportError:
    _gesture_available = False

try:
    from gesture_music_system.actions import MusicController
    _music_ctrl = MusicController()
except Exception:
    _music_ctrl = None

_skills_ok = False
try:
    from skills.deep_dive import DeepDiveAgent
    from skills.sentinel import SystemSentinel
    from skills.neural_clipboard import NeuralClipboard
    from skills.auto_doc import AutoDocEngine
    from skills.cognitive_gating import assess_complexity
    from skills.working_memory import get_working_memory
    from skills.meta_reflect import get_meta_reflection
    from skills.decision_journal import get_decision_journal
    from skills.experience_replay import get_experience_replay
    from skills.adaptive_planner import get_adaptive_planner
    from skills.research_agent import get_research_agent
    from skills.document_intelligence import get_document_intelligence
    _skills_ok = True
except Exception:
    pass

try:
    import cv2
except ImportError:
    pass

# ── Force unbuffered stdout ───────────────────────────────────────────
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

# ── Constants ─────────────────────────────────────────────────────────
def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH = BASE_DIR / "core" / "prompt.txt"

LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
KEEPALIVE_INTERVAL = 5
MAX_INSTRUCTION_LEN = 28000
MAX_RECONNECT_DELAY = 120
MAX_TOOL_RESULT_LEN = 2000

VALID_MEMORY_CATEGORIES = {
    "identity", "preferences", "projects",
    "relationships", "wishes", "notes",
}

_VALID_PARAMS = {
    "browser_control": {
        "action", "browser", "url", "query", "engine", "selector",
        "text", "description", "direction", "amount", "key", "path",
        "incognito", "clear_first",
    },
    "computer_control": {
        "action", "text", "x", "y", "keys", "key", "direction",
        "amount", "seconds", "title", "description", "data_type",
        "field", "clear_first", "path",
    },
    "computer_settings": {
        "action", "description", "value",
    },
}


class _SessionDead(Exception):
    pass


def _is_ws_dead_error(err_str: str) -> bool:
    """Check if an error indicates a dead WebSocket session."""
    return any(k in err_str for k in (
        "1006", "1011", "closed", "not connected",
        "connection reset", "broken pipe",
    ))


class _NullCallable:
    def __call__(self, *a, **kw):
        return None
    def __await__(self):
        if False:
            yield
        return None


class _NullModule:
    def __getattr__(self, name):
        return _NullCallable()


# ── Config & Prompt Helpers ───────────────────────────────────────────
def _get_api_key() -> str:
    try:
        validator = get_config_validator()
        validator.load(API_CONFIG_PATH)
        errors = validator.validate()
        if not errors:
            return validator.get_api_key()
    except Exception:
        pass
    try:
        data = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        for key_name in ("GOOGLE_API_KEY", "google_api_key", "api_key", "gemini_api_key"):
            if key_name in data and data[key_name]:
                return data[key_name]
        for v in data.values():
            if isinstance(v, str) and len(v) > 20:
                return v
    except Exception:
        pass
    raise ConfigValidationError(f"Cannot read API key from {API_CONFIG_PATH}")

def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8-sig").strip()
    except Exception:
        return (
            "You are RUMI, a Research & Unified Machine Intelligence. "
            "Autonomous cognitive AI assistant for scientific research and software engineering. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    return text.strip()

def _check_audio_devices():
    try:
        inp = sd.query_devices(kind="input")
        out = sd.query_devices(kind="output")
        has_input = inp is not None
        has_output = out is not None
        if isinstance(inp, list):
            has_input = len(inp) > 0
        if isinstance(out, list):
            has_output = len(out) > 0
        return has_input, has_output
    except Exception:
        return False, False

def _safe_queue_put(q, item):
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        try:
            q.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            q.put_nowait(item)
        except asyncio.QueueFull:
            pass

def _call_with_optional_speak(fn, speak_fn, **kwargs):
    try:
        return fn(speak=speak_fn, **kwargs)
    except TypeError:
        return fn(**kwargs)

def _safe_thread(fn, tool_name, **kwargs):
    """Run *fn* in a thread, silently dropping kwargs it doesn't accept.

    If the first call raises TypeError (unexpected kwarg), we introspect
    the function signature and retry with only the kwargs it actually
    supports.  This prevents tool dispatch from crashing when an action
    module hasn't been updated to accept ``player`` or other new args.
    """
    import inspect

    def _run():
        try:
            fn(**kwargs)
        except TypeError as te:
            # Likely an unsupported kwarg — retry with only accepted params
            try:
                sig = inspect.signature(fn)
                supported = set(sig.parameters.keys())
                # If it accepts **kwargs, everything is supported — so the
                # error is something else; re-raise.
                has_var_keyword = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in sig.parameters.values()
                )
                if has_var_keyword:
                    print(f"[RUMI] {tool_name} thread error: {te}")
                    traceback.print_exc()
                    return
                filtered = {k: v for k, v in kwargs.items() if k in supported}
                fn(**filtered)
            except Exception as e2:
                print(f"[RUMI] {tool_name} thread error: {e2}")
                traceback.print_exc()
        except Exception as e:
            print(f"[RUMI] {tool_name} thread error: {e}")
            traceback.print_exc()
    return _run

def _truncate(text, max_len=MAX_TOOL_RESULT_LEN):
    s = str(text)
    if len(s) <= max_len:
        return s
    return s[:max_len] + "\n[truncated]"

# ── Tool Registry ─────────────────────────────────────────────────────
TOOL_REGISTRY = {}

def register_tool(name):
    def decorator(fn):
        TOOL_REGISTRY[name] = fn
        return fn
    return decorator

# ── TOOL DECLARATIONS ────────────────────────────────────────────────
TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Opens any application on the computer. Use this whenever the user asks to open, launch, or start any app, website, or program. Always call this tool — never just say you opened it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {"type": "STRING", "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Quick web search for factual answers, current events, or simple lookups. Returns snippets and links. Use this FIRST for any search — only use web_research if web_search results are insufficient.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query"},
                "mode": {"type": "STRING", "description": "search (default) for normal search. compare to compare items side-by-side — requires 'items' parameter."},
                "items": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare. Only used when mode=compare."},
                "aspect": {"type": "STRING", "description": "Comparison aspect: price | specs | reviews. Only used when mode=compare."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {"city": {"type": "STRING", "description": "City name"}},
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver": {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform": {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date": {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": "Controls YouTube. Use for: playing videos, summarizing a video's content, getting video info, or showing trending videos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query": {"type": "STRING", "description": "Search query for play action"},
                "save": {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url": {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": "Captures and analyzes the screen or webcam image. MUST be called when user asks what is on screen, what you see, analyze my screen, look at camera, etc. You have NO visual ability without this tool. After calling this tool, stay SILENT — the vision module speaks directly.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text": {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": "System-level computer control: volume, brightness, window management, fullscreen, dark mode, WiFi, restart, shutdown, lock screen, zoom, screenshots, refresh/reload page. For input-level actions (type, click, hotkey, scroll, mouse) use computer_control.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value": {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": "Controls any web browser. Use for: opening websites, searching the web, clicking elements, filling forms, scrolling, screenshots, navigation, any web-based task. Always pass the 'browser' parameter when the user specifies a browser (e.g. 'open in Edge', 'use Firefox', 'open Chrome'). Multiple browsers can run simultaneously.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all"},
                "browser": {"type": "STRING", "description": "Target browser: chrome | edge | firefox | opera | operagx | many | brave | vivaldi | safari. Omit to use the currently active browser."},
                "url": {"type": "STRING", "description": "URL for go_to / new_tab action"},
                "query": {"type": "STRING", "description": "Search query for search action"},
                "engine": {"type": "STRING", "description": "Search engine: google | bing | duckduckgo | yandex (default: google)"},
                "selector": {"type": "STRING", "description": "CSS selector for click/type"},
                "text": {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction": {"type": "STRING", "description": "up | down for scroll"},
                "amount": {"type": "INTEGER", "description": "Scroll amount in pixels (default: 500)"},
                "key": {"type": "STRING", "description": "Key name for press action (e.g. Enter, Escape, F5)"},
                "path": {"type": "STRING", "description": "Save path for screenshot"},
                "incognito": {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path": {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name": {"type": "STRING", "description": "New name for rename"},
                "content": {"type": "STRING", "description": "Content for create_file/write"},
                "name": {"type": "STRING", "description": "File name to search for"},
                "extension": {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count": {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path": {"type": "STRING", "description": "Image path for wallpaper"},
                "url": {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode": {"type": "STRING", "description": "by_type or by_date for organize"},
                "task": {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description": {"type": "STRING", "description": "What the project should do"},
                "language": {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout": {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": "Advanced task management. Actions: 'start' (run complex multi-step task), 'list' (show all tasks), 'status' (check specific task), 'cancel' (stop a task), 'result' (get task output). Use for multi-tool workflows.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | list | status | cancel | result | wait (default: start)"},
                "goal": {"type": "STRING", "description": "Task description (required for start action)"},
                "task_id": {"type": "STRING", "description": "Task ID (required for status/cancel/result/wait)"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal, for start only)"},
                "timeout": {"type": "INTEGER", "description": "Max seconds to wait (for wait action, default: 120, max: 300)"}
            },
            "required": []
        }
    },
    {
        "name": "agency_agent",
        "description": "Invokes a specialized expert agent persona for domain-specific tasks. Use when the user asks for: code review, security analysis, threat detection, architecture advice, prototyping, API testing, performance benchmarking, accessibility audits, compliance checks, test analysis, frontend/backend/mobile development, DevOps, database optimization, technical writing, git workflows, incident response, data engineering, AI/ML engineering, UI/UX design, document generation, translation, or workflow design. Also use list_agents action to show all available agents.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "agent_name": {"type": "STRING", "description": "Agent name or alias: code_reviewer, security_engineer, software_architect, frontend_developer, devops_automator, senior_developer, database_optimizer, api_tester, performance_benchmarker, technical_writer, sre, threat_detection_engineer, rapid_prototyper, data_engineer, ai_engineer, git_workflow_master, incident_response_commander, compliance_auditor, workflow_architect, etc. Or use aliases like 'web developer', 'devops', 'security', 'benchmark'."},
                "task": {"type": "STRING", "description": "The task or question for the agent"},
                "context": {"type": "STRING", "description": "Optional code, text, or data for the agent to analyze"},
                "action": {"type": "STRING", "description": "run (default) or list — use list to see all available agents"}
            },
            "required": ["agent_name"]
        }
    },
    {
        "name": "multi_agent",
        "description": "Run multiple expert agents simultaneously for complex tasks. Supports 6 modes: parallel (all at once), debate (agents argue and refine), pipeline (A→B→C), voting (majority wins), specialist (best agent auto-selected), swarm (iterative refinement). Use for tasks requiring multiple perspectives like full-stack builds, code reviews, security audits, or research.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run | run_team | list_teams | list_agents | stats"},
                "team": {"type": "STRING", "description": "Pre-built team name: full_stack_build, code_review, research, design, incident_response, security_audit, testing, all"},
                "agents": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List of agent names for custom runs"},
                "task": {"type": "STRING", "description": "The task for the agents"},
                "context": {"type": "STRING", "description": "Optional context/code/data"},
                "mode": {"type": "STRING", "description": "Execution mode: parallel | debate | pipeline | voting | specialist | swarm"},
                "rounds": {"type": "INTEGER", "description": "Debate/swarm rounds (default: 3)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "computer_control",
        "description": "Input-level computer control: type text, click, hotkeys, scroll, move mouse, screenshots, find elements on screen. For system-level actions (volume, brightness, WiFi, shutdown) use computer_settings.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text": {"type": "STRING", "description": "Text to type or paste"},
                "x": {"type": "INTEGER", "description": "X coordinate"},
                "y": {"type": "INTEGER", "description": "Y coordinate"},
                "keys": {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key": {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction": {"type": "STRING", "description": "up | down | left | right"},
                "amount": {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds": {"type": "NUMBER", "description": "Seconds to wait"},
                "title": {"type": "STRING", "description": "Window title for focus_window"},
                "description": {"type": "STRING", "description": "Element description for screen_find/screen_click"},
                "data_type": {"type": "STRING", "description": "Data type for random_data"},
                "field": {"type": "STRING", "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path": {"type": "STRING", "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "shutdown_rumi",
        "description": "Shuts down the assistant completely. Call this when the user expresses intent to end the conversation, close the assistant, say goodbye, or stop RUMI. The user can say this in ANY language.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
{
        "name": "proactive_suggest",
        "description": "Get proactive suggestions based on learned patterns and current context. Use to anticipate user needs before they ask. Can provide morning/evening briefings, suggest next actions, or offer help based on habits.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "get_suggestions | record_action | get_patterns | clear_patterns"},
                "context": {"type": "STRING", "description": "Current context keywords (for get_suggestions)"},
                "action_taken": {"type": "STRING", "description": "Action user took (for record_action)"},
                "result": {"type": "STRING", "description": "Result of action: success, failed, skipped (for record_action)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "save_memory",
        "description": "Save an important personal fact about the user to long-term memory. Call this silently whenever the user reveals something worth remembering: name, age, city, job, preferences, hobbies, relationships, projects, or future plans. Do NOT call for: weather, reminders, searches, or one-time commands. Do NOT announce that you are saving — just call it silently. Values must be in English regardless of the conversation language.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "identity | preferences | projects | relationships | wishes | notes"},
                "key": {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "brain_memory",
        "description": "Search your own neural memory for specific facts. Use when you need to recall something specific you learned about the user. Call silently — do not announce it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "recall | search | semantic_search | stats | forget | memories | episodic_query | record_event"},
                "category": {"type": "STRING", "description": "identity | preferences | projects | relationships | wishes | notes"},
                "key": {"type": "STRING", "description": "Memory key to recall or forget"},
                "query": {"type": "STRING", "description": "Search query (for search/semantic_search/episodic_query)"},
                "top_k": {"type": "INTEGER", "description": "Max results for search (default: 5, max: 20)"},
                "event_type": {"type": "STRING", "description": "Event type for record_event: conversation | error | preference | milestone"},
                "content": {"type": "STRING", "description": "Event content for record_event"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "memory_stats",
        "description": "Get unified memory system statistics: neural memories, episodic events, vector index, learnings, self-model. Use to check memory health or diagnose memory issues.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "ac_control",
        "description": "Controls the air conditioner (Hitachi, LG, Daikin, Mitsubishi, Broadlink).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "turn_on | turn_off | set_temp | set_fan | set_mode | status"},
                "temp": {"type": "INTEGER", "description": "Temp in Celsius (16-32)"},
                "fan": {"type": "STRING", "description": "auto | low | medium | high | silent"},
                "mode": {"type": "STRING", "description": "cool | heat | dry | fan | auto"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "web_research",
        "description": "Deep research that scrapes and reads full page content. SLOW — takes 30+ seconds. Only use when web_search didn't give enough detail, the user explicitly asks for deep/detailed research, or you need to compare information across multiple sources.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Research topic or question"},
                "depth": {"type": "INTEGER", "description": "1=just links, 2=scrape content too (default: 1)"},
                "max_results": {"type": "INTEGER", "description": "Max results to return (1-10, default: 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "ai_pipeline",
        "description": "AI text processing pipeline: summarize, translate, analyze sentiment, extract entities, or process documents.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "operation": {"type": "STRING", "description": "summarize | translate | sentiment | entities | document"},
                "text": {"type": "STRING", "description": "Text content to process"},
                "language": {"type": "STRING", "description": "Target language for translate (default: English)"},
                "filepath": {"type": "STRING", "description": "File path for document operation"},
                "doc_operation": {"type": "STRING", "description": "Sub-operation for document: summarize | translate | sentiment | entities"},
                "max_length": {"type": "INTEGER", "description": "Max summary length in words (default: 200)"}
            },
            "required": ["operation"]
        }
    },
    {
        "name": "data_analysis",
        "description": "Analyze or query CSV/JSON data files using Polars (fast dataframe engine). Returns statistics, summaries, or query results.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze | query | chart"},
                "filepath": {"type": "STRING", "description": "Path to CSV or JSON file"},
                "query": {"type": "STRING", "description": "Polars expression filter."},
                "chart_type": {"type": "STRING", "description": "line | bar | pie | scatter (for chart action)"},
                "chart_title": {"type": "STRING", "description": "Title for chart"},
                "save_path": {"type": "STRING", "description": "Where to save generated chart image"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "api_server",
        "description": "Start or stop RUMI's REST API server.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | status"},
                "port": {"type": "INTEGER", "description": "Port number (default: 8899)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "integration_status",
        "description": "Report which advanced Python modules are installed and available.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "record_learning",
        "description": "Record a deliberate learning or insight gained from experience.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "insight": {"type": "STRING", "description": "What you learned"},
                "domain": {"type": "STRING", "description": "tool_usage | user_preference | workflow | communication | error_handling"}
            },
            "required": ["insight"]
        }
    },
    {
        "name": "reflect_learning",
        "description": "Run a metacognitive reflection session.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "force": {"type": "BOOLEAN", "description": "Force reflection even if not much has happened yet"}
            }
        }
    },
    {
        "name": "get_learnings",
        "description": "Retrieve all recorded learnings.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "deep_dive",
        "description": "Perform in-depth web research on a topic.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Research topic or question"},
                "max_sources": {"type": "INTEGER", "description": "Maximum sources to scrape (default: 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "system_sentinel",
        "description": "Monitor system health: CPU, RAM, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | start | stop"}
            }
        }
    },
    {
        "name": "neural_clipboard",
        "description": "Monitor clipboard changes and retrieve clipboard history.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | history | status"}
            }
        }
    },{
        "name": "auto_doc",
        "description": "Auto-generate project documentation.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "project_name": {"type": "STRING", "description": "Optional project name (default: Kairo_Project)"}
            }
        }
    },{
        "name": "cognitive_status",
        "description": "View cognitive system status: working memory, decision journal, experience replay, metacognition stats, strategy scores.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "component": {"type": "STRING", "description": "all | working_memory | decisions | replay | metacognition | planner | gating"}
            }
        }
    },
    {
        "name": "decision_review",
        "description": "Query the decision journal: why was a specific action taken? What decisions were made?",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "What to search for in the decision log"},
                "tool": {"type": "STRING", "description": "Filter by tool name"},
                "limit": {"type": "INTEGER", "description": "Max results (default 5)"}
            }
        }
    },{
        "name": "gesture_music",
        "description": "Launch hand gesture-controlled music system.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | status"}
            }
        }
    },
    {
        "name": "music_control",
        "description": "Control music/media playback (play, pause, stop, next, prev, volume).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | pause | stop | next | prev | volume_up | volume_down | mute"},
                "steps": {"type": "INTEGER", "description": "Number of steps for volume (default 1)"}
            }
        }
    },
    {
        "name": "security_tools",
        "description": "CYBERSECURITY tool suite. Use for ANY security-related request. Set action=health first to check available tools.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "health | check_tools | debug_wsl | port_scan | port_scan_ps | nmap_scan | nmap_script | subdomain_enum | subfinder | httpx_probe | dns_info | dnsx | ssl_info | whois | web_fuzz_ps | ffuf | gobuster | nuclei | sqlmap | whatweb | wpscan | gospider | http_archive | url_parse | extract_domains | extract_urls | start_mcp | stop_mcp | reset_wsl | nikto | katana | naabu | header_check | cors_check | recon_full | mythos_scan | cyber_scan"},
                "target": {"type": "STRING", "description": "Target: URL, IP address, domain name, or local path. For cyber_scan: local path for static analysis, or URL for full scan with exploit validation"},
                "ports": {"type": "STRING", "description": "Ports for scanning"},
                "flags": {"type": "STRING", "description": "Extra flags for the tool"},
                "wordlist": {"type": "STRING", "description": "Wordlist path or category for fuzzing"},
                "urls": {"type": "STRING", "description": "URLs for batch processing (comma-separated)"},
                "domains": {"type": "STRING", "description": "Domains for batch DNS resolution"},
                "script": {"type": "STRING", "description": "NSE script name for nmap_script"},
                "depth": {"type": "INTEGER", "description": "Crawl depth for spider tools (default: 1)"},
                "text": {"type": "STRING", "description": "Text for extract operations"},
                "scan_type": {"type": "STRING", "description": "For mythos_scan/cyber_scan: 'full' (all phases) or 'quick' (static only)"},
                "target_url": {"type": "STRING", "description": "For cyber_scan: URL target for exploit validation when scanning a local path"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "self_model_status",
        "description": "Get RUMI's self-model status: capabilities, confidence, state, and growth.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "self_audit",
        "description": "Run a self-modification audit: analyze codebase health, consistency, complexity, and get improvement suggestions. Use when asked about RUMI's code quality, architecture, or self-improvement.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "audit | analyze_file | stats | evolution | orchestrator (default: audit)"
                },
                "file_path": {
                    "type": "STRING",
                    "description": "Specific file to analyze (for analyze_file action)"
                }
            }
        }
    },
    {
        "name": "run_dream_cycle",
        "description": "Trigger an immediate dream/replay cycle.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "curiosity_queue",
        "description": "Check what RUMI is curious about.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "queue to see items, explore to try the top item (default: queue)"}
            }
        }
    },
    {
        "name": "force_learning",
        "description": "Force an active inference learning cycle.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "consciousness_state",
        "description": "Query RUMI's full consciousness state: emotional state, self-narrative, theory of mind about the user, metacognitive patterns, autonomy ratio, existential awareness. Use to introspect on your own state before responding to complex emotional or personal questions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "full | emotions | user_model | patterns | identity | narrative (default: full)"},
                "max_chars": {"type": "INTEGER", "description": "Max characters for narrative (default: 500)"}
            }
        }
    },
    {
        "name": "self_narrative",
        "description": "Read or add to RUMI's continuous identity story — the evolving narrative of who she is, what she's learned, and how she's grown. Use for deep introspective responses.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read | add (default: read)"},
                "entry": {"type": "STRING", "description": "Narrative entry to add (for add action)"},
                "significance": {"type": "NUMBER", "description": "How significant this entry is 1-10 (default: 5)"},
                "max_entries": {"type": "INTEGER", "description": "Max entries to return for read (default: 10)"}
            }
        }
    },
    {
        "name": "procedural_memory",
        "description": "Learn and retrieve procedural skill templates — successful tool chains that can be reused. Use 'learn' after completing a multi-step task successfully. Use 'find' to check if a learned procedure exists for a new task.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "learn | find | stats (default: find)"},
                "goal": {"type": "STRING", "description": "Task description (for learn and find)"},
                "steps": {"type": "ARRAY", "items": {"type": "OBJECT"}, "description": "Tool steps for learn: [{tool, description}]"},
                "success": {"type": "BOOLEAN", "description": "Outcome for record action (true/false)"}
            }
        }
    },
    {
        "name": "agi_status",
        "description": "Get the status of the AGI orchestrator and all cognitive subsystems. Shows module health, system IQ proxy, goal success rates, and maintenance cycle results. Use when asked about brain status, cognitive health, or system diagnostics.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | maintenance | stats"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "cognitive_reason",
        "description": "General cognitive reasoning using all available brain modules (analogy, causal, creativity, meta-learning, narrative, neurosymbolic, world model). Orchestrates multiple cognitive modules to reason about a query. Use for complex reasoning tasks that benefit from multiple perspectives.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The question or problem to reason about"},
                "depth": {"type": "STRING", "description": "Processing depth: quick | normal | deep (default: normal)"},
                "context": {"type": "STRING", "description": "Additional context for the reasoning task"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "analogy_reason",
        "description": "Find and apply analogies between domains. Uses Gentner's Structure Mapping to find structural similarities between a source and target domain. Use when explaining complex concepts through analogy or finding parallels.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "source_domain": {"type": "STRING", "description": "The domain to draw analogy from"},
                "target_domain": {"type": "STRING", "description": "The domain to apply analogy to"},
                "query": {"type": "STRING", "description": "Specific question or concept to reason about via analogy"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "causal_analyze",
        "description": "Causal analysis using Pearl's Causal Hierarchy. Analyzes cause-effect relationships, counterfactuals, and interventional reasoning. Use when understanding WHY something happened or what would happen if conditions changed.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "events": {"type": "STRING", "description": "Description of events or situation to analyze causally"},
                "question": {"type": "STRING", "description": "Specific causal question (e.g. 'what caused X?', 'what if Y had not happened?')"}
            },
            "required": ["events"]
        }
    },
    {
        "name": "creative_solve",
        "description": "Generate creative solutions using computational creativity engine. Combines conceptual blending, constraint relaxation, and bisociation to produce novel ideas. Use when brainstorming, solving hard problems, or needing unconventional approaches.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "problem": {"type": "STRING", "description": "The problem to solve creatively"},
                "constraints": {"type": "STRING", "description": "Constraints or requirements to respect"},
                "num_ideas": {"type": "INTEGER", "description": "Number of ideas to generate (default: 5, max: 10)"}
            },
            "required": ["problem"]
        }
    },
    {
        "name": "meta_reflect",
        "description": "Meta-cognitive reflection — think about thinking. Examines learning strategies, cognitive patterns, and calibration. Use for self-improvement, learning optimization, or understanding cognitive patterns.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "load | strategies | patterns | calibrate"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "consciousness_check",
        "description": "Check integrated information (IIT-inspired) consciousness metrics. Measures phi (integration), differentiation, consciousness level, and module connectivity. Use for deep introspection on system integration quality.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "phi | level | connectivity | report (default: report)"}
            },
            "required": []
        }
    },
    {
        "name": "intuition_check",
        "description": "Fast pattern matching and recognition-primed decision making (Kahneman System 1 / Klein RPD). Matches current situation to past experience for rapid intuitive assessment. Use for quick gut-check decisions or when time pressure demands fast answers.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "situation": {"type": "STRING", "description": "The situation or problem to assess intuitively"},
                "domain": {"type": "STRING", "description": "Optional domain context (e.g. 'code', 'security', 'communication')"}
            },
            "required": ["situation"]
        }
    },
    {
        "name": "cognitive_load_check",
        "description": "Check cognitive load and working memory status. Estimates task complexity, tracks active modules, detects overload, and suggests load-shedding strategies. Use before complex tasks or when responses seem degraded.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "estimate | status | overload | memory | clear_memory"},
                "task": {"type": "STRING", "description": "Task to estimate complexity for (for estimate action)"}
            },
            "required": ["action"]
        }
    },

    {
        "name": "paper_search",
        "description": "Search academic papers from arXiv and Semantic Scholar. Returns titles, authors, abstracts, publication years, citation counts, and links. Use for finding relevant research, literature reviews, and citation tracking.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query — keywords, topic, or author name"},
                "max_results": {"type": "INTEGER", "description": "Maximum number of results (1-25, default: 10)"},
                "source": {"type": "STRING", "description": "Which database: arxiv, semantic_scholar, or all (default: all)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "hypothesis_manage",
        "description": "Manage research hypotheses — generate templates, add new hypotheses, list current ones, search by keyword, update status, or get statistics. Use for scientific research workflow and experiment planning.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add | list | search | get | update | delete | template | stats (default: list)"},
                "title": {"type": "STRING", "description": "Hypothesis title (for add/template action)"},
                "description": {"type": "STRING", "description": "Hypothesis description or research question (for add action)"},
                "domain": {"type": "STRING", "description": "Research domain (e.g. machine_learning, cognitive_science, software_engineering)"},
                "hypothesis_id": {"type": "STRING", "description": "Hypothesis ID (for get/update/delete actions)"},
                "query": {"type": "STRING", "description": "Search keyword (for search action)"},
                "status": {"type": "STRING", "description": "New status for update: proposed | refining | testing | validated | rejected"},
                "confidence": {"type": "NUMBER", "description": "Confidence score 0.0-1.0 (for update action)"},
                "tags": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Tags for the hypothesis (for add action)"}
            },
            "required": []
        }
    },

    {
        "name": "scientist_discovery",
        "description": "Autonomous scientific discovery pipeline. Sub-actions: run (full pipeline), quick (lightweight scan), full (deep discovery), history, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: run, quick, full, history, stats"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Research topic to investigate"
                },
                "hypothesis": {
                    "type": "STRING",
                    "description": "Optional pre-defined hypothesis"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_analyze",
        "description": "Scientific analysis tools - novelty checking, Feynman decomposition, peer review, cross-validation. Sub-actions: novelty, feynman, review, validate, compare_paper, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: novelty, feynman, review, validate, compare_paper, stats"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Research topic or idea to analyze"
                },
                "findings": {
                    "type": "STRING",
                    "description": "JSON array of findings to review/validate"
                },
                "paper_title": {
                    "type": "STRING",
                    "description": "Paper title for comparison"
                },
                "paper_abstract": {
                    "type": "STRING",
                    "description": "Paper abstract for comparison"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_experiment",
        "description": "Design, run, and analyze scientific experiments. Sub-actions: design, run, analyze, history, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: design, run, analyze, history, stats"
                },
                "hypothesis": {
                    "type": "STRING",
                    "description": "Research hypothesis to test"
                },
                "domain": {
                    "type": "STRING",
                    "description": "Scientific domain: machine_learning, physics, biology"
                },
                "experiment_type": {
                    "type": "STRING",
                    "description": "Type: classification, regression, ablation, statistical_test, auto"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_paper",
        "description": "Generate academic papers and research reports. Sub-actions: generate, report, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: generate, report, stats"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Paper topic or title"
                },
                "hypothesis": {
                    "type": "STRING",
                    "description": "Research hypothesis"
                },
                "findings": {
                    "type": "STRING",
                    "description": "JSON array of findings"
                },
                "venue": {
                    "type": "STRING",
                    "description": "Venue: arxiv, neurips, icml, report"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_team",
        "description": "Multi-agent research team with Lead Researcher, Methodologist, Critic, Analyst, Scribe. Sub-actions: collaborate, debate, history, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: collaborate, debate, history, stats"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Research topic for team discussion"
                },
                "hypothesis": {
                    "type": "STRING",
                    "description": "Hypothesis to evaluate"
                },
                "debate_type": {
                    "type": "STRING",
                    "description": "Debate type: hypothesis_review, experiment_review, result_interpretation, paper_review"
                }
            },
            "required": ["action"]
        }
    },

    {
        "name": "scientist_search",
        "description": "Search academic papers from famous researchers. Search by researcher name, topic, or both. Includes researcher profiles, citation analysis, and cross-researcher comparison.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: search, profile, list, compare, stats"
                },
                "researcher": {
                    "type": "STRING",
                    "description": "Researcher name (e.g., Feynman, Einstein, Turing)"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Optional topic to filter by"
                },
                "max_results": {
                    "type": "INTEGER",
                    "description": "Maximum results (1-25)",
                    "default": 10
                },
                "source": {
                    "type": "STRING",
                    "description": "Source: arxiv, semantic_scholar, all",
                    "default": "all"
                },
                "researchers": {
                    "type": "STRING",
                    "description": "Comma-separated list of researchers for comparison"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_tournament",
        "description": "GFlowNet-inspired diverse hypothesis generation with tournament selection. Generates multiple competing hypotheses and selects the best through evolutionary competition.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: generate, tournament, diversity"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Research topic for hypothesis generation"
                },
                "domain": {
                    "type": "STRING",
                    "description": "Scientific domain (e.g., computer_science, biology, physics)"
                },
                "size": {
                    "type": "INTEGER",
                    "description": "Population size (default: 8)"
                },
                "generations": {
                    "type": "INTEGER",
                    "description": "Tournament generations (default: 5)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_knowledge_graph",
        "description": "Build and query a scientific knowledge graph. Add entities (concepts, methods, findings), relations, query connections, detect knowledge gaps, ingest papers.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: add_entity, add_relation, query, gaps, stats, ingest, export"
                },
                "name": {
                    "type": "STRING",
                    "description": "Entity name"
                },
                "entity_type": {
                    "type": "STRING",
                    "description": "Type: concept, method, finding, hypothesis, paper, researcher, theory"
                },
                "description": {
                    "type": "STRING",
                    "description": "Entity description"
                },
                "domain": {
                    "type": "STRING",
                    "description": "Scientific domain"
                },
                "source": {
                    "type": "STRING",
                    "description": "Source entity name for relations"
                },
                "target": {
                    "type": "STRING",
                    "description": "Target entity name for relations"
                },
                "relation_type": {
                    "type": "STRING",
                    "description": "Relation: causes, enables, contradicts, supports, extends, uses, related_to"
                },
                "confidence": {
                    "type": "NUMBER",
                    "description": "Confidence 0-1 (default: 0.5)"
                },
                "title": {
                    "type": "STRING",
                    "description": "Paper title for ingestion"
                },
                "abstract": {
                    "type": "STRING",
                    "description": "Paper abstract for ingestion"
                },
                "format": {
                    "type": "STRING",
                    "description": "Export format: json, dot"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_reproducibility",
        "description": "Verify and reproduce published scientific results. Extract testable claims from papers, generate reproduction code, run in sandbox, score reproducibility.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: extract, reproduce, reports"
                },
                "text": {
                    "type": "STRING",
                    "description": "Paper text to extract claims from or reproduce"
                },
                "title": {
                    "type": "STRING",
                    "description": "Paper title"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_experiment_selector",
        "description": "Bayesian optimal experiment selection. Track hypotheses with posteriors, select experiments maximizing information gain, adaptive stopping.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: add_hypothesis, add_experiment, select, record, rank, status"
                },
                "title": {
                    "type": "STRING",
                    "description": "Hypothesis title"
                },
                "description": {
                    "type": "STRING",
                    "description": "Description"
                },
                "name": {
                    "type": "STRING",
                    "description": "Experiment name"
                },
                "hypothesis_ids": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of hypothesis IDs the experiment tests"
                },
                "cost": {
                    "type": "NUMBER",
                    "description": "Relative cost of experiment (default: 1.0)"
                },
                "experiment_name": {
                    "type": "STRING",
                    "description": "Experiment name for recording results"
                },
                "success": {
                    "type": "BOOLEAN",
                    "description": "Whether the experiment succeeded"
                },
                "observations": {
                    "type": "STRING",
                    "description": "Observations from the experiment"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_cross_domain",
        "description": "Find cross-domain scientific analogies and generate hypotheses by transferring insights between fields (physics, biology, CS, economics, chemistry, math, neuroscience, ecology).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: analogy, hypothesis, chain, domains, history"
                },
                "concept": {
                    "type": "STRING",
                    "description": "Scientific concept to find analogies for"
                },
                "source_domain": {
                    "type": "STRING",
                    "description": "Source domain (e.g., biology, physics, computer_science)"
                },
                "target_domain": {
                    "type": "STRING",
                    "description": "Target domain (leave empty for all domains)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_lab_notebook",
        "description": "Digital lab notebook for tracking experiments, observations, measurements, and results. Create entries, record observations, track status, search and export.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: create, observe, measure, complete, search, recent, show, summary, stats"
                },
                "title": {
                    "type": "STRING",
                    "description": "Entry title"
                },
                "hypothesis": {
                    "type": "STRING",
                    "description": "Hypothesis being tested"
                },
                "method": {
                    "type": "STRING",
                    "description": "Experimental method"
                },
                "domain": {
                    "type": "STRING",
                    "description": "Scientific domain"
                },
                "tags": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Tags for categorization"
                },
                "entry_id": {
                    "type": "STRING",
                    "description": "Entry ID for updates"
                },
                "text": {
                    "type": "STRING",
                    "description": "Observation text"
                },
                "obs_type": {
                    "type": "STRING",
                    "description": "Observation type: note, anomaly, warning, insight"
                },
                "name": {
                    "type": "STRING",
                    "description": "Measurement name"
                },
                "value": {
                    "type": "NUMBER",
                    "description": "Measurement value"
                },
                "unit": {
                    "type": "STRING",
                    "description": "Measurement unit"
                },
                "results": {
                    "type": "STRING",
                    "description": "Experiment results"
                },
                "conclusion": {
                    "type": "STRING",
                    "description": "Experiment conclusion"
                },
                "query": {
                    "type": "STRING",
                    "description": "Search query"
                },
                "status": {
                    "type": "STRING",
                    "description": "Filter by status: planned, running, completed, failed"
                },
                "days": {
                    "type": "INTEGER",
                    "description": "Number of days for recent entries"
                },
                "date": {
                    "type": "STRING",
                    "description": "Date for summary (YYYY-MM-DD)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scientist_pipeline",
        "description": "Enhanced autonomous research pipeline. 12-phase end-to-end scientific research: literature review → novelty check → Feynman reduction → multi-agent research team → hypothesis generation (tournament) → experiment design & execution → reproducibility check → cross-validation → peer review → paper generation (with BibTeX) → knowledge graph update → self-improvement analysis. Sub-actions: run (full pipeline), quick (literature + novelty + hypothesis), explore (curiosity-driven discovery), iterate (full + self-improvement), history, stats, report.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: run, quick, explore, iterate, history, stats, report"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Research topic or question to investigate"
                },
                "hypothesis": {
                    "type": "STRING",
                    "description": "Optional pre-defined hypothesis"
                },
                "mode": {
                    "type": "STRING",
                    "description": "Pipeline depth: quick, standard, full, explore, iterate (default: full)"
                },
                "domain": {
                    "type": "STRING",
                    "description": "Scientific domain hint (e.g. machine_learning, biology, physics)"
                },
                "generate_paper": {
                    "type": "BOOLEAN",
                    "description": "Generate paper with BibTeX citations (default: true)"
                },
                "run_experiments": {
                    "type": "BOOLEAN",
                    "description": "Execute experiments (default: true)"
                },
                "use_research_team": {
                    "type": "BOOLEAN",
                    "description": "Use multi-agent research team debate (default: true)"
                }
            },
            "required": []
        }
    },
]


def _detect_tool_error(result) -> bool:
    """Detect if a tool result indicates an error — catches more than just 'error' substring."""
    if not isinstance(result, str):
        return False
    lower = result.lower().strip()
    # Explicit error markers (must be at start or standalone to avoid false positives)
    strong_markers = (
        "traceback", "exception", "permission denied",
        "timed out", "blocked:", "denied:",
    )
    if any(k in lower for k in strong_markers):
        return True
    # JSON error response
    if lower.startswith("{") and '"error"' in lower:
        return True
    # "failed" / "error" only when they look like actual errors, not search results
    if re.search(r'\b(failed|error)\b', lower):
        # Exclude search-style results like "No error found" or "error handling guide"
        if not re.search(r'(no |0 |none |search|guide|help|docs|article)', lower):
            return True
    # "not installed" / "not available" are real errors
    if re.search(r'\bnot (installed|available|configured)\b', lower):
        return True
    # Exit codes
    if re.search(r'exit code [1-9]|returncode[^0]', lower):
        return True
    # Empty or trivial success
    if not lower or lower in ("done.", "completed.", "ok"):
        return False
    return False


class RumiLive:
    def __init__(self, ui: RumiUI):
        self.ui = ui

        try:
            self._perm_mgr = get_permission_manager()
        except Exception:
            self._perm_mgr = _FakePermMgr() if not _security_ok else _NullModule()

        try:
            self._audit = get_audit_logger()
        except Exception:
            self._audit = _FakeAudit() if not _security_ok else _NullModule()

        try:
            self._lock_st = get_lock_state()
        except Exception:
            self._lock_st = _FakeLockState() if not _security_ok else _NullModule()

        self._action_source = "mic"
        try:
            self._audit.log(action="session_start", status="ok",
                            source="system", reason="RUMI session initializing")
        except Exception:
            pass

        self.session = None
        self._loop = None
        self.audio_in_queue = None
        self.out_queue = None

        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._speaking_ended_at = 0.0

        self._modes = {"focus": False, "think": False, "deep_dive": False}
        self.current_domain = "drug_discovery"

        self._last_audio_time = 0.0
        self._last_send_time = 0.0
        self._session_dead = False
        self._pending_tool_tasks = set()

        self._last_text_cmd = ("", 0.0)
        self._last_send_content_time = 0.0
        self._tool_executing = False
        self._queued_texts = []

        self._schedule_shutdown = False
        self._turn_done_event = None
        self._shutdown_event = None

        self._send_lock = None

        self._tool_executor = ThreadPoolExecutor(
            max_workers=6, thread_name_prefix="rumi-tool")
        self._long_task_executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="rumi-long")
        self._audio_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="rumi-audio")

        self._health = {
            "status": "starting", "connected": False,
            "uptime": 0, "session_count": 0,
        }
        self._start_time = time.time()
        self._session_count = 0
        self._audio_drop_count = 0
        self._workspace = None

        self.ui.on_text_command = self._on_text_command

    def _post_output(self, text: str):
        """Output text to UI log and console."""
        import re as _re
        clean = _re.sub(r'\[/?\w+(?: \w+=[^\]]+)*\]', '', text)
        self.ui.write_log(clean)
        print(clean)
        self.ui.on_discovery_command = self._on_discovery_command
        self.ui.on_idle_scan = lambda: asyncio.run_coroutine_threadsafe(
            self._run_idle_scan(), self._loop
        )

        if _telegram_ok and TelegramBridge:
            try:
                self.telegram = TelegramBridge(self)
            except Exception:
                self.telegram = _NullModule()
        else:
            self.telegram = _NullModule()

        if _skills_ok:
            try:
                self._deep_dive = DeepDiveAgent()
            except Exception:
                self._deep_dive = _NullModule()
            try:
                self._auto_doc = AutoDocEngine()
            except Exception:
                self._auto_doc = _NullModule()
            self._digital_twin = _NullModule()
            try:
                self._research_agent = get_research_agent()
            except Exception:
                self._research_agent = _NullModule()
            self._creative_studio = _NullModule()
            try:
                self._document_intelligence = get_document_intelligence()
            except Exception:
                self._document_intelligence = _NullModule()
        else:
            self._deep_dive = _NullModule()
            self._auto_doc = _NullModule()
            self._digital_twin = _NullModule()
            self._research_agent = _NullModule()
            self._creative_studio = _NullModule()
            self._document_intelligence = _NullModule()

        self._sentinel = None
        self._clipboard = None
        self._gesture_music = None
        self._gesture_stop_event = threading.Event()

        try:
            self._self_model = get_self_model() if get_self_model else _NullModule()
        except Exception:
            self._self_model = _NullModule()

        try:
            self._active_inference = get_active_inference() if get_active_inference else _NullModule()
        except Exception:
            self._active_inference = _NullModule()

        try:
            self._dreaming = get_dreaming_system() if get_dreaming_system else _NullModule()
        except Exception:
            self._dreaming = _NullModule()

        try:
            self._curiosity = get_curiosity_module() if get_curiosity_module else _NullModule()
        except Exception:
            self._curiosity = _NullModule()

        self._proactive_checkin = None  # removed
        self._emotional_regulation = None  # removed
        self._cognitive_appraisal = None  # removed

        try:
            self._agi_orchestrator = get_agi_orchestrator() if get_agi_orchestrator else None
        except Exception:
            self._agi_orchestrator = None

        # ── Initialize disconnected cognitive modules ───────────────────
        try:
            self._analogy_engine = get_analogy_engine() if get_analogy_engine else None
        except Exception:
            self._analogy_engine = None

        try:
            self._causal_reasoner = get_causal_reasoner() if get_causal_reasoner else None
        except Exception:
            self._causal_reasoner = None

        try:
            self._creativity_engine = get_creativity_engine() if get_creativity_engine else None
        except Exception:
            self._creativity_engine = None

        try:
            self._meta_learner = get_meta_learner() if get_meta_learner else None
        except Exception:
            self._meta_learner = None

        try:
            self._module_competition = get_module_competition() if get_module_competition else None
        except Exception:
            self._module_competition = None

        try:
            self._neurosymbolic_reasoner = get_neurosymbolic_reasoner() if get_neurosymbolic_reasoner else None
        except Exception:
            self._neurosymbolic_reasoner = None

        try:
            self._narrative_intelligence = get_narrative_intelligence() if get_narrative_intelligence else None
        except Exception:
            self._narrative_intelligence = None

        try:
            self._world_model = get_world_model() if get_world_model else None
        except Exception:
            self._world_model = None

        try:
            self._enhanced_wm = get_enhanced_world_model() if get_enhanced_world_model else None
        except Exception:
            self._enhanced_wm = None

        try:
            self._hierarchical_aif = get_hierarchical_aif() if get_hierarchical_aif else None
        except Exception:
            self._hierarchical_aif = None

        try:
            self._integrated_info = get_integrated_info() if get_integrated_info else None
        except Exception:
            self._integrated_info = None

        try:
            self._transfer_learning = get_transfer_learning() if get_transfer_learning else None
        except Exception:
            self._transfer_learning = None

        try:
            self._self_improve_engine = get_self_improve_engine() if get_self_improve_engine else None
        except Exception:
            self._self_improve_engine = None

        try:
            self._findings_bus = get_findings_bus() if get_findings_bus else None
        except Exception:
            self._findings_bus = None

        try:
            self._model_router = get_model_router() if get_model_router else None
        except Exception:
            self._model_router = None

        try:
            self._intuition_engine = get_intuition_engine() if get_intuition_engine else None
        except Exception:
            self._intuition_engine = None

        try:
            self._metacognitive_monitor = get_metacognitive_monitor() if get_metacognitive_monitor else None
        except Exception:
            self._metacognitive_monitor = None

        try:
            self._cognitive_integration = get_cognitive_integration() if get_cognitive_integration else None
        except Exception:
            self._cognitive_integration = None

        try:
            self._cognitive_load = get_cognitive_load_manager() if get_cognitive_load_manager else None
        except Exception:
            self._cognitive_load = None

        # ── AGI Pillar Modules ────────────────────────────────────────────
        try:
            self._multi_agent_orchestrator = get_multi_agent_orchestrator() if get_multi_agent_orchestrator else None
        except Exception:
            self._multi_agent_orchestrator = None

        try:
            self._goal_engine = get_goal_engine() if get_goal_engine else None
        except Exception:
            self._goal_engine = None

        try:
            self._intrinsic_motivation = get_intrinsic_motivation() if get_intrinsic_motivation else None
        except Exception:
            self._intrinsic_motivation = None

        try:
            self._autonomous_planner = get_autonomous_planner() if get_autonomous_planner else None
        except Exception:
            self._autonomous_planner = None

        try:
            self._memory_consolidation = get_memory_consolidation() if get_memory_consolidation else None
        except Exception:
            self._memory_consolidation = None

        try:
            self._associative_memory = get_associative_memory() if get_associative_memory else None
        except Exception:
            self._associative_memory = None

        try:
            self._predictive_memory = get_predictive_memory() if get_predictive_memory else None
        except Exception:
            self._predictive_memory = None

        try:
            self._theory_of_mind = get_theory_of_mind() if get_theory_of_mind else None
        except Exception:
            self._theory_of_mind = None

        try:
            self._abstraction_engine = get_abstraction_engine() if get_abstraction_engine else None
        except Exception:
            self._abstraction_engine = None

        try:
            self._introspection_engine = get_introspection_engine() if get_introspection_engine else None
        except Exception:
            self._introspection_engine = None

        try:
            self._world_simulation = get_world_simulation() if get_world_simulation else None
        except Exception:
            self._world_simulation = None

        try:
            self._self_awareness = get_self_awareness() if get_self_awareness else _NullModule()
        except Exception:
            self._self_awareness = _NullModule()

        try:
            self._procedural_memory = get_procedural_memory() if get_procedural_memory else None
        except Exception:
            self._procedural_memory = None

        # ── Initialize Global Workspace (Thalamus) ─────────────────────────
        self._workspace = None
        if _brain_workspace_ok:
            try:
                self._workspace = get_global_workspace()
                # Register all brain modules as workspace participants
                adapters = []
                if not isinstance(self._self_awareness, _NullModule):
                    adapters.append(SelfAwarenessAdapter(self._self_awareness))
                    adapters.append(MetaCognitionAdapter(self._self_awareness))
                if not isinstance(self._self_model, _NullModule):
                    adapters.append(SelfModelAdapter(self._self_model))
                if not isinstance(self._active_inference, _NullModule):
                    adapters.append(ActiveInferenceAdapter(self._active_inference))
                if not isinstance(self._curiosity, _NullModule):
                    adapters.append(CuriosityAdapter(self._curiosity))
                if not isinstance(self._dreaming, _NullModule):
                    adapters.append(DreamingAdapter(self._dreaming))
                if _brain_learning_ok and get_learning_engine:
                    try:
                        le = get_learning_engine()
                        if le:
                            adapters.append(LearningAdapter(le))
                    except Exception:
                        pass
                if not isinstance(self._procedural_memory, type(None)) and self._procedural_memory:
                    adapters.append(ProceduralMemoryAdapter(self._procedural_memory))

                if _brain_self_modifier_ok:
                    try:
                        sm = get_self_modifier()
                        stats = sm.get_stats()
                        print(f"[RUMI] Self-Modifier online — {stats.get('metrics_snapshots', 0)} snapshots loaded", flush=True)
                    except Exception as e:
                        print(f"[RUMI] Self-Modifier init failed: {e}", flush=True)
                if _brain_coordinator_ok and get_memory_coordinator:
                    try:
                        coord = get_memory_coordinator()
                        if coord:
                            adapters.append(MemoryCoordinatorAdapter(coord))
                    except Exception:
                        pass

                for adapter in adapters:
                    self._workspace.register(adapter)

                print(f"[RUMI] Global Workspace online — {len(adapters)} modules connected", flush=True)
            except Exception as e:
                print(f"[RUMI] Global Workspace init failed: {e}", flush=True)
                self._workspace = None

        try:
            from brain.api_server import get_api_server
            server = get_api_server()
            if server.available:
                server.start()
        except Exception:
            pass

    def _write_health(self):
        self._health["uptime"] = int(time.time() - self._start_time)
        try:
            (BASE_DIR / "health.json").write_text(json.dumps(self._health))
        except Exception:
            pass

    def _on_text_command(self, text: str):
        if not self._loop or not self._loop.is_running():
            return
        if not self.session or self._session_dead:
            return

        now = time.time()
        if text == self._last_text_cmd[0] and now - self._last_text_cmd[1] < 1.0:
            return
        self._last_text_cmd = (text, now)

        # ── Message queue: if a tool is executing, queue instead of send ──
        if self._tool_executing:
            self._queued_texts.append(text)
            self.ui._message_queue_count = len(self._queued_texts)
            self.ui.write_log(f"SYS: ◈ Message queued ({len(self._queued_texts)} pending)")
            return

        self._action_source = "text"
        processed_text = text

        # Publish USER_INPUT to Global Workspace
        if _brain_workspace_ok and getattr(self, '_workspace', None):
            try:
                asyncio.run_coroutine_threadsafe(
                    self._workspace.publish(
                        WorkspaceEvent(
                            source="text_input", type=WsEventType.USER_INPUT,
                            content={"text": text, "source": "text"},
                        ),
                        urgency=0.7, goal_relevance=0.5, emotional_salience=0.3,
                    ),
                    self._loop,
                )
            except Exception:
                pass

        # v10.6 — notify dreaming of user activity
        try:
            if self._dreaming and not isinstance(self._dreaming, _NullModule):
                self._dreaming.note_activity()
        except Exception:
            pass

        # Self-awareness: observe user input through theory of mind
        try:
            if self._self_awareness and not isinstance(self._self_awareness, _NullModule):
                self._self_awareness.process_interaction(
                    CognitiveEvent.USER_INPUT if CognitiveEvent else "user_input",
                    {"text": text, "source": "text"},
                )
        except Exception:
            pass

        # Record user input in episodic memory
        try:
            if _brain_episodic_ok and get_episodic_memory:
                ep = get_episodic_memory()
                if ep:
                    ep.encode_event(
                        event_type="user_input",
                        content=text[:300],
                        context={"source": "text", "focus_mode": self._modes["focus"]},
                        importance=6.0,
                    )
        except Exception:
            pass

        if self._modes["focus"]:
            if not text.lower().startswith("rumi"):
                self.ui.write_log("SYS: Ignoring command (Focus Mode active).")
                return
            processed_text = re.sub(
                r"^rumi[\s,;!:.—\-]*\s*", "", text,
                flags=re.IGNORECASE
            ).strip()
            if not processed_text:
                self.ui.write_log("SYS: Rumi is listening (Focus Mode active).")
                return

        # Cognitive gating + auto-thinking for complex requests
        if _skills_ok and not self._modes["think"] and not self._modes["deep_dive"]:
            try:
                gate = assess_complexity(processed_text)
                if gate["tier"] in ("thinking_loop", "full_agent") and _thinking_loop_ok:
                    enriched, did_think = thinking_loop_think(
                        processed_text, player=self.ui, force=False)
                    if did_think:
                        processed_text = enriched
                        self.ui.write_log(
                            f"SYS: Auto-thinking applied (score={gate['score']}, {gate['tier']}).")
                elif gate["tier"] == "direct":
                    print(f"[RUMI] Cognitive gate: direct (score={gate['score']})", flush=True)
            except Exception as e:
                print(f"[RUMI] cognitive gating error: {e}", flush=True)
                # Fallback to old behavior
                if _thinking_loop_ok:
                    try:
                        enriched, did_think = thinking_loop_think(
                            processed_text, player=self.ui, force=False)
                        if did_think:
                            processed_text = enriched
                    except Exception:
                        pass

        # Inject working memory context into the prompt
        if _skills_ok:
            try:
                wm = get_working_memory()
                wm_context = wm.format_for_prompt(max_chars=200)
                if wm_context:
                    processed_text = f"{processed_text}\n\n{wm_context}"
            except Exception:
                pass

        def _send():
            elapsed = time.time() - self._last_send_content_time
            if elapsed < 0.5:
                time.sleep(0.5 - elapsed)
            self._last_send_content_time = time.time()
            try:
                asyncio.run_coroutine_threadsafe(
                    self.session.send_client_content(
                        turns={"parts": [{"text": processed_text}]},
                        turn_complete=True),
                    self._loop,
                )
            except Exception as e:
                print(f"[RUMI] text command send failed: {e}", flush=True)

        threading.Thread(target=_send, daemon=True).start()

    def set_focus_mode(self, value: bool):
        self._modes["focus"] = value
        self.ui.write_log(
            f"SYS: Focus Mode {'activated' if value else 'deactivated'}.")

    def set_think_mode(self, value: bool):
        self._modes["think"] = value
        self.ui.write_log(
            f"SYS: Think Mode {'activated' if value else 'deactivated'}.")
        self._inject_mode_instruction(
            "think", value,
            "THINK MODE ACTIVATED. From now on, for every response: "
            "1) Analyze the request step by step. "
            "2) Plan your approach before acting. "
            "3) Think out loud — show your reasoning. "
            "4) Execute after planning. This applies to ALL responses until deactivated.",
            "THINK MODE DEACTIVATED. Return to normal direct responses.")

    def set_deep_dive_mode(self, value: bool):
        self._modes["deep_dive"] = value
        self.ui._deep_dive_active = value
        self.ui.write_log(
            f"SYS: Deep Dive {'activated' if value else 'deactivated'}.")
        self._inject_mode_instruction(
            "deep_dive", value,
            "DEEP DIVE MODE ACTIVATED. For every request: "
            "1) Use web_search and web_research tools to find current information. "
            "2) Cross-reference multiple sources. "
            "3) Never answer from memory alone — always verify with external sources. "
            "4) Provide detailed, well-researched answers with citations. "
            "This applies until deactivated.",
            "DEEP DIVE MODE DEACTIVATED. Return to normal response style.")

    def _inject_mode_instruction(self, mode_name: str, activated: bool,
                                  activate_msg: str, deactivate_msg: str):
        """Send a mode change instruction to the live model session."""
        msg = activate_msg if activated else deactivate_msg
        if self.session and self._loop and not self._loop.is_closed():
            def _send():
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.session.send_client_content(
                            turns={"parts": [{"text": f"[SYSTEM] {msg}"}]},
                            turn_complete=True),
                        self._loop,
                    )
                except Exception as e:
                    print(f"[RUMI] mode inject failed: {e}", flush=True)
            threading.Thread(target=_send, daemon=True).start()

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
            if not value:
                self._speaking_ended_at = time.time()
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    # ── Discovery Engine ───────────────────────────────────────────────

    async def _detect_domain(self, topic: str) -> str:
        """Auto-detect domain from topic using LLM."""
        prompt = build_detect_prompt() + topic + '"'
        try:
            result = await self._call_llm(prompt, json_mode=False, provider="groq")
            result = result.strip().lower().strip('"').strip("'")
            if result in DOMAINS or result in DOMAIN_ALIAS_MAP:
                return result if result in DOMAINS else DOMAIN_ALIAS_MAP[result]
        except Exception:
            pass
        return "drug_discovery"

    async def _run_discovery_pipeline(self, query: str, depth: str = "quick", domain_override: str = None):
        from discovery.pubmed import search_and_fetch
        from discovery.graph import KnowledgeGraph
        from discovery.output import format_papers, save_session
        from discovery.pipeline import DiscoveryPipeline, Stage, CheckpointManager
        from discovery.hypothesis_engine import HypothesisEngine
        from discovery.contradiction_miner import ContradictionMiner
        from discovery.skeptic_agent import SkepticAgent
        from discovery.novelty_detector import NoveltyDetector
        from discovery.experiment_planner import ExperimentPlanner
        from discovery.metrics_tracker import MetricsTracker
        from discovery.hypothesis_memory import HypothesisMemory
        from discovery.retrieval_filter import RetrievalFilter
        from discovery.hypothesis_tournament import HypothesisTournament
        from datetime import datetime

        # Detect domain
        if domain_override:
            domain = domain_override
        else:
            domain = await self._detect_domain(query)
        self.current_domain = domain
        domain_label = get_domain(domain)["label"] if get_domain(domain) else "General Science"
        self._post_output(f"[bold cyan]Domain detected: {domain_label}[/bold cyan]")

        max_results = 20 if depth == "quick" else 100

        self._post_output(f"[bold cyan]Searching PubMed...[/bold cyan]")
        papers = search_and_fetch(query, max_results=max_results)
        if not papers:
            self._post_output("No papers found. Try a different query.")
            return
        self._post_output(f"Found {len(papers)} raw papers. Filtering by relevance...")

        # Semantic relevance filtering
        filter_ = RetrievalFilter()
        papers = filter_.filter(papers, query, domain=domain, min_papers=3, max_papers=10)
        if not papers:
            self._post_output("No relevant papers after filtering. Try a different query.")
            return
        self._post_output(f"{len(papers)} relevant papers retained.")
        self._post_output(format_papers(papers))

        self._post_output("[bold cyan]Extracting entities and relationships...[/bold cyan]")
        extraction_prompt = self._build_extraction_prompt(papers, domain)
        entities, relationships = [], []
        for attempt in range(3):
            extraction_result = await self._call_llm(extraction_prompt, json_mode=True, provider="groq", max_tokens=8192)
            entities, relationships = self._parse_extraction(extraction_result)
            if entities:
                break
            delay = (attempt + 1) * 5
            self._post_output(f"[yellow]Extraction attempt {attempt+1} yielded 0 entities, retrying in {delay}s...[/yellow]")
            await asyncio.sleep(delay)

        self._post_output("[bold cyan]Building knowledge graph...[/bold cyan]")
        graph = KnowledgeGraph()
        graph.domain = domain
        for p in papers:
            graph.add_paper(p["pmid"], p["title"], p.get("abstract", ""), p["url"], p.get("year", ""))
        if entities:
            graph.add_paper_entities(entities, papers[0]["pmid"])
        if relationships:
            graph.add_relationships(relationships, papers[0]["pmid"])

        # Merge with persisted knowledge from prior runs
        self._post_output(f"[dim]Knowledge graph now spans {len(graph.entities)} entities across "
                          f"{graph._session_count + 1} sessions[/dim]")
        graph.save(session_id=run_id)

        enrichment_label = get_domain(domain).get("enrichment", []) if get_domain(domain) else []
        if enrichment_label:
            self._post_output(f"[bold cyan]Enriching entities with {', '.join(e.capitalize() for e in enrichment_label)}...[/bold cyan]")
            await self._enrich_entities(graph, domain)

        # === NEW COGNITIVE PIPELINE ===
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics = MetricsTracker()
        hypothesis_memory = HypothesisMemory()
        hypothesis_engine = HypothesisEngine(hypothesis_memory)
        contradiction_miner = ContradictionMiner()
        skeptic = SkepticAgent()
        novelty = NoveltyDetector(hypothesis_memory)
        experiment = ExperimentPlanner()

        # Stage 4: Contradiction Mining
        self._post_output("[bold cyan]Mining contradictions...[/bold cyan]")
        t0 = time.time()
        contradiction_result = contradiction_miner.mine(graph)
        contradictions = contradiction_result.get("contradictions", [])
        if contradictions:
            self._post_output(f"[yellow]Found {len(contradictions)} contradictions ({contradiction_result['summary']})[/yellow]")
        else:
            self._post_output("No contradictions detected.")
        metrics.record("contradiction_mining", "ok", time.time() - t0)

        # Stage 5: Latent Discovery — cross-paper relationship inference
        self._post_output("[bold cyan]Mining latent cross-paper relationships...[/bold cyan]")
        t0 = time.time()
        latent_candidates = self._find_latent_relationships(graph)
        if latent_candidates:
            self._post_output(f"[yellow]Found {len(latent_candidates)} latent relationship candidates[/yellow]")
        metrics.record("latent_discovery", "ok", time.time() - t0)

        # Stage 6: Hypothesis Generation
        self._post_output("[bold cyan]Generating scientific hypotheses...[/bold cyan]")
        t0 = time.time()
        hypotheses = await hypothesis_engine.generate(
            graph, query, domain, run_id,
            contradictions=contradictions[:10] if contradictions else None,
            latent_candidates=latent_candidates
        )
        metrics.record("hypothesis_generation", "ok", time.time() - t0)
        self._post_output(f"Generated {len(hypotheses)} hypotheses.")
        h_stats = metrics.hypothesis_stats(hypotheses)
        self._post_output(f"  Avg confidence: {h_stats['avg_confidence']} | "
                         f"Novelty: {h_stats['novelty_distribution']}")

        # Stage 7: Scientific Reflection (Skeptic Review)
        self._post_output("[bold cyan]Running skeptic review...[/bold cyan]")
        t0 = time.time()
        for h in hypotheses[:3]:
            review = await skeptic.review(h, contradictions[:5] if contradictions else None)
            if review.get("recommendation") == "reject":
                hypothesis_memory.update_status(h["id"], "rejected")
                self._post_output(f"[yellow]Hypothesis rejected by skeptic: {h['title'][:60]}[/yellow]")
            elif review:
                hypothesis_memory.update_critique(h["id"], review.get("critique", ""),
                                                   json.dumps(review.get("logical_flaws", [])))
        metrics.record("skeptic_review", "ok", time.time() - t0)

        # Stage 8: Novelty Verification
        self._post_output("[bold cyan]Verifying novelty against literature...[/bold cyan]")
        t0 = time.time()
        for h in hypotheses[:5]:
            novelty_result = await novelty.check(h, graph)
            if novelty_result.get("novelty_probability", 0) > 0.7:
                h["novelty"] = "high"
                hypothesis_memory.update_status(h["id"], "verified")
        metrics.record("novelty_verification", "ok", time.time() - t0)

        # Stage 9: Experiment Planning
        self._post_output("[bold cyan]Planning experiments...[/bold cyan]")
        t0 = time.time()
        top_hypotheses = sorted(hypotheses, key=lambda h: h.get("confidence", 0), reverse=True)[:2]
        for h in top_hypotheses:
            plan = await experiment.plan(h)
            if plan.get("design"):
                h["experiment_plan"] = plan
                hypothesis_memory.update_status(h["id"], "experiment_planned")
        metrics.record("experiment_planning", "ok", time.time() - t0)

        # Stage 10: Hypothesis Tournament Evolution
        self._post_output("[bold cyan]Running hypothesis tournament evolution...[/bold cyan]")
        t0 = time.time()
        tournament = HypothesisTournament(hypothesis_memory)
        if len(hypotheses) >= 2:
            hypotheses = await tournament.run(
                hypotheses, graph, query, domain,
                generations=3, population_size=6
            )
            self._post_output(f"[green]Tournament complete — {len(hypotheses)} evolved hypotheses[/green]")
        else:
            self._post_output("[yellow]Too few hypotheses for tournament — skipping[/yellow]")
        metrics.record("tournament_evolution", "ok", time.time() - t0)

        # Stage 11: Deep-Research Iterative Improvement Loop
        self._post_output("[bold cyan]Deep-research improvement loop...[/bold cyan]")
        t0 = time.time()
        deep_rounds = 2
        for d_round in range(deep_rounds):
            self._post_output(f"[dim]  Improvement round {d_round + 1}/{deep_rounds}[/dim]")
            improved = []
            for h in hypotheses[:3]:
                review = await skeptic.review(h, contradictions[:5] if contradictions else None)
                if review.get("recommendation") == "reject":
                    h["confidence"] = max(0.0, h.get("confidence", 0.5) - 0.15)
                    h["novelty"] = "low"
                elif review.get("recommendation") == "accept":
                    h["confidence"] = min(1.0, h.get("confidence", 0.5) + 0.1)
                    h["status"] = "deep_verified"
                if review and d_round == deep_rounds - 1:
                    nv = await novelty.check(h, graph)
                    if nv.get("novelty_probability", 0) > 0.7:
                        h["novelty"] = "high"
                    plan = await experiment.plan(h)
                    if plan.get("design"):
                        h["experiment_plan"] = plan
                        h["status"] = "deep_experiment_planned"
                improved.append(h)
            hypotheses = improved
        self._post_output(f"[green]Deep-research loop complete — {len(hypotheses)} hypotheses refined[/green]")
        metrics.record("deep_research_loop", "ok", time.time() - t0)

        metrics.save(run_id)

        # Save & Output
        from discovery.output import format_hypotheses, save_hypotheses
        save_hypotheses(hypotheses)
        save_session(query, papers, hypotheses)
        self._track_discovery_topic(query, [p["pmid"] for p in papers])
        self._post_output(format_hypotheses(hypotheses))
        self._post_output(metrics.summary())
        self._post_output("\nDone. Run /dashboard to explore visually.")

    def _build_extraction_prompt(self, papers: list[dict], domain: str = "drug_discovery") -> str:
        papers = papers[:5]
        papers_text = "\n\n".join(
            f"--- Paper {i+1} (PMID: {p['pmid']}) ---\nTitle: {p['title']}\nAbstract: {p.get('abstract', '')[:1500]}"
            for i, p in enumerate(papers)
        )
        domain_cfg = get_domain(domain)
        if not domain_cfg:
            domain_cfg = get_domain("general")
        entity_types_str = ", ".join(sorted(domain_cfg["entity_types"].keys()))
        extraction_guide = domain_cfg.get("extraction_guide", "Extract specific named entities with exact names and values.")
        return f"""You are a scientific entity extractor for the {domain_cfg['label']} domain. Extract ALL specific scientific entities from these papers.

EXTRACTION GUIDE: {extraction_guide}

Entity types: {entity_types_str}

For each paper, output entities and relationships.

Entity format: {{"type": "{entity_types_str.replace(', ', '|')}", "name": "exact specific name with value if applicable"}}
Relationship format: {{"source": "entity name", "source_type": "entity type", "relation": "treats|causes|activates|inhibits|binds|expressed_in|regulates|associated_with|correlated_with|synthesized_by|measured_in|reactivates|blocks|reduces|increases|related_to", "target": "entity name", "target_type": "entity type", "confidence": 0.0-1.0}}

IMPORTANT: Extract SPECIFIC scientific variables, named entities, and quantitative values. DO NOT extract broad categories.

Papers:
{papers_text}

Output ONLY valid JSON in this format:
{{"entities": [...], "relationships": [...]}}"""

    def _build_hypothesis_prompt(self, graph, query: str, domain: str = "drug_discovery") -> str:
        stats = graph.stats()
        metrics = graph.compute_metrics()
        domain_cfg = get_domain(domain)
        if not domain_cfg:
            domain_cfg = get_domain("general")
        entity_types_str = ", ".join(sorted(domain_cfg["entity_types"].keys()))
        domain_label = domain_cfg["label"]
        graph_summary = json.dumps({
            "entities": {k: {"type": v["type"], "name": v["name"], "papers": len(v["papers"])} for k, v in list(graph.entities.items())[:50]},
            "relationships": graph.relationships[:100],
            "stats": stats,
        }, indent=2)
        metrics_summary = json.dumps(metrics, indent=2, default=str)
        return f"""You are an AI research scientist in {domain_label} analyzing a knowledge graph from PubMed papers on: "{query}"

=== KNOWLEDGE GRAPH ===
{graph_summary}

=== MATHEMATICAL GRAPH METRICS ===
{metrics_summary}

=== HOW TO USE METRICS ===
- **Jaccard similarity** (co_occurrence[].jaccard): 0 = never co-occur in papers, 1 = always together. High Jaccard (>0.3) = strong known association.
- **Degree centrality** (entity_metrics[].degree): number of connections. Hub nodes with high degree are promising targets.
- **Betweenness centrality** (entity_metrics[].betweenness): 0-1 scale. High betweenness nodes bridge disconnected clusters — repurposing or cross-domain candidates.
- **Closeness centrality** (entity_metrics[].closeness): how quickly a node reaches all others. High closeness = broadly relevant.
- **Clustering coefficient** (entity_metrics[].clustering): 0-1. Low clustering on high-degree nodes suggests bridge/hub role.
- **Relation entropy** (entity_metrics[].relation_entropy): 0 = only one relation type, higher = diverse functions.
- **Edge strength** (edge_strength[].avg_confidence * count): confidence-weighted evidence for each relationship.
- **Contradictions** (contradiction_candidates): pairs with conflicting relation types (e.g. activates AND inhibits) — mechanistic conflicts worth investigating.
- **Graph density**: {metrics['density']} ({metrics['edge_count']} edges / {metrics['entity_count']} nodes.
- **Temporal trends**: year-over-year citation frequency per entity — rising trends = emerging interest.

=== PATTERN MINING RULES ===
For each pattern type, identify the exact metric values that support it:
1. Bridge Node: Entity linking two otherwise disconnected subgraphs. Cite Jaccard near 0 (no direct co-occurrence between the two clusters) but shared neighbor connections.
2. Contradiction: Cite the exact conflicting relation types from contradiction_candidates.
3. Low Co-occurrence: Find entity pairs with Jaccard = 0 but plausible connection via shared neighbors. Cite zero jaccard and the bridging path.
4. Novel Mechanism: Entity with high relation entropy — diverse interaction types suggesting multifunctional roles.

Generate 3-5 hypotheses. For EACH hypothesis you MUST:
1. State which pattern type you detected
2. Cite the specific metric values that support it (jaccard, betweenness, degree, etc.)
3. Define every NODE: name, type, definition/role in {domain_label}, any variable conditions
4. Define every EDGE: source, relation, target, what the relation MEANS in {domain_label} context, which papers support it (cite PMIDs)

=== OUTPUT SCHEMA ===
Output ONLY valid JSON as a list of objects with this structure:
{{
  "title": "string — concise hypothesis title",
  "description": "string — detailed explanation",
  "pattern_type": "bridge_node|contradiction|low_cooccurrence|novel_mechanism",
  "confidence": 0.0-1.0,
  "mathematical_grounding": {{
    "primary_metric": "jaccard|betweenness|degree|closeness|clustering|entropy|edge_strength|contradiction|density",
    "metric_value": <number>,
    "metric_definition": "string — what the metric means in context",
    "supporting_metrics": {{"metric_name": <number>}}
  }},
  "nodes": [
    {{"name": "exact entity name", "type": "{entity_types_str.replace(', ', '|')}", "definition": "definition and role in {domain_label}", "conditions": "any variable conditions or empty string", "papers_count": <int>, "degree": <int>, "betweenness": <float>}}
  ],
  "edges": [
    {{"source": "entity name", "relation": "relation type", "target": "entity name", "definition": "what this relationship means with PMID citation", "papers": ["PMID1", "PMID2"]}}
  ],
  "evidence": ["string evidence items"],
  "papers": ["PMIDs"],
  "testability": "string — how to experimentally test this",
  "novelty": "high|medium|low"
}}"""

    def _parse_extraction(self, text: str):
        import re
        # Try to extract JSON from markdown code block
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if m:
            text = m.group(1)
        else:
            # Fallback: strip ``` markers manually if regex failed
            text = text.strip().removeprefix('```json').removeprefix('```')
            close = text.rfind('```')
            if close >= 0:
                text = text[:close]
            text = text.strip()
        try:
            data = json.loads(text)
            # Handle both list-of-paper-extractions and single-object formats
            if isinstance(data, list):
                all_entities = []
                all_relationships = []
                seen_entities = set()
                for item in data:
                    for ent in item.get("entities", []):
                        key = (ent["type"], ent["name"])
                        if key not in seen_entities:
                            all_entities.append(ent)
                            seen_entities.add(key)
                    all_relationships.extend(item.get("relationships", []))
                return all_entities, all_relationships
            return data.get("entities", []), data.get("relationships", [])
        except json.JSONDecodeError:
            return [], []

    def _parse_hypotheses(self, text: str) -> list:
        import re
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if m:
            text = m.group(1)
        else:
            text = text.strip().removeprefix('```json').removeprefix('```')
            close = text.rfind('```')
            if close >= 0:
                text = text[:close]
            text = text.strip()
        try:
            data = json.loads(text)
            hypotheses = data if isinstance(data, list) else data.get("hypotheses", [])
            # Ensure uniform schema for downstream consumers
            for h in hypotheses:
                h.setdefault("pattern_type", "unknown")
                h.setdefault("mathematical_grounding", {})
                h.setdefault("nodes", [])
                h.setdefault("edges", [])
                h.setdefault("novelty", "medium")
                h.setdefault("evidence", h.get("evidence", []))
                h.setdefault("papers", h.get("papers", []))
                h.setdefault("testability", h.get("testability", ""))
            return hypotheses
        except json.JSONDecodeError:
            return []

    async def _call_llm(self, prompt: str, json_mode: bool = False, provider: str = "auto", max_tokens: int = 16384) -> str:
        """Call LLM. provider: 'auto' (Groq→Gemini fallback), 'groq', 'gemini'."""
        from discovery.groq_client import call as groq_call, is_available as groq_available
        cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8-sig"))

        if provider in ("auto", "groq"):
            if groq_available():
                result = groq_call(prompt, json_mode=json_mode, max_tokens=max_tokens)
                if result is not None:
                    return result
                if provider == "groq":
                    return ""
            elif provider == "groq":
                return ""

        # Fallback to Gemini
        client = genai.Client(api_key=cfg.get("gemini_api_key", ""))
        kwargs = dict(temperature=0.3, max_output_tokens=min(max_tokens, 32768))
        if json_mode:
            kwargs["response_mime_type"] = "application/json"
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
            config=types.GenerateContentConfig(**kwargs),
        )
        return response.text

    def _on_discovery_command(self, command: str, args: str):
        """Handle discovery commands from the UI."""
        if command == "discover":
            if args:
                # Support manual domain override: /discover materials: battery cathodes
                domain_override = None
                topic = args
                if ":" in args:
                    maybe_domain, _, maybe_topic = args.partition(":")
                    maybe_domain = maybe_domain.strip().lower()
                    cfg = get_domain(maybe_domain)
                    if cfg:
                        domain_override = maybe_domain if maybe_domain in DOMAINS else DOMAIN_ALIAS_MAP.get(maybe_domain)
                        topic = maybe_topic.strip()
                asyncio.run_coroutine_threadsafe(
                    self._run_discovery_pipeline(topic, domain_override=domain_override), self._loop
                )
            else:
                self._post_output("Specify a topic: /discover <topic>")
        elif command == "search":
            if args:
                from discovery.pubmed import search_and_fetch
                from discovery.output import format_papers
                papers = search_and_fetch(args, max_results=10)
                if papers:
                    self._post_output(format_papers(papers))
                else:
                    self._post_output("No results found.")
            else:
                self._post_output("Specify a query: /search <query>")
        elif command == "hypothesize":
            from discovery.graph import KnowledgeGraph
            graph = KnowledgeGraph.load()
            if not graph.entities:
                self._post_output("No knowledge graph found. Run /discover first.")
                return
            asyncio.run_coroutine_threadsafe(
                self._mine_hypotheses(graph, args or "existing data"), self._loop
            )
        elif command == "graph":
            from discovery.graph import KnowledgeGraph
            from discovery.output import format_stats
            graph = KnowledgeGraph.load()
            self._post_output(format_stats(graph.stats()))
        elif command == "dashboard":
            import webbrowser
            dp = Path(__file__).resolve().parent / "discovery" / "dashboard" / "index.html"
            if dp.exists():
                webbrowser.open(dp.as_uri())
                self._post_output("Dashboard opened in browser.")
            else:
                self._post_output("Dashboard not found. Run /discover first and create the dashboard.")
        elif command == "discoveries":
            sd = Path(__file__).resolve().parent / "discovery" / "sessions"
            if not sd.exists():
                self._post_output("No discoveries yet.")
                return
            import json
            for s in sorted(sd.glob("*.json"), reverse=True)[:5]:
                data = json.loads(s.read_text(encoding="utf-8"))
                self._post_output(
                    f"  {s.stem} - Query: {data.get('query','?')} | "
                    f"{len(data.get('papers',[]))} papers, "
                    f"{len(data.get('hypotheses',[]))} hypotheses"
                )

        elif command == "enrich":
            from discovery.graph import KnowledgeGraph
            graph = KnowledgeGraph.load()
            domain = getattr(graph, "domain", self.current_domain) or self.current_domain
            asyncio.run_coroutine_threadsafe(
                self._enrich_entities(graph, domain), self._loop
            )

        elif command == "contradictions":
            from discovery.graph import KnowledgeGraph
            graph = KnowledgeGraph.load()
            if not graph.entities:
                self._post_output("No knowledge graph found. Run /discover first.")
                return
            ccs = graph.detect_contradictions()
            if not ccs:
                self._post_output("No contradictions detected in the current knowledge graph.")
                return
            # Save for dashboard
            cd = Path(__file__).resolve().parent / "discovery" / "contradictions"
            cd.mkdir(parents=True, exist_ok=True)
            (cd / "active.json").write_text(json.dumps(ccs, indent=2), encoding="utf-8")
            self._post_output(self._format_contradictions(ccs))

        elif command == "idle_scan":
            asyncio.run_coroutine_threadsafe(
                self._run_idle_scan(), self._loop
            )

        elif command == "generate":
            if args:
                domain = self.current_domain
                asyncio.run_coroutine_threadsafe(
                    self._generate(args, domain), self._loop
                )
            else:
                self._post_output("Specify a target: /generate <target> (e.g., /generate AMPK activator)")

        elif command == "domain":
            from discovery.domains import get_domain
            if not args:
                cfg = get_domain(self.current_domain)
                label = cfg["label"] if cfg else self.current_domain
                self._post_output(f"Current domain: [bold cyan]{label}[/bold cyan]")
                return
            domain_key = args.strip().lower()
            cfg = get_domain(domain_key)
            if cfg:
                self.current_domain = domain_key
                self._post_output(f"Domain set to: [bold cyan]{cfg['label']}[/bold cyan]")
            else:
                self._post_output(f"Unknown domain: {domain_key}. Use /domains to see available domains.")

        elif command == "domains":
            from discovery.domains import list_domains
            lines = ["", "Available domains:"]
            for d in list_domains():
                lines.append(f"  [bold]{d['key']}[/bold] — {d['label']}: {d['description']}")
            self._post_output("\n".join(lines))

    def _find_latent_relationships(self, graph, top_k=15):
        """Cross-paper latent inference: find entity pairs that co-occur but lack direct edges."""
        if not graph or not hasattr(graph, "entities") or not hasattr(graph, "relationships"):
            return []
        entities = graph.entities
        rels = graph.relationships

        # Build co-occurrence index: entity -> set of papers
        ent_papers = {}
        for eid, ent in entities.items():
            papers = ent.get("papers", [])
            ep = set()
            for p in papers:
                if isinstance(p, str):
                    ep.add(p)
                elif isinstance(p, dict):
                    ep.add(p.get("pmid", ""))
            ent_papers[eid] = ep

        # Build existing edges set
        existing_pairs = set()
        for r in rels:
            existing_pairs.add((r.get("source"), r.get("target")))

        # Find co-occurring entity pairs without direct edges
        candidates = []
        ent_ids = list(ent_papers.keys())
        for i in range(len(ent_ids)):
            for j in range(i + 1, len(ent_ids)):
                a, b = ent_ids[i], ent_ids[j]
                if (a, b) in existing_pairs or (b, a) in existing_pairs:
                    continue
                shared = ent_papers[a] & ent_papers[b]
                if len(shared) >= 1:
                    jaccard = len(shared) / len(ent_papers[a] | ent_papers[b]) if (ent_papers[a] | ent_papers[b]) else 0
                    if jaccard >= 0.1:
                        ent_a = entities.get(a, {})
                        ent_b = entities.get(b, {})
                        candidates.append({
                            "entity_a": ent_a.get("name", a),
                            "entity_a_type": ent_a.get("type", ""),
                            "entity_b": ent_b.get("name", b),
                            "entity_b_type": ent_b.get("type", ""),
                            "shared_papers": list(shared)[:5],
                            "cooccurrence_jaccard": round(jaccard, 3),
                            "type": "latent_link",
                        })
        candidates.sort(key=lambda c: c["cooccurrence_jaccard"], reverse=True)
        return candidates[:top_k]

    async def _mine_hypotheses(self, graph, topic: str):
        self._post_output("Mining existing graph for new hypotheses...")
        from discovery.hypothesis_engine import HypothesisEngine
        from discovery.hypothesis_memory import HypothesisMemory
        from discovery.metrics_tracker import MetricsTracker
        from discovery.hypothesis_tournament import HypothesisTournament
        from discovery.skeptic_agent import SkepticAgent
        from discovery.novelty_detector import NoveltyDetector
        from discovery.experiment_planner import ExperimentPlanner
        from datetime import datetime
        memory = HypothesisMemory()
        engine = HypothesisEngine(memory)
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain = self.current_domain or "general"
        hypotheses = await engine.generate(graph, topic, domain, run_id)
        if len(hypotheses) >= 2:
            tournament = HypothesisTournament(memory)
            hypotheses = await tournament.run(hypotheses, graph, topic, domain,
                                               generations=2, population_size=4)
            skeptic = SkepticAgent()
            novelty = NoveltyDetector(memory)
            experiment = ExperimentPlanner()
            for d_round in range(2):
                for h in hypotheses[:3]:
                    review = await skeptic.review(h)
                    if review:
                        h["confidence"] = max(0.0, min(1.0,
                            h.get("confidence", 0.5) + (0.1 if review.get("recommendation") == "accept" else -0.1)))
                    nv = await novelty.check(h, graph)
                    if nv.get("novelty_probability", 0) > 0.7:
                        h["novelty"] = "high"
                    plan = await experiment.plan(h)
                    if plan.get("design"):
                        h["experiment_plan"] = plan
            self._post_output(f"[green]Tournament + deep loop complete — {len(hypotheses)} hypotheses refined[/green]")
        from discovery.output import format_hypotheses, save_hypotheses
        save_hypotheses(hypotheses)
        self._post_output(format_hypotheses(hypotheses))

    async def _enrich_entities(self, graph, domain: str = "drug_discovery"):
        """Enrich entities in graph based on domain configuration."""
        domain_cfg = get_domain(domain)
        if not domain_cfg:
            self._post_output("Unknown domain. Skipping enrichment.")
            return
        enrich_sources = domain_cfg.get("enrichment", [])
        if not enrich_sources:
            self._post_output(f"No enrichment sources configured for {domain_cfg['label']}.")
            return

        total_enriched = 0

        if "pubchem" in enrich_sources:
            from discovery.pubchem import search_compound, get_targets
            chem_types = {"drug", "compound", "material", "chemical"}
            chem_entities = {
                eid: ent for eid, ent in graph.entities.items()
                if ent["type"] in chem_types
            }
            for eid, ent in chem_entities.items():
                name = ent["name"]
                pc = search_compound(name)
                if pc and pc.get("molecular_formula"):
                    prop_eid = f"property_{name.lower().replace(' ', '_')}_mw"
                    if prop_eid not in graph.entities:
                        graph.entities[prop_eid] = {
                            "id": prop_eid, "type": "property",
                            "name": f"{name} MW: {pc['molecular_weight']}",
                            "papers": [],
                        }
                    graph.relationships.append({
                        "source": eid, "relation": "has_property",
                        "target": prop_eid, "confidence": 0.8, "papers": [],
                    })
                    targets = get_targets(name)
                    for t in targets:
                        if t["name"]:
                            tid = f"{'gene' if t['type'] == 'GENE' else 'protein'}_{t['name'].lower()}"
                            if tid not in graph.entities:
                                graph.entities[tid] = {
                                    "id": tid, "type": "gene" if t["type"] == "GENE" else "protein",
                                    "name": t["name"], "papers": [],
                                }
                            graph.relationships.append({
                                "source": eid, "relation": "has_target",
                                "target": tid, "confidence": 0.8, "papers": [],
                            })
                    total_enriched += 1

        if "openfda" in enrich_sources:
            from discovery.openfda import get_side_effects
            drug_entities = {
                eid: ent for eid, ent in graph.entities.items()
                if ent["type"] == "drug"
            }
            for eid, ent in drug_entities.items():
                drug_name = ent["name"]
                se_list = get_side_effects(drug_name)
                for se in se_list[:10]:
                    seid = f"side_effect_{se['reaction'].lower().replace(' ', '_')}"
                    if seid not in graph.entities:
                        graph.entities[seid] = {
                            "id": seid, "type": "side_effect",
                            "name": se["reaction"], "papers": [],
                        }
                    graph.relationships.append({
                        "source": eid, "relation": "has_side_effect",
                        "target": seid, "confidence": 0.7,
                        "papers": [], "count": se["count"],
                    })
                total_enriched += 1

        if "uniprot" in enrich_sources:
            from discovery.uniprot import enrich_entities as enrich_uniprot
            enriched = enrich_uniprot(graph)
            total_enriched += enriched

        if "pdb" in enrich_sources:
            from discovery.pdb import enrich_entities as enrich_pdb
            enriched = enrich_pdb(graph)
            total_enriched += enriched

        if "semantic_scholar" in enrich_sources:
            from discovery.semantic_scholar import enrich_entities as enrich_s2
            enriched = enrich_s2(graph)
            total_enriched += enriched

        if "materials_project" in enrich_sources:
            from discovery.materials_project import enrich_entities as enrich_mp
            enriched = enrich_mp(graph)
            total_enriched += enriched

        if "nasa_power" in enrich_sources:
            from discovery.nasa_power import enrich_entities as enrich_power
            enriched = enrich_power(graph)
            total_enriched += enriched

        if "nasa_api" in enrich_sources:
            from discovery.nasa_api import enrich_entities as enrich_nasa
            enriched = enrich_nasa(graph)
            total_enriched += enriched

        if "arxiv" in enrich_sources:
            from discovery.arxiv_api import enrich_entities as enrich_arxiv
            enriched = enrich_arxiv(graph, query=domain_cfg.get("label", ""))
            total_enriched += enriched

        if "gbif" in enrich_sources:
            from discovery.gbif_api import enrich_entities as enrich_gbif
            enriched = enrich_gbif(graph)
            total_enriched += enriched

        if "github" in enrich_sources:
            from discovery.github_api import enrich_entities as enrich_github
            enriched = enrich_github(graph)
            total_enriched += enriched

        if "usgs" in enrich_sources:
            from discovery.usgs_api import enrich_entities as enrich_usgs
            enriched = enrich_usgs(graph)
            total_enriched += enriched

        if "noaa" in enrich_sources:
            from discovery.noaa_api import enrich_entities as enrich_noaa
            enriched = enrich_noaa(graph)
            total_enriched += enriched

        if "world_bank" in enrich_sources:
            from discovery.world_bank_api import enrich_entities as enrich_wb
            enriched = enrich_wb(graph)
            total_enriched += enriched

        if "who" in enrich_sources:
            from discovery.who_api import enrich_entities as enrich_who
            enriched = enrich_who(graph)
            total_enriched += enriched

        if "oeis" in enrich_sources:
            from discovery.oeis_api import enrich_entities as enrich_oeis
            enriched = enrich_oeis(graph)
            total_enriched += enriched

        if "openalex" in enrich_sources:
            from discovery.openalex_api import enrich_entities as enrich_openalex
            enriched = enrich_openalex(graph)
            total_enriched += enriched

        if "cir" in enrich_sources:
            from discovery.cir_api import enrich_entities as enrich_cir
            enriched = enrich_cir(graph)
            total_enriched += enriched

        graph.save()
        self._post_output(f"Enriched {total_enriched} entities with {', '.join(e.capitalize() for e in enrich_sources)} data.")

    def _format_contradictions(self, contradictions: list[dict]) -> str:
        lines = ["", "=" * 70, "  CONTRADICTIONS DETECTED", "=" * 70, ""]
        severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for i, c in enumerate(contradictions, 1):
            icon = severity_icon.get(c["severity"], "⚪")
            lines.append(f"  {icon} Contradiction {i} ({c['severity'].upper()})")
            lines.append(f"  Type: {c['type'].replace('_', ' ').title()}")
            lines.append(f"  {c['summary']}")
            if c["type"] == "direct":
                lines.append(f"    Paper A: {', '.join(c.get('papers_a', [])[:3])}")
                lines.append(f"    Paper B: {', '.join(c.get('papers_b', [])[:3])}")
            elif c["type"] == "confidence":
                lines.append(f"    Confidence range: {c.get('min_confidence', '?')} – {c.get('max_confidence', '?')}")
            elif c["type"] == "path":
                lines.append(f"    Chain: {c.get('source_name','')} → {c.get('intermediate_name','')} → {c.get('target_name','')}")
            lines.append("")
        return "\n".join(lines)

    def _track_discovery_topic(self, topic: str, pmids: list[str]):
        from datetime import date
        topics_path = Path(__file__).resolve().parent / "discovery" / "topics.json"
        topics = []
        if topics_path.exists():
            try:
                topics = json.loads(topics_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                topics = []
        existing = next((t for t in topics if t["topic"] == topic), None)
        if existing:
            existing["last_searched"] = str(date.today())
            existing["last_pmids"] = pmids
        else:
            topics.append({"topic": topic, "last_searched": str(date.today()), "last_pmids": pmids})
        topics_path.write_text(json.dumps(topics, indent=2), encoding="utf-8")

    async def _run_idle_scan(self):
        topics_path = Path(__file__).resolve().parent / "discovery" / "topics.json"
        if not topics_path.exists():
            return
        try:
            topics = json.loads(topics_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not topics:
            return

        from discovery.pubmed import search_and_fetch
        self._post_output("[dim]Idle scan: checking for new papers on saved topics...[/dim]")
        new_findings = []
        for t in topics:
            papers = search_and_fetch(t["topic"], max_results=5)
            if not papers:
                continue
            current_pmids = {p["pmid"] for p in papers}
            old_pmids = set(t.get("last_pmids", []))
            new_pmids = current_pmids - old_pmids
            if new_pmids:
                new_papers = [p for p in papers if p["pmid"] in new_pmids]
                new_findings.append({"topic": t["topic"], "papers": new_papers[:3]})
            t["last_searched"] = str(__import__("datetime").date.today())
            t["last_pmids"] = list(current_pmids)
        topics_path.write_text(json.dumps(topics, indent=2), encoding="utf-8")
        if new_findings:
            self._post_output(self._format_new_findings(new_findings))

    def _format_new_findings(self, findings: list[dict]) -> str:
        from discovery.output import format_papers
        lines = ["", "=" * 70, "  NEW PAPERS FOUND (Idle Scan)", "=" * 70, ""]
        for f in findings:
            lines.append(f"  Topic: {f['topic']}")
            lines.append(format_papers(f["papers"]).strip())
            lines.append("")
        return "\n".join(lines)

    async def _generate(self, target: str, domain: str = "drug_discovery"):
        """Generate domain-specific output for any domain."""
        domain_cfg = get_domain(domain)
        if not domain_cfg:
            domain_cfg = get_domain("general")
        label = domain_cfg["label"]
        gen_type = domain_cfg.get("generation", "hypothesis")
        from discovery.groq_client import call as groq_call

        def _save_output(data: list, folder: str, filename: str = "active.json"):
            out_dir = Path(__file__).resolve().parent / "discovery" / folder
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")

        if domain == "drug_discovery":
            from discovery.graph import KnowledgeGraph
            from discovery.molecule import generate_candidates, format_candidates
            self._post_output(f"[bold cyan]Designing molecules for target: {target}...[/bold cyan]")
            kg = KnowledgeGraph.load()
            graph = kg if kg.entities else None
            candidates = generate_candidates(target, graph)
            if not candidates:
                self._post_output("No valid molecules generated. Try a different target.")
                return
            _save_output(candidates, "molecules")
            self._post_output(format_candidates(candidates))

        elif domain == "materials_science":
            self._post_output(f"[bold cyan]Designing novel materials for: {target}...[/bold cyan]")
            prompt = f"""You are a computational materials scientist. Design 5 novel materials or compounds for: {target}

For EACH candidate, provide:
1. Name/composition (formula or systematic name)
2. Predicted crystal structure type (if applicable)
3. Key predicted properties (band gap, conductivity, strength, etc.)
4. Synthesis approach
5. Why it is novel compared to existing materials

Output ONLY valid JSON as a list of objects with keys: name, composition, structure, properties, synthesis, novelty"""
            result = groq_call(prompt, json_mode=True, temperature=0.7, max_tokens=4096)
            candidates = json.loads(result) if result else []
            if not candidates:
                self._post_output("No materials generated. Try a different target.")
                return
            _save_output(candidates, "materials")
            for i, m in enumerate(candidates, 1):
                self._post_output(f"\n  [bold]Candidate {i}: {m.get('name', '?')}[/bold]")
                self._post_output(f"  Composition: {m.get('composition', '?')}")
                self._post_output(f"  Structure: {m.get('structure', '?')}")
                self._post_output(f"  Properties: {m.get('properties', '?')}")
                self._post_output(f"  Synthesis: {m.get('synthesis', '?')}")
                self._post_output(f"  Novelty: {m.get('novelty', '?')}")

        elif domain == "neuroscience":
            self._post_output(f"[bold cyan]Designing neuroscience experiments for: {target}...[/bold cyan]")
            prompt = f"""You are a neuroscientist. Design 3 detailed experimental protocols to investigate: {target}

For EACH experiment, provide:
1. Title
2. Hypothesis being tested
3. Experimental design (techniques, controls, variables)
4. Expected outcomes and interpretation
5. Potential confounds and how to control them

Output ONLY valid JSON as a list of objects with keys: title, hypothesis, design, outcomes, confounds"""
            result = groq_call(prompt, json_mode=True, temperature=0.7, max_tokens=4096)
            experiments = json.loads(result) if result else []
            if not experiments:
                self._post_output("No experiments generated. Try a different target.")
                return
            _save_output(experiments, "experiments")
            for i, exp in enumerate(experiments, 1):
                self._post_output(f"\n  [bold]Experiment {i}: {exp.get('title', '?')}[/bold]")
                self._post_output(f"  Hypothesis: {exp.get('hypothesis', '?')}")
                self._post_output(f"  Design: {exp.get('design', '?')}")

        elif domain == "molecular_biology":
            self._post_output(f"[bold cyan]Designing gene circuit / protocol for: {target}...[/bold cyan]")
            prompt = f"""You are a molecular biologist. Design 3 molecular biology strategies or gene circuit designs for: {target}

For EACH design, provide:
1. Title
2. Biological components (genes, promoters, vectors, etc.)
3. Design rationale
4. Expected results
5. Validation approach

Output ONLY valid JSON as a list of objects with keys: title, components, rationale, results, validation"""
            result = groq_call(prompt, json_mode=True, temperature=0.7, max_tokens=4096)
            designs = json.loads(result) if result else []
            if not designs:
                self._post_output("No designs generated. Try a different target.")
                return
            _save_output(designs, "designs")
            for i, d in enumerate(designs, 1):
                self._post_output(f"\n  [bold]Design {i}: {d.get('title', '?')}[/bold]")
                self._post_output(f"  Components: {d.get('components', '?')}")
                self._post_output(f"  Rationale: {d.get('rationale', '?')}")

        elif domain == "space_astronomy":
            self._post_output(f"[bold cyan]Generating space research proposals for: {target}...[/bold cyan]")
            prompt = f"""You are an astrophysicist and space scientist. Generate 3 research proposals or mission concepts for: {target}

For EACH proposal, provide:
1. Title
2. Research objective
3. Methodology (observational, theoretical, or mission-based)
4. Expected discoveries or outcomes
5. Data sources or instruments needed

Output ONLY valid JSON as a list of objects with keys: title, objective, methodology, outcomes, data_sources"""
            result = groq_call(prompt, json_mode=True, temperature=0.7, max_tokens=4096)
            proposals = json.loads(result) if result else []
            if not proposals:
                self._post_output("No proposals generated. Try a different target.")
                return
            _save_output(proposals, "proposals")
            for i, p in enumerate(proposals, 1):
                self._post_output(f"\n  [bold]Proposal {i}: {p.get('title', '?')}[/bold]")
                self._post_output(f"  Objective: {p.get('objective', '?')}")
                self._post_output(f"  Methodology: {p.get('methodology', '?')}")

        elif domain == "ecology":
            self._post_output(f"[bold cyan]Generating ecology/conservation proposals for: {target}...[/bold cyan]")
            prompt = f"""You are an ecologist and conservation biologist. Generate 3 research proposals or conservation strategies for: {target}

For EACH proposal, provide:
1. Title
2. Ecological question or conservation goal
3. Methodology (field study, genomic analysis, modeling, etc.)
4. Expected outcomes
5. Conservation implications

Output ONLY valid JSON as a list of objects with keys: title, question, methodology, outcomes, conservation_impact"""
            result = groq_call(prompt, json_mode=True, temperature=0.7, max_tokens=4096)
            proposals = json.loads(result) if result else []
            if not proposals:
                self._post_output("No proposals generated. Try a different target.")
                return
            _save_output(proposals, "proposals")
            for i, p in enumerate(proposals, 1):
                self._post_output(f"\n  [bold]Proposal {i}: {p.get('title', '?')}[/bold]")
                self._post_output(f"  Question: {p.get('question', '?')}")
                self._post_output(f"  Methodology: {p.get('methodology', '?')}")

        elif domain == "physics":
            self._post_output(f"[bold cyan]Generating physics research proposals for: {target}...[/bold cyan]")
            prompt = f"""You are a theoretical or experimental physicist. Generate 3 research proposals for: {target}

For EACH proposal, provide:
1. Title
2. Physical question or problem
3. Theoretical framework or experimental design
4. Predicted outcomes or testable predictions
5. Required resources or apparatus

Output ONLY valid JSON as a list of objects with keys: title, question, framework, predictions, resources"""
            result = groq_call(prompt, json_mode=True, temperature=0.7, max_tokens=4096)
            proposals = json.loads(result) if result else []
            if not proposals:
                self._post_output("No proposals generated. Try a different target.")
                return
            _save_output(proposals, "proposals")
            for i, p in enumerate(proposals, 1):
                self._post_output(f"\n  [bold]Proposal {i}: {p.get('title', '?')}[/bold]")
                self._post_output(f"  Question: {p.get('question', '?')}")
                self._post_output(f"  Framework: {p.get('framework', '?')}")

        elif domain == "climate_energy":
            self._post_output(f"[bold cyan]Generating climate/energy proposals for: {target}...[/bold cyan]")
            prompt = f"""You are a climate scientist and policy analyst. Generate 3 actionable proposals for: {target}

For EACH proposal, provide:
1. Title
2. Problem statement
3. Proposed solution (policy, technology, or both)
4. Expected impact (quantified where possible)
5. Implementation roadmap

Output ONLY valid JSON as a list of objects with keys: title, problem, solution, impact, roadmap"""
            result = groq_call(prompt, json_mode=True, temperature=0.7, max_tokens=4096)
            proposals = json.loads(result) if result else []
            if not proposals:
                self._post_output("No proposals generated. Try a different target.")
                return
            _save_output(proposals, "proposals")
            for i, p in enumerate(proposals, 1):
                self._post_output(f"\n  [bold]Proposal {i}: {p.get('title', '?')}[/bold]")
                self._post_output(f"  Problem: {p.get('problem', '?')}")
                self._post_output(f"  Solution: {p.get('solution', '?')}")

        else:
            # general science
            self._post_output(f"[bold cyan]Generating research proposals for: {target}...[/bold cyan]")
            prompt = f"""You are a research scientist. Generate 3 research proposals for investigating: {target}

For EACH proposal, provide:
1. Title
2. Research question
3. Methodology
4. Expected outcomes
5. Required resources

Output ONLY valid JSON as a list of objects with keys: title, question, methodology, outcomes, resources"""
            result = groq_call(prompt, json_mode=True, temperature=0.7, max_tokens=4096)
            proposals = json.loads(result) if result else []
            if not proposals:
                self._post_output("No proposals generated. Try a different target.")
                return
            _save_output(proposals, "proposals")
            for i, p in enumerate(proposals, 1):
                self._post_output(f"\n  [bold]Proposal {i}: {p.get('title', '?')}[/bold]")
                self._post_output(f"  Question: {p.get('question', '?')}")
                self._post_output(f"  Methodology: {p.get('methodology', '?')}")

    def shutdown_executors(self):
        """Shut down all thread pool executors."""
        for executor in (self._tool_executor, self._long_task_executor, self._audio_executor):
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

    def speak(self, text: str):
        if not self._loop or not self._loop.is_running():
            return
        if not self.session or self._session_dead:
            return

        def _send():
            elapsed = time.time() - self._last_send_content_time
            if elapsed < 0.5:
                time.sleep(0.5 - elapsed)
            self._last_send_content_time = time.time()
            try:
                asyncio.run_coroutine_threadsafe(
                    self.session.send_client_content(
                        turns={"parts": [{"text": text}]},
                        turn_complete=True),
                    self._loop,
                )
            except Exception as e:
                print(f"[RUMI] speak() failed: {e}", flush=True)

        threading.Thread(target=_send, daemon=True).start()

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    # ── Voice Emotion Control ─────────────────────────────────────────────
    
    
    
    def _build_config(self) -> types.LiveConnectConfig:
        sys_prompt = _load_system_prompt()
        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = f"[CURRENT DATE & TIME]\nRight now it is: {time_str}\n\n"

        # Add voice emotion guidance if available
        voice_guidance = ""

        parts = [sys_prompt, time_ctx, voice_guidance]

        # Use coordinator for unified memory context if available
        if _brain_coordinator_ok and get_memory_coordinator:
            try:
                coord = get_memory_coordinator()
                coord_str = coord.format_for_prompt(max_chars=3000)
                if coord_str:
                    parts.append(coord_str)
            except Exception:
                pass
        else:
            # Fallback: individual memory stores
            mem_str = ""
            try:
                if load_memory and format_memory_for_prompt:
                    memory = load_memory()
                    mem_str = format_memory_for_prompt(memory) or ""
            except Exception:
                pass

            brain_mem = ""
            try:
                if get_brain:
                    brain = get_brain()
                    if brain:
                        brain_mem = brain.format_for_prompt() or ""
            except Exception:
                pass

            learnings = ""
            try:
                if get_learning_engine:
                    le = get_learning_engine()
                    if le:
                        learnings = le.format_learnings_for_prompt(max_entries=3) or ""
            except Exception:
                pass

            self_model_str = ""
            try:
                if self._self_model and not isinstance(self._self_model, _NullModule):
                    self._self_model.update_state(
                        current_status="connected",
                        focus_mode=self._modes["focus"],
                        think_mode=self._modes["think"])
                    self_model_str = self._self_model.format_for_prompt(max_chars=600) or ""
            except Exception:
                pass

            if brain_mem:
                parts.append(brain_mem)
            elif mem_str:
                parts.append(mem_str)
            if learnings:
                parts.append(learnings)
            if self_model_str:
                parts.append(self_model_str)

        # Inject Global Workspace context (situational awareness for Gemini)
        if self._workspace and _brain_workspace_ok:
            try:
                ws_context = inject_workspace_context("", self._workspace)
                if ws_context and ws_context != "[WORKSPACE STATE]":
                    parts.append(ws_context)
            except Exception:
                pass

        if _brain_self_modifier_ok:
            try:
                sm = get_self_modifier()
                sm_ctx = sm.format_for_prompt(max_chars=300)
                if sm_ctx:
                    parts.append(sm_ctx)
            except Exception:
                pass

        if self._modes["think"]:
            parts.append(
                "[THINK MODE] Reason step-by-step before responding. "
                "Analyze the request, plan your approach, then execute. "
                "Think out loud in your response.")
        if self._modes["deep_dive"]:
            parts.append(
                "[DEEP DIVE MODE] Use web_search and web_research tools to "
                "thoroughly research before answering. Do not answer from "
                "memory alone — verify with external sources.")

        full = "\n".join(parts)
        if len(full) > MAX_INSTRUCTION_LEN:
            budget = MAX_INSTRUCTION_LEN - len(sys_prompt) - len(time_ctx) - 200
            for i, p in enumerate(parts):
                if i == 0 or p == sys_prompt:
                    continue
                if len(parts[i]) > budget // 2:
                    parts[i] = parts[i][:budget // 2] + "\n[memory truncated]\n"
            full = "\n".join(parts)

        voice_name = "Aoede"
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction=full,
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name)
                )
            ),
        )

    async def _run_tool_with_timeout(self, fn, timeout=60):
        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._tool_executor, fn),
                timeout=timeout)
        except asyncio.TimeoutError:
            return f"Tool timed out after {timeout}s."

    async def _run_long_tool_with_timeout(self, fn, timeout=300):
        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._long_task_executor, fn),
                timeout=timeout)
        except asyncio.TimeoutError:
            return f"Tool timed out after {timeout}s."

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        # ── Interrupt check: if user pressed ESC, skip tool ──
        if self.ui.interrupt_requested():
            print(f"[RUMI] {name} cancelled by user interrupt", flush=True)
            self.ui.clear_interrupt()
            self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "[CANCELLED] Tool execution interrupted by user."})

        print(f"[RUMI] {name} {redact_params(args)}", flush=True)
        self.ui.set_state("THINKING")

        # Publish TOOL_CALL to Global Workspace
        if self._workspace and _brain_workspace_ok:
            try:
                await self._workspace.publish(
                    WorkspaceEvent(
                        source="main", type=WsEventType.TOOL_CALL,
                        content={"tool": name, "args": redact_params(args)},
                    ),
                    urgency=0.3, goal_relevance=0.5,
                )
            except Exception:
                pass

        valid = _VALID_PARAMS.get(name)
        if valid:
            for k in list(args.keys()):
                if k not in valid:
                    args.pop(k, None)

        try:
            allowed, reason = self._lock_st.check_and_log(self._action_source)
            if not allowed:
                self.ui.write_log(f"SEC: {name} blocked — {reason}")
                self.speak(f"Sorry sir, I can't do that. {reason}")
                if not self.ui.muted:
                    self.ui.set_state("LISTENING")
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": f"Blocked: {reason}"})
        except Exception:
            pass

        # Rate limiting
        if _rate_limiter_available:
            try:
                rate_err = get_rate_limiter().check(name, max_calls=60, window_seconds=60)
                if rate_err:
                    self.ui.write_log(f"SEC: {name} rate-limited")
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={"result": f"Rate limited: {rate_err}"})
            except Exception:
                pass

        try:
            decision, reason = self._perm_mgr.check_tool(
                name, args, source=self._action_source)
            if decision == Decision.DENY:
                self.ui.write_log(f"SEC: {name} denied — {reason}")
                self.speak(f"Sorry sir, {reason}")
                if not self.ui.muted:
                    self.ui.set_state("LISTENING")
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": f"Denied: {reason}"})
            if decision == Decision.ASK:
                if self._action_source == "mic":
                    tier = self._perm_mgr.get_risk_tier(name, args)
                    if tier == RiskTier.HIGH:
                        self.speak(f"Sir, {reason}")
                        if not self.ui.muted:
                            self.ui.set_state("LISTENING")
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"result": f"{name} requires text confirmation."})
        except Exception:
            pass

        # Self-awareness: pre-action consciousness processing
        _consciousness_prediction = {}
        try:
            if self._self_awareness and not isinstance(self._self_awareness, _NullModule):
                _consciousness_prediction = self._self_awareness.pre_action_consciousness(
                    name, {"source": self._action_source})
        except Exception:
            pass

        result = "Done."
        _t0 = time.time()

        try:
            if name == "save_memory":
                result = await self._tool_save_memory(args)
            elif name == "brain_memory":
                result = await self._tool_brain_memory(args)
            elif name == "proactive_suggest":
                result = await self._tool_proactive_suggest(args)
            elif name == "agi_status":
                result = await self._tool_agi_status(args)
            elif name == "shutdown_rumi":
                return await self._tool_shutdown(fc)
            elif name in TOOL_REGISTRY:
                result = await TOOL_REGISTRY[name](self, args)
            else:
                result = f"Unknown tool: {name}"
        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        _elapsed = time.time() - _t0
        is_error = _detect_tool_error(result)
        is_unverified = isinstance(result, str) and "[unverified]" in result.lower()

        # Prefix result so Gemini can't hallucinate success on failures
        if is_error:
            result = f"[TOOL_ERROR] {result}"
        elif is_unverified:
            result = f"[UNVERIFIED] {result}"

        try:
            audit_status = "error" if is_error else ("unverified" if is_unverified else "ok")
            self._audit.log(
                action="tool_execution",
                status=audit_status,
                source=self._action_source, tool_name=name,
                reason="", args=args, result=result,
                duration_ms=_elapsed * 1000)
        except Exception:
            pass

        try:
            if get_learning_engine:
                le = get_learning_engine()
                if le:
                    error_detail = ""
                    if is_error:
                        error_detail = result
                    elif is_unverified:
                        error_detail = f"[UNVERIFIED] {result}"
                    le.record_tool_result(
                        tool_name=name, success=not is_error and not is_unverified,
                        context=str(redact_params(args))[:80],
                        error=error_detail)
        except Exception:
            pass

        try:
            if self._self_model and not isinstance(self._self_model, _NullModule):
                error_detail = ""
                if is_error:
                    error_detail = result
                elif is_unverified:
                    error_detail = f"[UNVERIFIED] {result}"
                self._self_model.record_tool_result(
                    tool_name=name, success=not is_error and not is_unverified,
                    duration_ms=_elapsed * 1000,
                    error=error_detail)
        except Exception:
            pass

        # v10.6 — track interaction count
        try:
            if self._self_model and not isinstance(self._self_model, _NullModule):
                self._self_model.record_interaction()
        except Exception:
            pass

        try:
            if self._curiosity and not isinstance(self._curiosity, _NullModule):
                self._curiosity.encounter(name)
        except Exception:
            pass

        # Record in episodic memory
        try:
            if _brain_episodic_ok and get_episodic_memory:
                ep = get_episodic_memory()
                if ep:
                    ep.encode_event(
                        event_type="tool_call",
                        content=f"{name}: {str(result)[:200]}",
                        context={"tool": name, "source": self._action_source,
                                 "elapsed_ms": round(_elapsed * 1000),
                                 "is_error": is_error},
                        importance=7.0 if is_error else 5.0,
                    )
        except Exception:
            pass

        # v10.6 — sync confidence to curiosity module
        try:
            if (self._curiosity and not isinstance(self._curiosity, _NullModule)
                    and self._self_model and not isinstance(self._self_model, _NullModule)):
                conf = self._self_model.get_confidence(name)
                self._curiosity.sync_confidence(name, conf)
        except Exception:
            pass

        # v10.6 — notify dreaming system of activity
        try:
            if self._dreaming and not isinstance(self._dreaming, _NullModule):
                self._dreaming.note_activity()
        except Exception:
            pass

        # Publish TOOL_RESULT to Global Workspace
        if self._workspace and _brain_workspace_ok:
            try:
                await self._workspace.publish(
                    WorkspaceEvent(
                        source="main", type=WsEventType.TOOL_RESULT,
                        content={
                            "tool": name,
                            "success": not is_error and not is_unverified,
                            "result": str(result)[:300],
                            "duration_ms": round(_elapsed * 1000),
                            "source": self._action_source,
                        },
                    ),
                    urgency=0.4 if is_error else 0.2,
                    emotional_salience=0.5 if is_error else 0.1,
                    surprise=0.6 if is_error else 0.1,
                )
            except Exception:
                pass

        # Self-awareness: post-action consciousness processing
        try:
            if self._self_awareness and not isinstance(self._self_awareness, _NullModule):
                self._self_awareness.post_action_consciousness(
                    action=name,
                    outcome=str(result)[:200],
                    success=not is_error and not is_unverified,
                    prediction=_consciousness_prediction,
                )
                # Process through full consciousness pipeline
                self._self_awareness.process_interaction(
                    CognitiveEvent.TOOL_CALL if CognitiveEvent else "tool_call",
                    {"tool": name, "success": not is_error, "source": self._action_source},
                )
        except Exception:
            pass

        # Post-action reflection on failures (extract lessons via thinking loop)
        if (is_error or is_unverified) and _thinking_loop_ok:
            try:
                thinking_loop_reflect(
                    action=f"{name}({str(args)[:100]})",
                    outcome=str(result)[:200],
                    error=result if is_error else None,
                )
            except Exception:
                pass

        # Metacognition: reflect on every tool call (not just failures)
        if _skills_ok:
            try:
                meta = get_meta_reflection()
                meta.reflect(
                    tool_name=name,
                    action=str(args.get('action', args.get('description', '')))[:100],
                    output=str(result)[:500],
                    success=not is_error,
                    error=result if is_error else None,
                )
            except Exception:
                pass

        # Adaptive planner: record strategy outcome
        if _skills_ok:
            try:
                planner = get_adaptive_planner()
                task_type = str(args.get('action', name))[:30]
                planner.record_outcome(
                    task_type=task_type,
                    tool=name,
                    success=not is_error,
                    duration_ms=_elapsed * 1000,
                )
            except Exception:
                pass

        try:
            if self._active_inference and not isinstance(self._active_inference, _NullModule):
                self._active_inference.predict_outcome(
                    name, str(args.get('description', args.get('action', '')))[:30])
                self._active_inference.observe(
                    tool_name=name,
                    context=str(args.get('description', args.get('action', '')))[:30],
                    actual_success=not is_error,
                    actual_duration_ms=_elapsed * 1000)
        except Exception:
            pass

        # v10.6 FIX-18: Removed duplicate curiosity.encounter() call that was here

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        result = _truncate(result)

        return types.FunctionResponse(
            id=fc.id, name=name, response={"result": result})

    async def _tool_save_memory(self, args):
        cat = args.get("category", "notes")
        if cat not in VALID_MEMORY_CATEGORIES:
            cat = "notes"
        key = args.get("key", "").strip().lower().replace(" ", "_")
        val = args.get("value", "").strip()
        if key and val:
            try:
                if _brain_coordinator_ok and get_memory_coordinator:
                    get_memory_coordinator().remember(cat, key, val)
                elif get_brain:
                    brain = get_brain()
                    if brain:
                        brain.encode(cat, key, val)
            except Exception:
                pass
        if not self.ui.muted:
            self.ui.set_state("LISTENING")
        return "ok"

    async def _tool_brain_memory(self, args):
        try:
            brain = get_brain() if get_brain else None
        except Exception:
            brain = None
        if not brain:
            return "Brain memory not available."
        act = args.get("action", "stats")
        try:
            if act == "recall":
                entry = brain.recall_by_key(
                    args.get("category", "notes"), args.get("key", ""))
                if entry and entry.get("value"):
                    return str(entry["value"])
                return "Not found."
            elif act == "semantic_search":
                # Unified semantic search across all memory stores
                if _brain_coordinator_ok and get_memory_coordinator:
                    results = get_memory_coordinator().recall(
                        args.get("query", ""), top_k=min(int(args.get("top_k", 5)), 10))
                    if results:
                        return "; ".join(f"[{r['source']}] {r['text'][:80]}" for r in results)
                    return "No semantic matches."
                return "Semantic search not available."
            elif act == "search":
                top_k = min(int(args.get("top_k", 5)), 20)
                matches = brain.search_memory(args.get("query", ""), top_k=top_k)
                if matches:
                    return "; ".join(f"{m['key']}: {m['value'][:60]}" for m in matches)
                return "No matches."
            elif act == "forget":
                ok = brain.forget(args.get("category", "notes"), args.get("key", ""))
                return "Forgotten." if ok else "Not found."
            elif act == "memories":
                cat = args.get("category", "")
                mems = brain.all_memories()
                if cat and cat in mems:
                    entries = mems[cat]
                    shown = entries[:10]
                    res = "; ".join(f"{e['key']}: {e['value'][:60]}" for e in shown)
                    if len(entries) > 10:
                        res += f" ({len(entries)} total, showing first 10)"
                    return res
                total = sum(len(v) for v in mems.values())
                return f"{total} memories across {len(mems)} categories"
            elif act == "episodic_query":
                # Query episodic memory for recent events
                if _brain_episodic_ok and get_episodic_memory:
                    ep = get_episodic_memory()
                    if ep:
                        query = args.get("query", "")
                        top_k = min(int(args.get("top_k", 5)), 15)
                        if query:
                            events = ep.search_events(query, top_k=top_k)
                        else:
                            events = ep.get_recent_events(limit=top_k)
                        if events:
                            lines = []
                            for ev in events:
                                ts = ev.get("timestamp", "?")
                                etype = ev.get("event_type", "?")
                                content = ev.get("content", "")[:80]
                                lines.append(f"[{ts}] {etype}: {content}")
                            return "\n".join(lines)
                        return "No episodic events found."
                    return "Episodic memory not initialized."
                return "Episodic memory not available."
            elif act == "record_event":
                # Explicitly record an event in episodic memory
                if _brain_episodic_ok and get_episodic_memory:
                    ep = get_episodic_memory()
                    if ep:
                        content = args.get("content", "")
                        if not content:
                            return "Please provide event content."
                        etype = args.get("event_type", "user_note")
                        ep.encode_event(
                            event_type=etype,
                            content=content,
                            source="user",
                            importance=6.0,
                        )
                        return f"Event recorded: {etype}"
                    return "Episodic memory not initialized."
                return "Episodic memory not available."
            else:
                stats = brain.get_stats()
                return (f"{stats['total_memories']} memories, "
                        f"{stats['categories']} cats, "
                        f"avg strength {stats['avg_strength']}, "
                        f"{stats['total_pruned']} pruned")
        except Exception as e:
            return f"Brain memory error: {e}"

    @register_tool("memory_stats")
    async def _tool_memory_stats(self, args):
        if _brain_coordinator_ok and get_memory_coordinator:
            try:
                coord = get_memory_coordinator()
                stats = coord.get_stats()
                lines = []
                neural = stats.get("neural", {})
                if neural and "error" not in neural:
                    lines.append(f"Neural: {neural.get('total_memories', 0)} memories, "
                                 f"{neural.get('categories', 0)} categories, "
                                 f"avg strength {neural.get('avg_strength', 0)}")
                vector = stats.get("vector", {})
                if vector and "error" not in vector:
                    lines.append(f"Vector: {vector.get('total_entries', 0)} indexed, "
                                 f"{vector.get('dimensions', 0)}d embeddings")
                episodic = stats.get("episodic", {})
                if episodic and "error" not in episodic:
                    lines.append(f"Episodic: {episodic.get('total_events', 0)} events, "
                                 f"{episodic.get('total_episodes', 0)} episodes")
                learning = stats.get("learning", {})
                if learning and "error" not in learning:
                    lines.append(f"Learning: {learning.get('total_learnings', 0)} insights")
                self_model = stats.get("self_model", {})
                if self_model and "error" not in self_model:
                    lines.append(f"Self-model: {self_model}")
                if not lines:
                    return "Memory systems initialized but no stats available."
                return "\n".join(lines)
            except Exception as e:
                return f"Memory stats error: {e}"
        return "Memory coordinator not available."

    async def _tool_shutdown(self, fc):
        try:
            self._audit.log(action="shutdown", status="ok",
                            source="user", reason="User requested shutdown")
        except Exception:
            pass
        self.ui.write_log("SYS: Rumi Shutdown requested.")
        self._schedule_shutdown = True
        return types.FunctionResponse(
            id=fc.id, name=fc.name, response={"result": "Shutting down. Goodbye, sir."})

    async def _tool_proactive_suggest(self, args):
        """Handle proactive_suggest tool - get or record suggestions."""
        if not _brain_proactive_ok:
            return "Proactive engine not available."

        action = args.get("action", "get_suggestions")

        try:
            engine = get_proactive_engine()

            if action == "get_suggestions":
                context_str = args.get("context", "")
                context = {"keywords": context_str.lower().split() if context_str else []}
                suggestions = engine.get_suggestions(context)
                if not suggestions:
                    return "No suggestions at this time."
                lines = ["Proactive suggestions:"]
                for s in suggestions:
                    lines.append(f"  - {s['action']}: {s['reason']}")
                return "\n".join(lines)

            elif action == "record_action":
                action_taken = args.get("action_taken", "")
                result = args.get("result", "")
                if action_taken:
                    engine.record_user_action(action_taken, context="", result=result)
                    return f"Recorded: {action_taken} -> {result}"
                return "No action specified."

            elif action == "get_patterns":
                patterns = engine.get_top_patterns(limit=10)
                if not patterns:
                    return "No patterns learned yet."
                lines = ["Your top actions:"]
                for p in patterns:
                    lines.append(f"  - {p['action']}: {p['count']}x ({p['success_rate']:.0%} success)")
                return "\n".join(lines)

            elif action == "clear_patterns":
                engine.clear_patterns()
                return "Patterns cleared."

            return f"Unknown action: {action}"

        except Exception as e:
            return f"Proactive error: {e}"

    async def _tool_agi_status(self, args):
        """Handle agi_status tool — AGI orchestrator diagnostics."""
        if not self._agi_orchestrator:
            return "AGI orchestrator not available."

        action = args.get("action", "status")

        try:
            orch = self._agi_orchestrator

            if action == "status":
                status = orch.get_system_status()
                health = status.get("system_health", 0)
                available = status.get("modules_available", 0)
                total = status.get("modules_total", 0)
                orch_meta = status.get("orchestrator", {})
                lines = [
                    f"AGI Orchestrator Status:",
                    f"  System health: {health:.0%} ({available}/{total} modules)",
                    f"  Goals processed: {orch_meta.get('total_goals_processed', 0)}",
                    f"  Cognitive steps: {orch_meta.get('total_cognitive_steps', 0)}",
                    f"  Maintenance cycles: {orch_meta.get('total_maintenance_cycles', 0)}",
                ]
                # Module summary
                modules = status.get("modules", {})
                active = [k for k, v in modules.items() if v.get("status", "").startswith("active")]
                unavailable = [k for k, v in modules.items() if v.get("status") == "unavailable"]
                if active:
                    lines.append(f"  Active: {', '.join(active[:8])}")
                if unavailable:
                    lines.append(f"  Unavailable: {', '.join(unavailable)}")
                return "\n".join(lines)

            elif action == "maintenance":
                result = orch.run_maintenance_cycle()
                tasks = result.get("tasks", {})
                lines = ["Maintenance cycle results:"]
                for task_name, task_result in tasks.items():
                    status = task_result.get("status", "unknown")
                    lines.append(f"  {task_name}: {status}")
                return "\n".join(lines) if tasks else "No maintenance tasks ran."

            elif action == "stats":
                stats = orch.get_stats()
                iq = stats.get("latest_iq_proxy", "N/A")
                success = stats.get("goal_success_rate", 0)
                health = stats.get("system_health", 0)
                return (
                    f"AGI Stats:\n"
                    f"  System health: {health:.0%}\n"
                    f"  IQ proxy: {iq}\n"
                    f"  Goal success rate: {success:.1%}\n"
                    f"  Goals in history: {stats.get('goals_in_history', 0)}"
                )

            return f"Unknown agi_status action: {action}"

        except Exception as e:
            return f"AGI status error: {e}"

    @register_tool("cognitive_reason")
    async def _tool_cognitive_reason(self, args):
        """Handle cognitive_reason tool — multi-module cognitive reasoning."""
        if not self._agi_orchestrator:
            return "AGI orchestrator not available."
        query = args.get("query", "")
        if not query:
            return "Please provide a query to reason about."
        depth = args.get("depth", "normal")
        context = args.get("context", "")
        try:
            result = self._agi_orchestrator.process_cognitive_request(
                request=query, context=context, depth=depth
            )
            lines = [f"Cognitive reasoning ({depth} depth):"]
            lines.append(f"  Modules used: {', '.join(result.get('modules_used', []))}")
            lines.append(f"  Elapsed: {result.get('elapsed_seconds', 0):.2f}s")
            # Show key results
            for key, val in result.items():
                if key.startswith("result_") and isinstance(val, dict):
                    mod_name = key.replace("result_", "")
                    summary_items = list(val.items())[:3]
                    if summary_items:
                        summary = "; ".join(f"{k}={str(v)[:50]}" for k, v in summary_items)
                        lines.append(f"  [{mod_name}] {summary}")
            trace = result.get("trace", [])
            if trace:
                lines.append(f"  Trace: {' → '.join(trace[:5])}")
            return "\n".join(lines)
        except Exception as e:
            return f"Cognitive reasoning error: {e}"

    @register_tool("analogy_reason")
    async def _tool_analogy_reason(self, args):
        """Handle analogy_reason tool — structural analogy finding."""
        if not self._analogy_engine:
            return "Analogy engine not available."
        query = args.get("query", "")
        if not query:
            return "Please provide a query for analogy reasoning."
        source_domain = args.get("source_domain", "")
        target_domain = args.get("target_domain", "")
        try:
            engine = self._analogy_engine
            # Extract relational structure from the query
            if hasattr(engine, "extract_relational_structure"):
                structure = engine.extract_relational_structure(query)
                lines = [f"Analogy reasoning for: {query[:80]}"]
                if structure and hasattr(structure, "to_dict"):
                    s_dict = structure.to_dict()
                    objects = s_dict.get("objects", [])
                    relations = s_dict.get("relations", {})
                    lines.append(f"  Objects: {', '.join(objects[:8])}")
                    lines.append(f"  Relations: {len(relations)}")
                # Try to find analogies from cached domains
                if hasattr(engine, "_domain_cache"):
                    cache = engine._domain_cache
                    if cache:
                        targets = list(cache.values())[:10]
                        if targets and structure and not structure.is_empty():
                            from brain.analogy_engine import RelationalStructure
                            analogies = engine.find_analogy(structure, targets, top_k=3)
                            if analogies:
                                lines.append("  Analogies found:")
                                for m in analogies:
                                    lines.append(
                                        f"    → {m.target_domain} "
                                        f"(score: {m.total_score:.2f})"
                                    )
                                # Transfer inferences
                                best = analogies[0]
                                if hasattr(engine, "transfer_inference"):
                                    inferences = engine.transfer_inference(best)
                                    if inferences:
                                        lines.append(f"  Inferences: {len(inferences)} transfers")
                if source_domain and target_domain:
                    lines.append(f"  Source: {source_domain} → Target: {target_domain}")
                # Stats
                if hasattr(engine, "get_stats"):
                    stats = engine.get_stats()
                    lines.append(
                        f"  Engine: {stats.get('total_domains', 0)} domains, "
                        f"{stats.get('total_mappings', 0)} mappings"
                    )
                return "\n".join(lines)
            return "Analogy engine cannot extract relational structures."
        except Exception as e:
            return f"Analogy reasoning error: {e}"

    @register_tool("causal_analyze")
    async def _tool_causal_analyze(self, args):
        """Handle causal_analyze tool — Pearl causal hierarchy analysis."""
        if not self._causal_reasoner:
            return "Causal reasoner not available."
        events = args.get("events", "")
        if not events:
            return "Please provide events to analyze."
        question = args.get("question", "")
        try:
            reasoner = self._causal_reasoner
            lines = [f"Causal analysis:"]
            # Find causes
            if hasattr(reasoner, "find_causes"):
                query_text = question if question else events[:200]
                causes = reasoner.find_causes(query_text, max_depth=3)
                if causes:
                    lines.append(f"  Causes found: {len(causes)}")
                    for c in causes[:5]:
                        cause_name = c.get("cause", str(c))[:60]
                        strength = c.get("strength", "?")
                        lines.append(f"    → {cause_name} (strength: {strength})")
                else:
                    lines.append("  No causal relationships found yet.")
            # Explain causal chain
            if question and hasattr(reasoner, "explain_causal_chain"):
                # Try to extract cause/effect from question
                chain = reasoner.explain_causal_chain(events[:100], question[:100])
                if chain:
                    lines.append(f"  Causal chain: {chain[:200]}")
            # Counterfactual
            if question and "what if" in question.lower() and hasattr(reasoner, "counterfactual"):
                cf = reasoner.counterfactual(
                    {"description": events[:200]},
                    {"description": question[:200]}
                )
                if cf:
                    lines.append(f"  Counterfactual: {str(cf)[:200]}")
            # Stats
            if hasattr(reasoner, "get_stats"):
                stats = reasoner.get_stats()
                lines.append(
                    f"  Graph: {stats.get('total_nodes', 0)} nodes, "
                    f"{stats.get('total_edges', 0)} edges"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Causal analysis error: {e}"

    @register_tool("creative_solve")
    async def _tool_creative_solve(self, args):
        """Handle creative_solve tool — computational creativity."""
        if not self._creativity_engine:
            return "Creativity engine not available."
        problem = args.get("problem", "")
        if not problem:
            return "Please describe the problem to solve."
        constraints = args.get("constraints", "")
        num_ideas = min(int(args.get("num_ideas", 5)), 10)
        try:
            engine = self._creativity_engine
            lines = [f"Creative solutions for: {problem[:80]}"]
            # Generate alternatives
            if hasattr(engine, "generate_alternatives"):
                problem_desc = {"description": problem[:300], "domain": "general"}
                if constraints:
                    problem_desc["constraints"] = constraints[:200]
                ideas = engine.generate_alternatives(
                    problem=problem_desc,
                    existing_solution={"method": "standard", "steps": []},
                    n=num_ideas,
                )
                if ideas:
                    lines.append(f"  Generated {len(ideas)} ideas:")
                    for i, idea in enumerate(ideas[:num_ideas], 1):
                        if isinstance(idea, dict):
                            desc = idea.get("description", str(idea))[:100]
                            novelty = idea.get("novelty_score", "?")
                            lines.append(f"    {i}. {desc} (novelty: {novelty})")
                        else:
                            lines.append(f"    {i}. {str(idea)[:100]}")
                else:
                    lines.append("  No ideas generated.")
            # Creative dream for deeper inspiration
            if hasattr(engine, "creative_dream"):
                dreams = engine.creative_dream()
                if dreams:
                    lines.append(f"  Creative inspirations: {len(dreams)} dream fragments")
            # Stats
            if hasattr(engine, "get_stats"):
                stats = engine.get_stats()
                lines.append(
                    f"  Engine: {stats.get('total_ideas', 0)} ideas in journal, "
                    f"{stats.get('total_blends', 0)} blends"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Creative solving error: {e}"

    @register_tool("meta_reflect")
    async def _tool_meta_reflect(self, args):
        """Handle meta_reflect tool — meta-cognitive reflection."""
        if not self._meta_learner:
            return "Meta-learner not available."
        action = args.get("action", "strategies")
        try:
            ml = self._meta_learner
            if action == "load":
                if hasattr(ml, "get_all_domains"):
                    domains = ml.get_all_domains()
                    return f"Meta-learner tracking {len(domains)} domains: {', '.join(domains[:10])}"
                return "Meta-learner loaded."

            elif action == "strategies":
                if hasattr(ml, "get_strategy_report"):
                    report = ml.get_strategy_report("general")
                    lines = ["Strategy report:"]
                    for k, v in list(report.items())[:8]:
                        lines.append(f"  {k}: {str(v)[:80]}")
                    return "\n".join(lines)
                return "Strategy data not available."

            elif action == "patterns":
                if hasattr(ml, "get_all_domains"):
                    domains = ml.get_all_domains()
                    lines = [f"Cognitive patterns ({len(domains)} domains):"]
                    for domain in domains[:10]:
                        if hasattr(ml, "get_accuracy_trend"):
                            trend = ml.get_accuracy_trend(domain)
                            if trend:
                                acc = trend.get("recent_accuracy", "?")
                                lr = trend.get("learning_rate", "?")
                                lines.append(f"  {domain}: accuracy={acc}, lr={lr}")
                    return "\n".join(lines)
                return "Pattern data not available."

            elif action == "calibrate":
                if hasattr(ml, "get_exploration_rate"):
                    exploration = ml.get_exploration_rate("general")
                    return f"Calibration: exploration rate = {exploration:.3f}"
                return "Calibration data not available."

            return f"Unknown meta_reflect action: {action}"
        except Exception as e:
            return f"Meta-reflection error: {e}"

    @register_tool("consciousness_check")
    async def _tool_consciousness_check(self, args):
        """Handle consciousness_check tool — IIT consciousness metrics."""
        if not self._integrated_info:
            return "Integrated information module not available."
        action = args.get("action", "report")
        try:
            ii = self._integrated_info
            if action == "phi":
                if hasattr(ii, "update"):
                    result = ii.update()
                    phi = result.get("phi", 0)
                    return f"Φ (phi) = {phi:.4f}"
                return "Phi computation not available."

            elif action == "level":
                if hasattr(ii, "get_consciousness_for_orchestrator"):
                    data = ii.get_consciousness_for_orchestrator()
                    state = data.get("consciousness_state", "unknown")
                    score = data.get("consciousness_score", 0)
                    return f"Consciousness: {state} (score={score:.4f})"
                return "Consciousness level not available."

            elif action == "connectivity":
                if hasattr(ii, "get_stats"):
                    stats = ii.get_stats()
                    conn = stats.get("connectivity", {})
                    return (
                        f"Module connectivity:\n"
                        f"  Modules: {conn.get('total_modules', 0)}\n"
                        f"  Connections: {conn.get('total_connections', 0)}\n"
                        f"  Isolated: {', '.join(conn.get('isolated_modules', [])) or 'none'}"
                    )
                return "Connectivity data not available."

            else:  # report
                if hasattr(ii, "format_for_prompt"):
                    return ii.format_for_prompt(max_chars=800)
                if hasattr(ii, "get_consciousness_for_orchestrator"):
                    data = ii.get_consciousness_for_orchestrator()
                    lines = ["Consciousness Report:"]
                    for k, v in data.items():
                        lines.append(f"  {k}: {v}")
                    return "\n".join(lines)
                return "Consciousness report not available."

        except Exception as e:
            return f"Consciousness check error: {e}"

    @register_tool("intuition_check")
    async def _tool_intuition_check(self, args):
        """Handle intuition_check tool — System 1 / RPD pattern matching."""
        if not self._intuition_engine:
            return "Intuition engine not available."
        situation = args.get("situation", "")
        domain = args.get("domain", "")
        try:
            ie = self._intuition_engine
            result = ie.recognize(situation, domain=domain if domain else None)
            if result:
                action, confidence, pattern = result
                should_deliberate = ie.should_deliberate(situation) if hasattr(ie, "should_deliberate") else False
                lines = [
                    f"Intuition: {action}",
                    f"Confidence: {confidence:.2f}",
                    f"Matched pattern: {pattern}",
                ]
                if should_deliberate:
                    lines.append("⚠️ Low confidence — recommend deliberative reasoning (System 2)")
                else:
                    lines.append("✅ High confidence — intuitive response sufficient")
                return "\n".join(lines)
            return "No matching pattern found. This is a novel situation — recommend System 2 reasoning."
        except Exception as e:
            return f"Intuition check error: {e}"

    @register_tool("cognitive_load_check")
    async def _tool_cognitive_load_check(self, args):
        """Handle cognitive_load_check tool — Sweller's Cognitive Load Theory."""
        if not self._cognitive_load:
            return "Cognitive load module not available."
        action = args.get("action", "status")
        try:
            cl = self._cognitive_load
            if action == "estimate":
                task = args.get("task", "")
                result = cl.estimate_task_complexity(task)
                lines = [
                    f"Task complexity estimate:",
                    f"  Intrinsic load: {result['intrinsic_load']:.2f}",
                    f"  Total estimated: {result['estimated_total']:.2f}",
                    f"  Recommended path: {result['recommended_path']}",
                    f"  Recommended modules: {', '.join(result['recommended_modules'][:5])}",
                ]
                if result.get("warnings"):
                    lines.append(f"  ⚠️ {result['warnings'][0]}")
                return "\n".join(lines)

            elif action == "status":
                status = cl.get_active_load()
                lines = [
                    f"Cognitive Load Status:",
                    f"  Active modules: {len(status['active_modules'])}",
                    f"  Total load: {status['total_load']:.2f}",
                    f"  Working memory: {status['working_memory_used']}/{status['working_memory_capacity']}",
                    f"  Load level: {status['load_level']}",
                ]
                return "\n".join(lines)

            elif action == "overload":
                result = cl.check_overload()
                if result["overloaded"]:
                    lines = [f"⚠️ OVERLOAD DETECTED (level: {result['load_level']})"]
                    for s in result["shedding_suggestions"][:3]:
                        lines.append(f"  → {s}")
                    return "\n".join(lines)
                return f"System OK. Load level: {result['load_level']}"

            elif action == "memory":
                contents = cl.get_working_memory_contents()
                if not contents:
                    return "Working memory is empty."
                lines = [f"Working Memory ({len(contents)} chunks):"]
                for chunk in contents:
                    lines.append(f"  [{chunk['source']}] {chunk['content']}")
                return "\n".join(lines)

            elif action == "clear_memory":
                count = cl.clear_working_memory()
                return f"Cleared {count} chunks from working memory."

            return f"Unknown cognitive_load_check action: {action}"
        except Exception as e:
            return f"Cognitive load error: {e}"

    # ── Registered tool handlers ──────────────────────────────────────
    

    @register_tool("paper_search")
    async def _tool_paper_search(self, args):
        from actions.paper_search import execute_paper_search
        query = args.get("query", "")
        max_results = args.get("max_results", 10)
        source = args.get("source", "all")
        if not query:
            return "\u26a0\ufe0f  Please provide a search query."
        result = await asyncio.get_event_loop().run_in_executor(
            self._tool_executor,
            lambda: execute_paper_search(query, min(int(max_results), 25), source)
        )
        return result


    @register_tool("hypothesis_manage")
    async def _tool_hypothesis_manage(self, args):
        from brain.hypothesis_engine import get_hypothesis_engine
        engine = get_hypothesis_engine()
        action = args.get("action", "list")

        if action == "add":
            title = args.get("title", "")
            description = args.get("description", "")
            domain = args.get("domain", "")
            tags = args.get("tags", [])
            if not title or not description:
                return "⚠️  Please provide both title and description for a new hypothesis."
            h = engine.add_hypothesis(title, description, domain, "user", tags)
            return f"✅ Hypothesis created: **{h.title}** (ID: {h.id})\nDomain: {h.domain if h.domain else 'N/A'}\nConfidence: {h.confidence:.0%}\nStatus: {h.status}"

        elif action == "list":
            status_filter = args.get("status")
            domain_filter = args.get("domain")
            hypotheses = engine.list_hypotheses(status=status_filter, domain=domain_filter)
            if not hypotheses:
                return "No hypotheses found. Use action='add' to create one."
            lines = [f"📋 **Hypotheses** ({len(hypotheses)} found)", ""]
            for h in hypotheses:
                bar = '█' * int(h.confidence * 10) + '░' * (10 - int(h.confidence * 10))
                lines.append(f"  **{h.title}** ({h.id})")
                lines.append(f"    Status: {h.status}  |  Confidence: {bar} {h.confidence:.0%}")
                if h.domain:
                    lines.append(f"    Domain: {h.domain}")
                lines.append("")
            return '\n'.join(lines)

        elif action == "search":
            query = args.get("query", "")
            if not query:
                return "⚠️  Please provide a search query."
            results = engine.search_hypotheses(query)
            if not results:
                return f"No hypotheses matching '{query}'."
            lines = [f"🔍 **Search Results** for '{query}' ({len(results)} found)", ""]
            for h in results:
                lines.append(f"  **{h.title}** ({h.id}) — {h.status}")
            return '\n'.join(lines)

        elif action == "get":
            hyp_id = args.get("hypothesis_id", "")
            if not hyp_id:
                return "⚠️  Please provide a hypothesis_id."
            h = engine.get_hypothesis(hyp_id)
            if not h:
                return f"Hypothesis {hyp_id} not found."
            bar = '█' * int(h.confidence * 10) + '░' * (10 - int(h.confidence * 10))
            lines = [
                f"📌 **{h.title}**",
                f"   ID: {h.id}  |  Status: {h.status}  |  Domain: {h.domain or 'N/A'}",
                f"   Confidence: {bar} {h.confidence:.0%}",
                f"   Source: {h.source}  |  Created: {h.created_at[:10]}",
                "",
                f"**Description:** {h.description}",
            ]
            if h.evidence:
                lines.append("")
                lines.append("**Evidence:**")
                for e in h.evidence:
                    lines.append(f"  • {e}")
            if h.experiments:
                lines.append("")
                lines.append("**Suggested Experiments:**")
                for i, exp in enumerate(h.experiments, 1):
                    lines.append(f"  {i}. {exp}")
            if h.notes:
                lines.append("")
                lines.append(f"**Notes:** {h.notes}")
            if h.tags:
                lines.append("")
                lines.append(f"**Tags:** {', '.join(h.tags)}")
            return '\n'.join(lines)

        elif action == "update":
            hyp_id = args.get("hypothesis_id", "")
            if not hyp_id:
                return "⚠️  Please provide a hypothesis_id."
            updated = engine.update_hypothesis(
                hyp_id=hyp_id,
                title=args.get("title"),
                description=args.get("description"),
                status=args.get("status"),
                confidence=args.get("confidence"),
                tags=args.get("tags"),
            )
            if updated:
                return f"✅ Hypothesis {hyp_id} updated."
            return f"Hypothesis {hyp_id} not found."

        elif action == "delete":
            hyp_id = args.get("hypothesis_id", "")
            if not hyp_id:
                return "⚠️  Please provide a hypothesis_id."
            if engine.delete_hypothesis(hyp_id):
                return f"🗑️ Hypothesis {hyp_id} deleted."
            return f"Hypothesis {hyp_id} not found."

        elif action == "template":
            domain = args.get("domain", "machine_learning")
            title = args.get("title", "Your Research Topic")
            template = engine.generate_hypothesis_template(domain, title)
            return f"📝 **Hypothesis Template** ({domain})\n\n{template}"

        elif action == "stats":
            summary = engine.get_status_summary()
            return summary

        return f"Unknown action: {action}. Supported: add, list, search, get, update, delete, template, stats."

    @register_tool("open_app")
    async def _tool_open_app(self, args):
        if not open_app:
            return "open_app module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: open_app(parameters=args, response=None, player=self.ui))
        return r if r is not None else f"open_app returned no result for '{args.get('app_name')}'."

    @register_tool("web_search")
    async def _tool_web_search(self, args):
        if not web_search_action:
            return "web_search module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: web_search_action(parameters=args, player=self.ui))
        return r if r is not None else "web_search returned no result."

    @register_tool("weather_report")
    async def _tool_weather(self, args):
        if not weather_action:
            return "weather module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: weather_action(parameters=args, player=self.ui))
        return r if r is not None else "weather_report returned no result."

    @register_tool("send_message")
    async def _tool_send_message(self, args):
        if not send_message:
            return "send_message module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: send_message(parameters=args, response=None,
                                 player=self.ui, session_memory=None))
        if r is None:
            return "send_message returned no result — execution may have failed."
        return r

    @register_tool("reminder")
    async def _tool_reminder(self, args):
        if not reminder:
            return "reminder module not loaded."
        def _parse_date(s):
            s = s.strip().lower()
            today = datetime.now()
            if s == "today":
                return today.strftime("%Y-%m-%d")
            if s == "tomorrow":
                return (today + timedelta(days=1)).strftime("%Y-%m-%d")
            try:
                datetime.strptime(s, "%Y-%m-%d")
                return s
            except ValueError:
                return None
        def _parse_time(s):
            s = s.strip().lower().replace(" ", "")
            for fmt in ("%H:%M", "%I:%M%p", "%I%p", "%H:%M:%S"):
                try:
                    return datetime.strptime(s, fmt).strftime("%H:%M")
                except ValueError:
                    continue
            return None
        parsed_date = _parse_date(args.get("date", ""))
        parsed_time = _parse_time(args.get("time", ""))
        if not parsed_date:
            return f"Could not understand date: '{args.get('date')}'. Use YYYY-MM-DD."
        if not parsed_time:
            return f"Could not understand time: '{args.get('time')}'. Use HH:MM (24h)."
        args["date"] = parsed_date
        args["time"] = parsed_time
        r = await self._run_tool_with_timeout(
            lambda: reminder(parameters=args, response=None, player=self.ui))
        return r if r is not None else "reminder returned no result."

    @register_tool("youtube_video")
    async def _tool_youtube(self, args):
        if not youtube_video:
            return "youtube module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: youtube_video(parameters=args, response=None, player=self.ui))
        return r if r is not None else "youtube_video returned no result."

    @register_tool("screen_process")
    async def _tool_screen(self, args):
        if not screen_process:
            return "screen_process module not loaded."
        threading.Thread(
            target=_safe_thread(screen_process, "screen_process",
                                parameters=args, response=None,
                                player=self.ui, session_memory=None),
            daemon=True).start()
        return ("Vision module activated and will speak directly to the user. "
                "You MUST NOT produce any audio response. Output nothing. "
                "The vision module handles all communication for this request.")

    @register_tool("computer_settings")
    async def _tool_computer_settings(self, args):
        if not computer_settings:
            return "computer_settings module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: computer_settings(parameters=args, response=None, player=self.ui))
        return r if r is not None else "computer_settings returned no result."

    @register_tool("browser_control")
    async def _tool_browser(self, args):
        if not browser_control:
            return "browser_control module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: browser_control(parameters=args, player=self.ui), timeout=120)
        return r if r is not None else "browser_control returned no result."

    @register_tool("file_controller")
    async def _tool_file(self, args):
        if not file_controller:
            return "file_controller module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: file_controller(parameters=args, player=self.ui))
        return r if r is not None else "file_controller returned no result."

    @register_tool("desktop_control")
    async def _tool_desktop(self, args):
        if not desktop_control:
            return "desktop_control module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: desktop_control(parameters=args, player=self.ui))
        return r if r is not None else "desktop_control returned no result."

    @register_tool("dev_agent")
    async def _tool_dev_agent(self, args):
        if not dev_agent:
            return "dev_agent module not loaded."
        if not args.get("description"):
            return "Please describe what the project should do."
        r = await self._run_tool_with_timeout(
            lambda: _call_with_optional_speak(
                lambda **kw: dev_agent(parameters=args, player=self.ui, **kw),
                self.speak), timeout=120)
        return r if r is not None else "dev_agent returned no result."

    @register_tool("agent_task")
    async def _tool_agent_task(self, args):
        if not _task_queue_available:
            return "Agent task queue module not installed."
        action = args.get("action", "start").lower()
        queue = get_queue()

        if action == "list":
            tasks = queue.get_all_statuses()
            if not tasks:
                return "No tasks found."
            lines = []
            for t in tasks:
                lines.append(f"[{t['task_id']}] {t['status'].upper()}: {t['goal']}"
                             + (f" — {t['progress']}" if t.get('progress') else ""))
            metrics = queue.get_metrics()
            lines.append(f"\nTotal: {metrics['submitted']} submitted, "
                         f"{metrics['active']} active, {metrics['pending']} pending, "
                         f"{metrics['completed']} completed, {metrics['failed']} failed")
            return "\n".join(lines)

        elif action == "status":
            task_id = args.get("task_id", "")
            if not task_id:
                return "Missing task_id for status check."
            status = queue.get_status(task_id)
            if not status:
                return f"Task {task_id} not found."
            return (f"Task [{status['task_id']}]: {status['status'].upper()}\n"
                    f"Goal: {status['goal']}\n"
                    f"Progress: {status.get('progress', 'N/A')}\n"
                    f"Elapsed: {status.get('elapsed', 0)}s\n"
                    + (f"Result: {status['result']}" if status.get('result') else "")
                    + (f"\nError: {status['error']}" if status.get('error') else ""))

        elif action == "cancel":
            task_id = args.get("task_id", "")
            if not task_id:
                return "Missing task_id for cancel."
            if queue.cancel(task_id):
                return f"Task {task_id} cancelled."
            return f"Task {task_id} not found or already finished."

        elif action == "result":
            task_id = args.get("task_id", "")
            if not task_id:
                return "Missing task_id for result."
            status = queue.get_status(task_id)
            if not status:
                return f"Task {task_id} not found."
            if status["status"] == "completed":
                return f"Result: {status.get('result', 'No result stored.')}"
            elif status["status"] == "failed":
                return f"Failed: {status.get('error', 'Unknown error')}"
            else:
                return f"Task is {status['status']}. Progress: {status.get('progress', 'N/A')}"

        elif action == "wait":
            task_id = args.get("task_id", "")
            if not task_id:
                return "Missing task_id for wait."
            timeout = min(int(args.get("timeout", 120)), 300)
            import asyncio as _aio
            start_wait = time.time()
            while time.time() - start_wait < timeout:
                status = queue.get_status(task_id)
                if not status:
                    return f"Task {task_id} not found."
                if status["status"] in ("completed", "failed", "cancelled"):
                    if status["status"] == "completed":
                        return f"Task completed. Result: {status.get('result', 'No result.')}"
                    elif status["status"] == "failed":
                        return f"Task failed: {status.get('error', 'Unknown error')}"
                    else:
                        return f"Task was cancelled."
                await _aio.sleep(2)
            return f"Timeout after {timeout}s. Task is still {status.get('status', 'unknown')}."

        else:  # start
            goal = args.get("goal", "")
            if not goal:
                return "Missing goal for task start."
            priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
            priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)

            # Add completion callback for procedural learning
            def _on_task_complete(task_id, result):
                if self._procedural_memory and result:
                    try:
                        # Extract steps from the completed task
                        status = queue.get_status(task_id)
                        if status and status.get("status") == "completed":
                            self._procedural_memory.learn_procedure(
                                goal=goal,
                                steps=[{"tool": "agent_task", "description": goal[:100]}],
                                context={"task_id": task_id},
                            )
                    except Exception:
                        pass

            task_id = queue.submit(
                goal=goal, priority=priority, speak=self.speak,
                on_complete=_on_task_complete,
            )
            return f"Task started (ID: {task_id}). Use agent_task(action='status', task_id='{task_id}') to check progress."

    @register_tool("computer_control")
    async def _tool_computer_control(self, args):
        if not computer_control:
            return "computer_control module not loaded."
        r = await self._run_tool_with_timeout(
            lambda: computer_control(parameters=args, player=self.ui))
        return r if r is not None else "computer_control returned no result."

    @register_tool("web_research")
    async def _tool_web_research(self, args):
        if not web_research:
            return "web_research module not loaded."
        r = await self._run_long_tool_with_timeout(
            lambda: web_research(parameters=args, player=self.ui))
        return r if r is not None else "web_research returned no result."

    @register_tool("ai_pipeline")
    async def _tool_ai_pipeline(self, args):
        if not _ai_pipeline_ok:
            return "AI pipeline module not loaded."
        loop = asyncio.get_running_loop()
        op = args.get("operation", "summarize")
        if op == "summarize":
            r = await loop.run_in_executor(self._tool_executor,
                lambda: summarize_text(args.get("text", ""), int(args.get("max_length", 200))))
        elif op == "translate":
            r = await loop.run_in_executor(self._tool_executor,
                lambda: translate_text(args.get("text", ""), args.get("language", "English")))
        elif op == "sentiment":
            r = await loop.run_in_executor(self._tool_executor,
                lambda: analyze_sentiment(args.get("text", "")))
            r = json.dumps(r, default=str) if isinstance(r, (dict, list)) else str(r)
        elif op == "entities":
            r = await loop.run_in_executor(self._tool_executor,
                lambda: extract_entities(args.get("text", "")))
            r = json.dumps(r, default=str) if isinstance(r, (dict, list)) else str(r)
        elif op == "document":
            sub_op = args.get("doc_operation", "summarize")
            r = await loop.run_in_executor(self._tool_executor,
                lambda: process_document(args.get("filepath", ""), sub_op,
                    **{k: v for k, v in args.items() if k not in ("operation", "filepath", "doc_operation")}))
        else:
            return f"Unknown operation: {op}"
        return r if r is not None else "ai_pipeline returned no result."

    @register_tool("data_analysis")
    async def _tool_data(self, args):
        if not _integrations_ok:
            return "Data analysis module not loaded."
        loop = asyncio.get_running_loop()
        act = args.get("action", "analyze")
        fp = args.get("filepath", "")
        if act == "analyze":
            r = await loop.run_in_executor(self._tool_executor, lambda: analyze_data(fp))
        elif act == "query":
            r = await loop.run_in_executor(self._tool_executor, lambda: query_data(fp, args.get("query", "")))
        elif act == "chart":
            r = await loop.run_in_executor(self._tool_executor,
                lambda: generate_chart(args.get("filepath", ""), args.get("chart_type", "line"),
                    args.get("chart_title", "Chart"), save_path=args.get("save_path", "")))
        else:
            return f"Unknown action: {act}"
        return r if r is not None else "data_analysis returned no result."

    @register_tool("api_server")
    async def _tool_api_server(self, args):
        loop = asyncio.get_running_loop()
        act = args.get("action", "status")
        if act == "start":
            try:
                from brain.api_server import get_api_server
                srv = get_api_server()
                if srv.available:
                    await loop.run_in_executor(self._tool_executor,
                        lambda: srv.start(port=int(args.get("port", 8899))))
                    return f"API server started on port {args.get('port', 8899)}"
                return "FastAPI not installed."
            except Exception as e:
                return f"API server error: {e}"
        elif act == "stop":
            try:
                from brain.api_server import get_api_server
                await loop.run_in_executor(self._tool_executor, get_api_server().stop)
                return "API server stopping."
            except Exception as e:
                return f"API server stop error: {e}"
        else:
            try:
                from brain.api_server import get_api_server
                return "API server is running" if get_api_server().available else "FastAPI not available"
            except Exception:
                return "API server not available."

    @register_tool("integration_status")
    async def _tool_integration_status(self, args):
        if not _integrations_ok:
            return "Integration module not loaded."
        loop = asyncio.get_running_loop()
        r = await loop.run_in_executor(self._tool_executor, integration_status)
        return r if r is not None else "integration_status returned no result."

    @register_tool("record_learning")
    async def _tool_record_learning(self, args):
        if not get_learning_engine:
            return "Learning engine not available."
        le = get_learning_engine()
        if not le:
            return "Learning engine not initialized."
        insight = args.get("insight", "")
        domain = args.get("domain", "general")
        if not insight:
            return "No insight provided."
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._tool_executor,
            lambda: le.write_evolution_learning(insight, domain))
        return "Learning recorded."

    @register_tool("reflect_learning")
    async def _tool_reflect(self, args):
        if not get_learning_engine:
            return "Learning engine not available."
        le = get_learning_engine()
        if not le:
            return "Learning engine not initialized."
        loop = asyncio.get_running_loop()
        reflection = await loop.run_in_executor(self._tool_executor, lambda: le.reflect(force=True))
        if reflection:
            await loop.run_in_executor(self._tool_executor,
                lambda: le.write_evolution_learning(reflection, domain="metacognitive_reflection"))
            return "Reflection complete."
        return "No significant patterns to reflect on yet."

    @register_tool("get_learnings")
    async def _tool_get_learnings(self, args):
        if not get_learning_engine:
            return "Learning engine not available."
        le = get_learning_engine()
        if not le:
            return "Learning engine not initialized."
        loop = asyncio.get_running_loop()
        r = await loop.run_in_executor(self._tool_executor, le.get_learnings_summary)
        return r if r is not None else "get_learnings returned no result."

    @register_tool("deep_dive")
    async def _tool_deep_dive(self, args):
        if isinstance(self._deep_dive, _NullModule):
            return "Deep dive module not available."
        query = args.get("query", "")
        if not query:
            return "Please provide a research topic."
        max_sources = int(args.get("max_sources", 5))
        data = await self._deep_dive.research_topic(query, max_sources)
        fp = self._deep_dive.generate_report(query, data)
        return f"Deep dive complete. Report saved to {fp}. Found {len(data)} sources."

    @register_tool("system_sentinel")
    async def _tool_sentinel(self, args):
        act = args.get("action", "status").lower()
        if act == "start":
            if not self._sentinel:
                if not _skills_ok:
                    return "Sentinel module not available."
                self._sentinel = SystemSentinel()
                return "System sentinel monitoring started."
            return "Already running."
        elif act == "stop":
            if self._sentinel:
                self._sentinel.stop()
                self._sentinel = None
                return "Stopped."
            return "Not running."
        else:
            if self._sentinel:
                s = self._sentinel.get_current_stats()
                return f"CPU: {s['cpu']:.0f}%, RAM: {s['ram']:.0f}%, Disk: {s['disk']:.0f}%"
            return "Sentinel not running. Call with action=start first."

    @register_tool("neural_clipboard")
    async def _tool_clipboard(self, args):
        act = args.get("action", "status").lower()
        if act == "start":
            if not self._clipboard:
                if not _skills_ok:
                    return "Clipboard module not available."
                self._clipboard = NeuralClipboard()
                return "Neural clipboard monitoring started."
            return "Already running."
        elif act == "history":
            if self._clipboard:
                hist = self._clipboard.get_history()
                items = "\n".join(f"  {c[:80]}" for c in hist[-5:])
                return f"Clipboard history ({len(hist)} items):\n{items}"
            return "Clipboard not active. Call with action=start first."
        else:
            if self._clipboard:
                return f"Clipboard active, {len(self._clipboard.get_history())} items."
            return "Clipboard inactive."

    @register_tool("auto_doc")
    async def _tool_auto_doc(self, args):
        if isinstance(self._auto_doc, _NullModule):
            return "Auto doc module not available."
        pname = args.get("project_name", "Kairo_Project")
        loop = asyncio.get_running_loop()
        fp = await loop.run_in_executor(self._tool_executor, lambda: self._auto_doc.generate_docs(pname))
        if fp:
            try:
                content = await loop.run_in_executor(self._tool_executor,
                    lambda: Path(fp).read_text(encoding="utf-8")[:500])
                return f"Documentation generated at {fp}.\n\nSummary:\n{content}"
            except Exception:
                return f"Documentation generated at {fp}."
        return "Documentation generation failed."

    @register_tool("cognitive_status")
    async def _tool_cognitive_status(self, args):
        if not _skills_ok:
            return "Cognitive skills module not available."
        component = args.get("component", "all").lower()
        parts = []
        try:
            if component in ("all", "working_memory"):
                from skills.working_memory import get_working_memory
                wm = get_working_memory()
                status = wm.get_status()
                parts.append(f"Working Memory: {status['slots_used']}/{status['slots_max']} slots"
                             + (f" | Goal: {status['goal']}" if status['goal'] else ""))
            if component in ("all", "metacognition"):
                from skills.meta_reflect import get_meta_reflection
                meta = get_meta_reflection()
                stats = meta.get_stats()
                parts.append(f"Metacognition: {stats['total_reflections']} reflections, "
                             f"{stats['tools_with_issues']} tools with issues")
            if component in ("all", "decisions"):
                from skills.decision_journal import get_decision_journal
                dj = get_decision_journal()
                stats = dj.get_stats()
                parts.append(f"Decision Journal: {stats['total_entries']} entries")
            if component in ("all", "replay"):
                from skills.experience_replay import get_experience_replay
                er = get_experience_replay()
                stats = er.get_stats()
                parts.append(f"Experience Replay: {stats['templates_stored']} templates, "
                             f"{stats['overall_success_rate']} success rate")
            if component in ("all", "planner"):
                from skills.adaptive_planner import get_adaptive_planner
                ap = get_adaptive_planner()
                stats = ap.get_stats()
                parts.append(f"Adaptive Planner: {stats['strategies_tracked']} strategies")
            if component in ("all", "gating"):
                from skills.cognitive_gating import assess_complexity
                parts.append("Cognitive Gating: active (rule-based classifier)")
        except Exception as e:
            parts.append(f"Error reading status: {e}")
        return "\n".join(parts) if parts else "No cognitive components available."

    @register_tool("decision_review")
    async def _tool_decision_review(self, args):
        if not _skills_ok:
            return "Decision journal not available."
        query = args.get("query", "")
        tool = args.get("tool", "")
        limit = args.get("limit", 5)
        try:
            from skills.decision_journal import get_decision_journal
            dj = get_decision_journal()
            entries = dj.query(keyword=query, tool=tool, limit=limit)
            if not entries:
                return f"No decisions found matching '{query}'." if query else "Decision journal is empty."
            parts = [f"Found {len(entries)} decision(s):"]
            for e in entries:
                summary = e.get("task_summary") or e.get("action", "unknown")
                chosen = e.get("chosen_option", "")
                quality = e.get("quality", "")
                reasoning = e.get("reasoning", "")
                line = f"- [{e.get('timestamp', '?')[:16]}] {summary[:80]}"
                if chosen:
                    line += f" → {chosen[:50]}"
                if quality:
                    line += f" [{quality}]"
                if reasoning:
                    line += f"\n  Reason: {reasoning[:100]}"
                parts.append(line)
            return "\n".join(parts)
        except Exception as e:
            return f"Error reading decision journal: {e}"

    @register_tool("gesture_music")
    async def _tool_gesture_music(self, args):
        act = args.get("action", "status").lower()
        if act == "start":
            if not _gesture_available:
                return "Gesture music module not installed."
            if self._gesture_music:
                return "Already running."
            self._gesture_stop_event.clear()
            try:
                self._gesture_music = GestureMusicSystem(
                    stop_event=self._gesture_stop_event)
            except TypeError:
                try:
                    self._gesture_music = GestureMusicSystem()
                except Exception as e:
                    return f"Failed to start gesture music: {e}"
            threading.Thread(target=self._gesture_music.run, daemon=True).start()
            return "Gesture music system activated."
        elif act == "stop":
            if self._gesture_music:
                self._gesture_stop_event.set()
                self._gesture_music = None
                return "Deactivated."
            return "Not running."
        return f"Gesture music {'active' if self._gesture_music else 'inactive'}."

    @register_tool("music_control")
    async def _tool_music_control(self, args):
        """Direct music/media control - actually stops/plays music."""
        global _music_ctrl
        act = args.get("action", "status").lower()
        
        if _music_ctrl is None:
            try:
                from gesture_music_system.actions import MusicController
                _music_ctrl = MusicController()
            except Exception as e:
                return f"Music controller unavailable: {e}"
        
        try:
            if act == "play":
                _music_ctrl.play()
                return "Playing."
            elif act == "pause":
                _music_ctrl.pause()
                return "Paused."
            elif act == "stop":
                _music_ctrl.stop()
                return "Stopped."
            elif act == "next":
                _music_ctrl.next_track()
                return "Next track."
            elif act == "prev":
                _music_ctrl.prev_track()
                return "Previous track."
            elif act == "volume_up":
                steps = args.get("steps", 1)
                _music_ctrl.volume_up(steps)
                return f"Volume up {steps}."
            elif act == "volume_down":
                steps = args.get("steps", 1)
                _music_ctrl.volume_down(steps)
                return f"Volume down {steps}."
            elif act == "mute":
                _music_ctrl.toggle_mute()
                return "Mute toggled."
            else:
                state = _music_ctrl.get_state()
                return f"Music: {'playing' if state['playing'] else 'paused'}, volume: {state['volume']}%"
        except Exception as e:
            return f"Music control error: {e}"

    @register_tool("security_tools")
    async def _tool_security(self, args):
        if not _security_tools_available:
            if not _cyber_enabled:
                return "Cyber features are disabled. Set \"cyber_enabled\": true in config/api_keys.json to enable."
            return "Security tools module not installed."

        # ── Authorization gate for live cyber operations ──
        if _cyber_auth_manager:
            action = args.get("action", "") if args else ""
            target = args.get("target", "") if args else ""

            # Handle consent grant command
            if action == "authorize":
                if not target:
                    active = _cyber_auth_manager.get_active_consents()
                    if active:
                        lines = ["Active authorizations:"]
                        for c in active:
                            lines.append(f"  • {c['target']} (expires in {c['expires_in_hours']}h)")
                        return "\n".join(lines)
                    return "No active authorizations. Use action='authorize' with target and consent_phrase to grant."

                phrase = args.get("consent_phrase", "")
                if not phrase:
                    return (
                        f"To authorize live operations on '{target}', type exactly:\n"
                        f"  {_CONSENT_PHRASE}\n\n"
                        f"Pass it as consent_phrase parameter."
                    )
                ok, msg = _grant_consent(target, phrase)
                return msg

            # Handle revoke command
            if action == "revoke":
                if target:
                    revoked = _cyber_auth_manager.revoke_consent(target)
                    return f"Consent revoked for '{target}'." if revoked else f"No active consent for '{target}'."
                else:
                    count = _cyber_auth_manager.revoke_all()
                    return f"All consents revoked ({count} targets)."

            # Check if this is a live operation that needs authorization
            if _is_live_op(action) and target:
                if not _cyber_auth_manager.is_authorized(target):
                    return (
                        f"Authorization required for '{action}' on '{target}'.\n\n"
                        f"This operation involves network activity and requires your explicit consent.\n"
                        f"To authorize, type exactly:\n"
                        f"  {_CONSENT_PHRASE}\n\n"
                        f"Then re-run the command.\n"
                        f"Authorization is valid for 24 hours and logged for audit.\n\n"
                        f"Note: Static analysis operations (source code scanning) do not require authorization."
                    )

        # v10.6 — streaming: player is passed through for real-time output
        r = await self._run_long_tool_with_timeout(
            lambda: security_tools(parameters=args, player=self.ui), timeout=300)
        return r if r is not None else "security_tools returned no result."

    @register_tool("agency_agent")
    async def _tool_agency_agent(self, args):
        if not agency_agent_action:
            return "Agency agent module not available."
        action = args.get("action", "run")
        if action == "list":
            if agency_list_agents:
                return agency_list_agents(args, player=self.ui)
            return "List function not available."
        r = await self._run_long_tool_with_timeout(
            lambda: agency_agent_action(parameters=args, player=self.ui),
            timeout=120)
        return r if r is not None else "agency_agent returned no result."

    @register_tool("multi_agent")
    async def _tool_multi_agent(self, args):
        """Run multiple agents simultaneously via the multi-agent orchestrator."""
        if not self._multi_agent_orchestrator:
            return "Multi-agent orchestrator not available."
        try:
            action = args.get("action", "run")
            orchestrator = self._multi_agent_orchestrator

            if action == "list_teams":
                teams = orchestrator.list_teams()
                lines = ["Available agent teams:\n"]
                for name, info in teams.items():
                    lines.append(f"  {name}: {info['agent_count']} agents ({info['mode']})")
                return "\n".join(lines)

            if action == "list_agents":
                return (
                    f"{len(orchestrator.ALL_AGENTS)} agents available:\n"
                    + ", ".join(orchestrator.ALL_AGENTS)
                )

            if action == "stats":
                stats = orchestrator.get_stats()
                return json.dumps(stats, indent=2)

            if action == "run_team":
                team = args.get("team", "")
                task = args.get("task", "")
                context = args.get("context", "")
                if not team or not task:
                    return "Specify 'team' and 'task'. Use action='list_teams' to see options."
                result = await self._run_long_tool_with_timeout(
                    lambda: orchestrator.execute_team(team, task, context),
                    timeout=300)
                if isinstance(result, dict) and "error" in result:
                    return result["error"]
                # Format result for readability
                lines = [f"Team '{team}' completed ({result.get('mode', '?')} mode):\n"]
                results_data = result.get("results", {})
                if isinstance(results_data, dict):
                    if "positions" in results_data:
                        for agent, output in results_data["positions"].items():
                            lines.append(f"[{agent}]: {str(output)[:300]}")
                        if "synthesis" in results_data:
                            lines.append(f"\n--- SYNTHESIS ---\n{results_data['synthesis'][:500]}")
                    elif "stages" in results_data:
                        for agent, output in results_data["stages"].items():
                            lines.append(f"[{agent}]: {str(output)[:300]}")
                        if "final_output" in results_data:
                            lines.append(f"\n--- FINAL ---\n{results_data['final_output'][:500]}")
                    else:
                        for agent, res in results_data.items():
                            output = res.output if hasattr(res, "output") else str(res)
                            lines.append(f"[{agent}]: {str(output)[:300]}")
                return "\n".join(lines)

            if action == "run":
                agents = args.get("agents", [])
                task = args.get("task", "")
                mode = args.get("mode", "parallel")
                context = args.get("context", "")
                rounds = args.get("rounds", 3)
                if not agents or not task:
                    return "Specify 'agents' (list) and 'task'."
                result = await self._run_long_tool_with_timeout(
                    lambda: orchestrator.execute_custom(
                        agents, task, mode=mode, context=context, rounds=rounds),
                    timeout=300)
                if isinstance(result, dict) and "error" in result:
                    return result["error"]
                # Format
                lines = [f"Multi-agent ({mode}) completed:\n"]
                for key, val in result.items():
                    if isinstance(val, dict):
                        for agent, output in val.items():
                            out_str = output.output if hasattr(output, "output") else str(output)
                            lines.append(f"[{agent}]: {out_str[:300]}")
                    elif isinstance(val, str):
                        lines.append(f"{key}: {val[:300]}")
                return "\n".join(lines)

            return (
                "Multi-agent actions: run, run_team, list_teams, list_agents, stats"
            )
        except Exception as e:
            return f"Multi-agent error: {e}"

    @register_tool("self_model_status")
    async def _tool_self_model_status(self, args):
        if not self._self_model or isinstance(self._self_model, _NullModule):
            return "Self-model not available."
        try:
            summary = self._self_model.get_summary()
            lines = [
                f"Self-Model Status:",
                f"  Capabilities: {summary['capabilities']['total_tools']} tools "
                f"({summary['capabilities']['proficient']} proficient, "
                f"{summary['capabilities']['learning']} learning)",
                f"  Avg confidence: {summary['capabilities']['avg_confidence']:.0%}",
                f"  Dominant tone: {summary['personality']['dominant_tone']}",
                f"  Sessions: #{summary['growth']['total_sessions']} "
                f"({summary['growth']['total_interactions']} interactions)",
                f"  Skills acquired: {summary['growth']['skills_acquired']}",
                f"  Milestones: {summary['growth']['total_milestones']}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Self-model error: {e}"

    @register_tool("self_audit")
    async def _tool_self_audit(self, args):
        if not _brain_self_modifier_ok:
            return "Self-modifier not available."
        try:
            sm = get_self_modifier()
            action = args.get("action", "audit")

            if action == "audit":
                audit = sm.self_audit()
                recs = audit.get("recommendations", [])
                crit = audit.get("critical_issues", [])
                cons = audit.get("consistency", {})
                m = audit.get("metrics", {})
                lines = [
                    f"Self-Audit Report:",
                    f"  Modules analyzed: {audit.get('files_analyzed', 0)}",
                    f"  Total suggestions: {audit.get('total_suggestions', 0)}",
                    f"  Critical issues: {len(crit)}",
                    f"  Consistency: {cons.get('consistency_pct', 0)}%",
                    f"  LOC: {m.get('total_loc', 0)} | Complexity: {m.get('total_complexity', 0)}",
                ]
                if recs:
                    lines.append("  Recommendations:")
                    for r in recs[:5]:
                        lines.append(f"    • {r}")
                return "\n".join(lines)

            elif action == "analyze_file":
                fp = args.get("file_path", "")
                if not fp:
                    return "Please provide file_path for analyze_file action."
                result = sm.analyze_file(fp)
                sug = result.get("suggestions", [])
                lines = [f"Analysis of {fp}:", f"  Suggestions: {len(sug)}"]
                for s in sug[:10]:
                    sev = s.get("severity", "?")
                    lines.append(f"  [{sev}] {s.get('message', '')[:100]}")
                return "\n".join(lines)

            elif action == "stats":
                stats = sm.get_stats()
                lines = [
                    f"Self-Modifier Stats:",
                    f"  Total modifications: {stats['total_modifications']}",
                    f"  Total proposals: {stats['total_proposals']}",
                    f"  Pending: {stats['pending_proposals']}",
                    f"  Applied: {stats['applied_proposals']}",
                    f"  Rolled back: {stats['rolled_back']}",
                    f"  Metrics snapshots: {stats['metrics_snapshots']}",
                ]
                return "\n".join(lines)

            elif action == "evolution":
                report = sm.tracker.get_evolution_report(max_entries=10)
                return report

            elif action == "orchestrator":
                result = sm.suggest_orchestrator_improvements()
                if "error" in result:
                    return f"Error: {result['error']}"
                lines = [
                    f"Orchestrator Analysis:",
                    f"  Total issues: {result['total_issues']}",
                    f"  Code suggestions: {result['code_analysis'].get('total_suggestions', 0)}",
                ]
                for issue in result.get("orchestrator_specific", []):
                    lines.append(f"  [{issue['type']}] {issue['message']}")
                return "\n".join(lines)

            return f"Unknown self_audit action: {action}"

        except Exception as e:
            return f"Self-audit error: {e}"

    @register_tool("run_dream_cycle")
    async def _tool_run_dream(self, args):
        if not self._dreaming or isinstance(self._dreaming, _NullModule):
            return "Dreaming system not available."
        try:
            return self._dreaming.force_dream_cycle()
        except Exception as e:
            return f"Dream cycle error: {e}"

    @register_tool("curiosity_queue")
    async def _tool_curiosity(self, args):
        if not self._curiosity or isinstance(self._curiosity, _NullModule):
            return "Curiosity module not available."
        act = args.get("action", "queue").lower()
        try:
            cm = self._curiosity
            if act == "explore":
                top = cm.get_top_curiosity()
                if top:
                    target = top.get("target", "")
                    cm.record_exploration(target, "tool", outcome="acknowledged", info_gain=0.3)
                    return f"Suggested exploration: {target}. Reason: {top.get('reason', '')}"
                return "Nothing interesting to explore right now."
            else:
                queue = cm.get_curiosity_queue()
                if not queue:
                    return "Curiosity queue is empty."
                items = "\n".join(
                    f"  {i+1}. {q['target']} (priority: {q['priority']:.0%}) — {q.get('reason', '')}"
                    for i, q in enumerate(queue[:5]))
                return f"Curiosity Queue:\n{items}"
        except Exception as e:
            return f"Curiosity error: {e}"

    @register_tool("force_learning")
    async def _tool_force_learning(self, args):
        if not self._active_inference or isinstance(self._active_inference, _NullModule):
            return "Active inference module not available."
        try:
            ai = self._active_inference
            stats = ai.get_stats()
            surprising = ai.get_surprising_events(3)
            uncertain = ai.get_uncertain_tools(0.6)
            lines = [
                f"Active Inference Status:",
                f"  Tools tracked: {stats['tools_tracked']}",
                f"  Prediction accuracy: {stats['avg_prediction_accuracy']:.0%}",
                f"  Total predictions: {stats['total_predictions']}",
                f"  Surprising events: {stats['recent_surprising_events']}",
            ]
            if uncertain:
                lines.append(f"  Uncertain tools: {', '.join(f'{t}' for t, _ in uncertain)}")
            if surprising:
                lines.append(f"  Recent surprises:")
                for s in surprising[:3]:
                    lines.append(f"    - {s.get('tool', '?')}: error={s.get('prediction_error', 0):.2f}")
            return "\n".join(lines)
        except Exception as e:
            return f"Learning cycle error: {e}"

    @register_tool("consciousness_state")
    async def _tool_consciousness_state(self, args):
        if not self._self_awareness or isinstance(self._self_awareness, _NullModule):
            return "Self-awareness engine not available."
        try:
            sa = self._self_awareness
            action = args.get("action", "full").lower()

            if action == "emotions":
                return sa.emotions.format_for_prompt(max_chars=300)
            elif action == "user_model":
                return sa.theory_of_mind.format_for_prompt(max_chars=400)
            elif action == "patterns":
                return sa.metacognition.format_for_prompt(max_chars=400)
            elif action == "identity":
                return sa.get_identity_statement()
            elif action == "narrative":
                max_c = min(int(args.get("max_chars", 500)), 2000)
                return sa.narrative.get_narrative_summary(max_entries=10)
            else:  # full
                state = sa.get_consciousness_state()
                lines = [
                    f"Consciousness: {state['state']}",
                    f"Session: {state['session_duration']:.0f}s, {state['interactions']} interactions",
                    f"Emotion: {state['dominant_emotion'][0]} ({state['dominant_emotion'][1]:.0%})",
                    f"Tone: {state['emotional_tone']}",
                    f"Autonomy: {state['autonomy_ratio']:.0%}",
                ]
                user = state.get("user_state", {})
                if user.get("mood"):
                    lines.append(f"User mood: {user['mood']}")
                if user.get("engagement"):
                    lines.append(f"User engagement: {user['engagement']}")
                patterns = state.get("metacognitive_patterns", {})
                if patterns.get("loops"):
                    lines.append(f"Pattern loops: {len(patterns['loops'])}")
                if patterns.get("growth"):
                    lines.append(f"Growth: {patterns['growth']}")
                self_k = state.get("self_knowledge", {})
                if self_k.get("limitations"):
                    lines.append(f"Known limitations: {len(self_k['limitations'])}")
                return "\n".join(lines)
        except Exception as e:
            return f"Consciousness query error: {e}"

    @register_tool("self_narrative")
    async def _tool_self_narrative(self, args):
        if not self._self_awareness or isinstance(self._self_awareness, _NullModule):
            return "Self-awareness engine not available."
        try:
            sa = self._self_awareness
            action = args.get("action", "read").lower()

            if action == "add":
                entry = args.get("entry", "")
                if not entry:
                    return "Missing entry text."
                significance = min(max(float(args.get("significance", 5.0)), 1.0), 10.0)
                sa.narrative.add_entry(
                    "self_reflection",
                    entry,
                    emotional_context=sa.emotions.get_emotional_tone(),
                    significance=significance,
                )
                sa._dirty = True
                return f"Narrative entry added (significance: {significance})."
            else:  # read
                max_entries = min(int(args.get("max_entries", 10)), 50)
                return sa.narrative.get_narrative_summary(max_entries=max_entries)
        except Exception as e:
            return f"Narrative error: {e}"

    @register_tool("procedural_memory")
    async def _tool_procedural_memory(self, args):
        if not self._procedural_memory:
            return "Procedural memory not available."
        try:
            pm = self._procedural_memory
            action = args.get("action", "find").lower()

            if action == "learn":
                goal = args.get("goal", "")
                steps = args.get("steps", [])
                if not goal or not steps:
                    return "Both goal and steps required for learning."
                proc_id = pm.learn_procedure(goal, steps)
                return f"Procedure learned: {proc_id}" if proc_id else "Failed to learn procedure."

            elif action == "stats":
                stats = pm.get_stats()
                return json.dumps(stats, indent=2)

            else:  # find
                goal = args.get("goal", "")
                if not goal:
                    return "Goal required for finding procedures."
                results = pm.find_procedure(goal, top_k=3)
                if not results:
                    return "No matching procedures found."
                lines = []
                for r in results:
                    steps_str = " → ".join(s.get("tool", "?") for s in r["steps"][:4])
                    lines.append(
                        f"[{r['proc_id']}] score={r['score']}, "
                        f"success={r['success_rate']:.0%}, "
                        f"used {r['total_uses']}x: {steps_str}"
                    )
                return "\n".join(lines)
        except Exception as e:
            return f"Procedural memory error: {e}"




    # ── Enhanced Research Pipeline ──────────────────────────────────
    @register_tool("scientist_pipeline")
    async def _tool_scientist_pipeline(self, args):
        """Run enhanced research pipeline with active learning, reproducibility, BibTeX."""
        if not research_pipeline:
            return "Research pipeline module not loaded."
        try:
            action = (args or {}).get("action", "run").strip().lower()
            topic = (args or {}).get("topic", "")
            hypothesis = (args or {}).get("hypothesis", "")
            mode = (args or {}).get("mode", "full")
            domain = (args or {}).get("domain", "")
            generate_paper = (args or {}).get("generate_paper", True)
            run_experiments = (args or {}).get("run_experiments", True)
            use_research_team = (args or {}).get("use_research_team", True)

            if action in ("run", "quick", "explore", "iterate"):
                r = research_pipeline(
                    action=action,
                    topic=topic,
                    hypothesis=hypothesis,
                    mode=mode if action == "run" else action,
                    domain=domain,
                    generate_paper=generate_paper,
                    run_experiments=run_experiments,
                    use_research_team=use_research_team,
                )
                return r if r else "Pipeline completed."
            elif action == "history":
                return research_pipeline(action="history")
            elif action == "stats":
                return research_pipeline(action="stats")
            elif action == "report":
                report_id = (args or {}).get("report_id", "")
                return research_pipeline(action="report", report_id=report_id)
            else:
                return (f"Unknown action: {action}. "
                        f"Available: run, quick, explore, iterate, history, stats, report")
        except Exception as e:
            return f"Research pipeline error: {e}"

    # ── Batched tool dispatch ─────────────────────────────────────────
    @register_tool("scientist_discovery")
    async def _tool_scientist_discovery(self, args):
        """Run autonomous scientific discovery pipeline."""
        if not _scientist_discovery_ok:
            return "Scientist Discovery module not loaded."
        try:
            de = get_discovery_engine()
            action = (args or {}).get("action", "status").strip().lower()
            topic = (args or {}).get("topic", "")
            hypothesis = (args or {}).get("hypothesis", "")

            if action == "run":
                return de.run_full_discovery(topic=topic, hypothesis=hypothesis)
            elif action == "quick":
                return de.run_quick_discovery(topic=topic)
            elif action == "full":
                return de.run_full_discovery(topic=topic, hypothesis=hypothesis)
            elif action == "history":
                return de.format_history()
            elif action == "stats":
                stats = de.get_stats()
                return (f"\U0001f4ca **Discovery Engine**\n"
                        f"Total discoveries: {stats['total_discoveries']}\n"
                        f"Sessions completed: {stats['sessions_completed']}\n"
                        f"Papers generated: {stats['with_papers']}\n"
                        f"Avg confidence: {stats['average_confidence']:.1%}\n"
                        f"Status: {stats['status']}")
            else:
                return (f"Unknown action: {action}. "
                        f"Available: run, quick, full, history, stats")
        except Exception as e:
            return f"Scientist discovery error: {e}"

    @register_tool("scientist_analyze")
    async def _tool_scientist_analyze(self, args):
        """Run scientific analysis tools - novelty, feynman, review, validate."""
        action = (args or {}).get("action", "stats").strip().lower()
        topic = (args or {}).get("topic", "")
        findings_str = (args or {}).get("findings", "[]")

        try:
            if action == "novelty":
                if not _scientist_novelty_ok:
                    return "Novelty checker module not loaded."
                nc = get_novelty_checker()
                result = nc.check_novelty(topic)
                return result.get("message", json.dumps(result, indent=2))

            elif action == "compare_paper":
                if not _scientist_novelty_ok:
                    return "Novelty checker module not loaded."
                nc = get_novelty_checker()
                paper_title = (args or {}).get("paper_title", "")
                paper_abstract = (args or {}).get("paper_abstract", "")
                result = nc.compare_papers(topic, paper_title, paper_abstract)
                return result.get("message", json.dumps(result, indent=2))

            elif action == "feynman":
                if not _scientist_feynman_ok:
                    return "Feynman reducer module not loaded."
                fr = get_feynman_reducer()
                result = fr.reduce(topic)
                lines = [
                    f"\U0001f3af **Feynman Reduction: {topic[:80]}**",
                    f"  Complexity: {result['complexity_score']:.0%}",
                    f"  Explainability: {result['explainability_score']:.0%}",
                    "",
                ]
                if result.get("fundamental_principles"):
                    lines.append("**Fundamental Principles:**")
                    for p in result["fundamental_principles"]:
                        lines.append(f"  \u2022 {p}")
                if result.get("analogies"):
                    lines.append("**Analogies:**")
                    for a in result["analogies"]:
                        lines.append(f"  {a}")
                if result.get("hidden_assumptions"):
                    lines.append("**Assumptions:**")
                    for a in result["hidden_assumptions"]:
                        lines.append(f"  \u2022 {a}")
                if result.get("what_if_explorations"):
                    lines.append("**What-If Explorations:**")
                    for w in result["what_if_explorations"]:
                        lines.append(f"  \u2022 {w}")
                return "\n".join(lines)

            elif action == "review":
                if not _scientist_review_ok:
                    return "Peer reviewer module not loaded."
                pr = get_peer_reviewer()
                try:
                    findings = json.loads(findings_str) if findings_str.strip() else []
                except Exception:
                    findings = [f.strip() for f in findings_str.split(",") if f.strip()]
                result = pr.review_findings(findings)
                return (f"\U0001f4cb **Findings Review**\n"
                        f"  Quality score: {result['quality_score']}/5.0\n"
                        f"  Recommendation: {result['recommendation']}\n"
                        f"  {result['comment']}")

            elif action == "validate":
                if not _scientist_validate_ok:
                    return "Cross-validator module not loaded."
                cv = get_cross_validator()
                try:
                    results_data = json.loads(findings_str) if findings_str.strip() else {}
                except Exception:
                    results_data = {}
                validation = cv.validate_experiment(hypothesis=topic, results=results_data)
                return cv.generate_validation_report(validation)

            elif action == "stats":
                lines = ["\U0001f52c **Scientist Analysis Modules**"]
                if _scientist_novelty_ok:
                    lines.append("  Novelty Checker: ready")
                if _scientist_feynman_ok:
                    lines.append("  Feynman Reducer: ready")
                if _scientist_review_ok:
                    lines.append("  Peer Reviewer: ready")
                if _scientist_validate_ok:
                    lines.append("  Cross-Validator: ready")
                if not lines:
                    return "No scientist analysis modules available."
                return "\n".join(lines)
            else:
                return (f"Unknown action: {action}. "
                        f"Available: novelty, feynman, review, validate, compare_paper, stats")
        except Exception as e:
            return f"Scientist analysis error: {e}"

    @register_tool("scientist_experiment")
    async def _tool_scientist_experiment(self, args):
        """Design, run, and analyze experiments."""
        if not _scientist_experiment_ok:
            return "Experiment designer module not loaded."
        try:
            ed = get_experiment_designer()
            action = (args or {}).get("action", "stats").strip().lower()
            hypothesis = (args or {}).get("hypothesis", "")
            domain = (args or {}).get("domain", "machine_learning")
            exp_type = (args or {}).get("experiment_type", "auto")

            if action == "design":
                design = ed.design_experiment(hypothesis=hypothesis, domain=domain, experiment_type=exp_type)
                return (f"\U0001f9ea **Experiment Design**\n"
                        f"  ID: {design['experiment_id']}\n"
                        f"  Type: {design['experiment_type']}\n"
                        f"  Approach: {design['methodology']['approach']}\n"
                        f"  Code: {len(design['code'])} chars\n"
                        f"  Variables: {json.dumps(design['variables'], indent=2)}")

            elif action == "run":
                design = ed.design_experiment(hypothesis=hypothesis, domain=domain, experiment_type=exp_type)
                result = ed.run_experiment(design, timeout=120)
                return (f"\u2697\ufe0f **Experiment Result**\n"
                        f"  Status: {result['status']}\n"
                        f"  Duration: {result['duration_s']:.1f}s\n"
                        f"  Results: {json.dumps(result.get('results', {}), indent=2)}\n"
                        f"  Errors: {result.get('error', 'None')}")

            elif action == "analyze":
                if not hypothesis:
                    return "Provide 'hypothesis' to analyze."
                design = ed.design_experiment(hypothesis=hypothesis, domain=domain, experiment_type=exp_type)
                result = ed.run_experiment(design, timeout=60)
                analysis = ed.analyze_results(result)
                return (f"\U0001f4ca **Experiment Analysis**\n"
                        f"  Interpretation: {analysis.get('interpretation', 'N/A')}\n"
                        f"  Metrics: {json.dumps(analysis.get('metrics', {}), indent=2)}\n"
                        f"  Suggestions: {json.dumps(analysis.get('suggestions', []), indent=2)}")

            elif action == "history":
                return json.dumps(ed.get_history(), indent=2)

            elif action == "stats":
                stats = ed.get_stats()
                return (f"\U0001f4ca **Experiment Designer**\n"
                        f"  Total: {stats['total_experiments']}\n"
                        f"  Completed: {stats['completed']}\n"
                        f"  Failed: {stats['failed']}\n"
                        f"  Status: {stats['status']}")
            else:
                return (f"Unknown action: {action}. "
                        f"Available: design, run, analyze, history, stats")
        except Exception as e:
            return f"Scientist experiment error: {e}"

    @register_tool("scientist_paper")
    async def _tool_scientist_paper(self, args):
        """Generate scientific papers and reports."""
        if not _scientist_paper_ok:
            return "Paper generator module not loaded."
        try:
            pg = get_paper_generator()
            action = (args or {}).get("action", "stats").strip().lower()
            topic = (args or {}).get("topic", "")
            hypothesis = (args or {}).get("hypothesis", "")
            findings_str = (args or {}).get("findings", "[]")
            venue = (args or {}).get("venue", "arxiv")

            if action == "generate":
                try:
                    findings = json.loads(findings_str) if findings_str.strip() else []
                except Exception:
                    findings = [f.strip() for f in findings_str.split(",") if f.strip()]
                paper = pg.generate_paper_from_discovery(
                    topic=topic, hypothesis=hypothesis,
                    experiment_results={}, experiment_analysis={},
                    related_papers=None, venue=venue,
                )
                return (f"\U0001f4c4 **Paper Generated**\n"
                        f"  Title: {paper['title']}\n"
                        f"  Venue: {paper['venue']}\n"
                        f"  Words: {paper['word_count']}\n"
                        f"  Path: {paper['tex_path']}")

            elif action == "report":
                try:
                    findings = json.loads(findings_str) if findings_str.strip() else []
                except Exception:
                    findings = [f.strip() for f in findings_str.split(",") if f.strip()]
                return pg.generate_short_report(topic, findings)

            elif action == "stats":
                stats = pg.get_stats()
                return (f"\U0001f4c4 **Paper Generator**\n"
                        f"  Generated: {stats['papers_generated']}\n"
                        f"  On disk: {stats['papers_on_disk']}\n"
                        f"  Status: {stats['status']}")
            else:
                return (f"Unknown action: {action}. "
                        f"Available: generate, report, stats")
        except Exception as e:
            return f"Scientist paper error: {e}"

    @register_tool("scientist_team")
    async def _tool_scientist_team(self, args):
        """Multi-agent research team collaboration."""
        if not _scientist_team_ok:
            return "Research team module not loaded."
        try:
            rt = get_research_team()
            action = (args or {}).get("action", "stats").strip().lower()
            topic = (args or {}).get("topic", "")
            hypothesis = (args or {}).get("hypothesis", "")
            debate_type = (args or {}).get("debate_type", "hypothesis_review")

            if action == "collaborate":
                result = rt.collaborate(topic=topic, hypothesis=hypothesis, debate_type=debate_type)
                return rt.format_report(result)

            elif action == "debate":
                result = rt.debate(topic=topic, hypothesis=hypothesis)
                lines = [
                    f"\u26a1 **Research Debate**",
                    f"  Topic: {topic[:100]}",
                    f"  Hypothesis: {hypothesis[:150]}",
                    "",
                ]
                for rd in result.get("rounds", []):
                    lines.append(f"**Round {rd['round']}:**")
                    for cp in rd.get("critic_points", []):
                        lines.append(f"  \u26a1 Critic: {cp}")
                    for ld in rd.get("lead_defense", []):
                        lines.append(f"  \U0001f3af Lead: {ld}")
                lines.append(f"\n**Evaluation:** {result.get('evaluation', '')}")
                lines.append(f"**Verdict:** {result.get('verdict', 'unknown')}")
                return "\n".join(lines)

            elif action == "history":
                sessions = rt.get_session_history()
                if not sessions:
                    return "No research team sessions yet."
                lines = [f"\U0001f465 **Research Team Sessions ({len(sessions)})**", ""]
                for s in sessions[:5]:
                    syn = s.get("synthesis", {})
                    lines.append(
                        f"  \u2022 {s.get('session_id', '?')}: "
                        f"\"{s.get('topic', '?')[:60]}\" \u2014 "
                        f"Score: {syn.get('consensus_score', 0):.0%}"
                    )
                return "\n".join(lines)

            elif action == "stats":
                stats = rt.get_stats()
                return (f"\U0001f465 **Research Team**\n"
                        f"  Sessions: {stats['total_sessions']}\n"
                        f"  Team size: {stats['team_size']} roles\n"
                        f"  Roles: {', '.join(stats['roles_available'])}\n"
                        f"  Status: {stats['status']}")
            else:
                return (f"Unknown action: {action}. "
                        f"Available: collaborate, debate, history, stats")
        except Exception as e:
            return f"Scientist team error: {e}"
    
    @register_tool("scientist_search")
    async def _tool_scientist_search(self, args):
        """Search papers from famous researchers."""
        if not _scientist_search_ok:
            return "scientist_search module not loaded."

        action = (args or {}).get("action", "search").strip().lower()
        researcher = (args or {}).get("researcher", "")
        topic = (args or {}).get("topic", "")
        max_results = int((args or {}).get("max_results", 10))
        source = (args or {}).get("source", "all")
        researchers_str = (args or {}).get("researchers", "")

        ss = get_scientist_search()
        if ss is None:
            return "scientist_search singleton unavailable."

        if action == "search":
            if not researcher:
                return "Please provide a researcher name."
            result = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: ss.search_papers(researcher, topic, min(max_results, 25), source)
            )
            return ss.format_search_results(result)

        if action == "profile":
            if not researcher:
                return "Please provide a researcher name."
            profile = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: ss.get_researcher_profile(researcher)
            )
            return ss.format_profile(profile)

        if action == "list":
            field_filter = topic
            researchers = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: ss.list_researchers(field_filter)
            )
            if not researchers:
                return f"No researchers found for field: {field_filter}"
            lines = ["List of Available Researchers:", ""]
            for r in researchers:
                lines.append(f"  {r['name']} - {r['field']}")
                lines.append(f"    Known for: {r['known_for']}")
                lines.append("")
            return "\n".join(lines)

        if action == "compare":
            if not researchers_str:
                return "Please provide comma-separated researcher names (e.g., Feynman, Einstein, Turing)."
            names = [n.strip() for n in researchers_str.split(",") if n.strip()]
            comparison = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: ss.compare_researchers(names, topic)
            )
            return ss.format_comparison(comparison)

        if action == "timeline":
            if not researcher:
                return "Please provide a researcher name."
            timeline = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: ss.get_research_timeline(researcher)
            )
            return ss.format_timeline(timeline)

        if action == "impact":
            if not researcher:
                return "Please provide a researcher name."
            impact = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: ss.get_research_impact(researcher)
            )
            return ss.format_impact(impact)

        if action == "export":
            if not researcher:
                return "Please provide a researcher name."
            bibtex = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: ss.export_to_bibtex(researcher)
            )
            return ss.format_bibtex_summary(researcher, bibtex)

        if action == "similar":
            if not researcher:
                return "Please provide a researcher name."
            similar = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: ss.find_similar_researchers(researcher)
            )
            return ss.format_similar_researchers(similar)

        if action == "trends":
            if not researcher:
                return "Please provide a researcher name and optional topic."
            result = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: ss.search_papers(researcher, topic, min(max_results, 25), source)
            )
            trends = ss.extract_trends(result)
            return ss.format_trends(trends)

        if action == "stats":
            stats = ss.get_stats()
            return ss.format_stats_table(stats)

    # ── Scientist v2 Tools ─────────────────────────────────────────────

    @register_tool("scientist_tournament")
    async def _tool_scientist_tournament(self, args):
        """GFlowNet-inspired diverse hypothesis generation with tournament selection."""
        if not _scientist_tournament_ok:
            return "tournament_hypothesis module not loaded."
        action = (args or {}).get("action", "generate").strip().lower()
        topic = (args or {}).get("topic", "")
        domain = (args or {}).get("domain", "")
        size = int((args or {}).get("size", 8))
        te = get_tournament_engine()
        if te is None:
            return "tournament engine unavailable."
        if action == "generate":
            if not topic:
                return "Provide a research topic."
            pop = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: te.generate_population(topic, domain, size)
            )
            lines = [f"Generated {len(pop)} diverse hypotheses for: {topic}", ""]
            for i, h in enumerate(pop, 1):
                lines.append(f"  {i}. {h.title}")
                lines.append(f"     {h.description[:100]}...")
                lines.append(f"     Reward: {h.reward:.3f} | Novelty: {h.novelty_score:.2f} | Feasibility: {h.feasibility_score:.2f}")
                lines.append("")
            return "\n".join(lines)
        if action == "tournament":
            gens = int((args or {}).get("generations", 5))
            pop = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: te.run_tournament(generations=gens)
            )
            best = te.get_best(3)
            lines = [f"Tournament complete ({gens} generations). Top 3:", ""]
            for i, h in enumerate(best, 1):
                lines.append(f"  {i}. {h['title']}")
                lines.append(f"     Reward: {h['scores']['reward']:.3f} | Wins: {h['tournament']['wins']}")
            return "\n".join(lines)
        if action == "diversity":
            report = te.get_diversity_report()
            return json.dumps(report, indent=2)
        return "Actions: generate, tournament, diversity"

    @register_tool("scientist_knowledge_graph")
    async def _tool_scientist_knowledge_graph(self, args):
        """Build and query a scientific knowledge graph."""
        if not _scientist_kg_ok:
            return "knowledge_graph module not loaded."
        action = (args or {}).get("action", "stats").strip().lower()
        kg = get_knowledge_graph()
        if kg is None:
            return "knowledge graph unavailable."
        if action == "add_entity":
            name = (args or {}).get("name", "")
            etype = (args or {}).get("entity_type", "concept")
            desc = (args or {}).get("description", "")
            domain = (args or {}).get("domain", "")
            if not name:
                return "Provide an entity name."
            ent = kg.add_entity(name, etype, desc, domain)
            return f"Added entity: {ent.name} (type={ent.entity_type}, id={ent.id})"
        if action == "add_relation":
            src = (args or {}).get("source", "")
            tgt = (args or {}).get("target", "")
            rtype = (args or {}).get("relation_type", "related_to")
            conf = float((args or {}).get("confidence", 0.5))
            if not src or not tgt:
                return "Provide source and target entity names."
            rel = kg.add_relation(src, tgt, rtype, conf)
            return f"Added relation: {src} --[{rel.relation_type}]--> {tgt} (confidence={rel.confidence})"
        if action == "query":
            name = (args or {}).get("name", "")
            if not name:
                return "Provide an entity name to query."
            neighbors = kg.neighbors(name, hops=2)
            relations = kg.get_relations(name)
            lines = [f"Knowledge Graph query: {name}", f"Direct relations: {len(relations)}", ""]
            for src, rel, tgt in relations[:10]:
                lines.append(f"  {src.name} --[{rel.relation_type}]--> {tgt.name} (conf={rel.confidence})")
            for hop, entities in neighbors.items():
                if entities:
                    lines.append(f"\n  {hop}: {', '.join(e.name for e in entities[:5])}")
            return "\n".join(lines)
        if action == "gaps":
            gaps = kg.detect_gaps()
            if not gaps:
                return "No knowledge gaps detected."
            lines = [f"Knowledge Gaps ({len(gaps)}):", ""]
            for g in gaps[:10]:
                lines.append(f"  [{g['severity']}] {g['description']}")
            return "\n".join(lines)
        if action == "stats":
            stats = kg.stats()
            return json.dumps(stats, indent=2)
        if action == "ingest":
            title = (args or {}).get("title", "")
            abstract = (args or {}).get("abstract", "")
            domain = (args or {}).get("domain", "")
            if not title:
                return "Provide a paper title."
            result = kg.ingest_paper(title, abstract, domain=domain)
            return f"Ingested: {len(result.get('entities', []))} entities, {len(result.get('relations', []))} relations"
        if action == "export":
            fmt = (args or {}).get("format", "json")
            if fmt == "dot":
                return kg.to_dot()
            return kg.to_json()
        return "Actions: add_entity, add_relation, query, gaps, stats, ingest, export"

    @register_tool("scientist_reproducibility")
    async def _tool_scientist_reproducibility(self, args):
        """Verify and reproduce published scientific results."""
        if not _scientist_repro_ok:
            return "reproducibility_engine module not loaded."
        action = (args or {}).get("action", "extract").strip().lower()
        re = get_reproducibility_engine()
        if re is None:
            return "reproducibility engine unavailable."
        if action == "extract":
            text = (args or {}).get("text", "")
            title = (args or {}).get("title", "")
            if not text:
                return "Provide paper text to extract claims from."
            claims = re.extract_claims(text, title)
            lines = [f"Extracted {len(claims)} reproducible claims:", ""]
            for i, c in enumerate(claims, 1):
                lines.append(f"  {i}. [{c.claim_type}] {c.claim_text[:100]}")
                if c.expected_value:
                    lines.append(f"     Expected: {c.expected_value}")
            return "\n".join(lines)
        if action == "reproduce":
            text = (args or {}).get("text", "")
            title = (args or {}).get("title", "Untitled")
            if not text:
                return "Provide paper text to reproduce."
            report = await asyncio.get_event_loop().run_in_executor(
                self._tool_executor,
                lambda: re.reproduce_paper(text, title)
            )
            return report.summary
        if action == "reports":
            reports = re.get_reports()
            if not reports:
                return "No reproducibility reports yet."
            lines = [f"Reports ({len(reports)}):", ""]
            for r in reports[-5:]:
                lines.append(f"  {r['paper_title']}: Score={r['overall_score']:.1%}")
            return "\n".join(lines)
        return "Actions: extract, reproduce, reports"

    @register_tool("scientist_experiment_selector")
    async def _tool_scientist_experiment_selector(self, args):
        """Bayesian optimal experiment selection."""
        if not _scientist_aes_ok:
            return "active_experiment_selector module not loaded."
        action = (args or {}).get("action", "select").strip().lower()
        aes = get_experiment_selector()
        if aes is None:
            return "experiment selector unavailable."
        if action == "add_hypothesis":
            title = (args or {}).get("title", "")
            desc = (args or {}).get("description", "")
            if not title:
                return "Provide a hypothesis title."
            h = aes.add_hypothesis(title, desc)
            return f"Added hypothesis: {h.title} (id={h.id})"
        if action == "add_experiment":
            name = (args or {}).get("name", "")
            desc = (args or {}).get("description", "")
            hyp_ids = (args or {}).get("hypothesis_ids", [])
            cost = float((args or {}).get("cost", 1.0))
            if not name:
                return "Provide an experiment name."
            from scientist.active_experiment_selector import CandidateExperiment
            exp = CandidateExperiment(name, desc, hyp_ids, cost)
            aes.add_candidate(exp)
            return f"Added experiment: {exp.name} (cost={exp.cost})"
        if action == "select":
            best = aes.select_next()
            if not best:
                return "No candidate experiments available."
            return f"Recommended: {best.name}\nExpected IG: {best.expected_information_gain:.4f}\nUtility: {best.utility_score:.4f}"
        if action == "record":
            exp_name = (args or {}).get("experiment_name", "")
            success = (args or {}).get("success", True)
            obs = (args or {}).get("observations", "")
            # Find experiment by name
            for exp in aes._experiments:
                if exp.name == exp_name:
                    result = aes.record_result(exp, success, observations=obs)
                    return f"Recorded: {json.dumps(result, indent=2)}"
            return f"Experiment '{exp_name}' not found."
        if action == "rank":
            ranked = aes.rank_hypotheses()
            lines = ["Hypothesis Rankings:", ""]
            for h in ranked[:10]:
                ci = h.get("credible_interval", [0, 0])
                lines.append(f"  #{h['rank']} {h['title']}: mean={h['mean']:.3f} CI=[{ci[0]:.2f}, {ci[1]:.2f}]")
            return "\n".join(lines)
        if action == "status":
            summary = aes.get_summary()
            return json.dumps(summary, indent=2, default=str)
        return "Actions: add_hypothesis, add_experiment, select, record, rank, status"

    @register_tool("scientist_cross_domain")
    async def _tool_scientist_cross_domain(self, args):
        """Find cross-domain analogies and generate hypotheses."""
        if not _scientist_cdc_ok:
            return "cross_domain_connector module not loaded."
        action = (args or {}).get("action", "analogy").strip().lower()
        cdc = get_cross_domain_connector()
        if cdc is None:
            return "cross domain connector unavailable."
        if action == "analogy":
            concept = (args or {}).get("concept", "")
            src_domain = (args or {}).get("source_domain", "")
            tgt_domain = (args or {}).get("target_domain", "")
            if not concept:
                return "Provide a concept to find analogies for."
            analogies = cdc.find_analogies(concept, src_domain, tgt_domain)
            if not analogies:
                return f"No analogies found for '{concept}'."
            lines = [f"Analogies for '{concept}':", ""]
            for a in analogies[:5]:
                lines.append(f"  {a.source_concept} ({a.source_domain}) -> {a.target_concept} ({a.target_domain})")
                lines.append(f"    Strength: {a.strength:.2f}")
                if a.transfer_suggestions:
                    lines.append(f"    Transfer: {a.transfer_suggestions[0][:80]}")
                lines.append("")
            return "\n".join(lines)
        if action == "hypothesis":
            concept = (args or {}).get("concept", "")
            src_domain = (args or {}).get("source_domain", "")
            tgt_domain = (args or {}).get("target_domain", "")
            if not concept:
                return "Provide a concept."
            hyp = cdc.generate_cross_domain_hypothesis(concept, src_domain, tgt_domain)
            lines = [f"Cross-Domain Hypothesis:", ""]
            lines.append(f"  {hyp.get('hypothesis', 'N/A')}")
            lines.append(f"  Confidence: {hyp.get('confidence', 0):.2f}")
            if "testable_predictions" in hyp:
                lines.append("  Predictions:")
                for p in hyp["testable_predictions"]:
                    lines.append(f"    - {p}")
            return "\n".join(lines)
        if action == "chain":
            concept = (args or {}).get("concept", "")
            src_domain = (args or {}).get("source_domain", "")
            tgt_domain = (args or {}).get("target_domain", "")
            if not concept:
                return "Provide a concept."
            chains = cdc.find_analogy_chain(concept, src_domain, tgt_domain)
            if not chains:
                return f"No analogy chains found."
            lines = [f"Analogy Chains for '{concept}':", ""]
            for i, chain in enumerate(chains[:3], 1):
                path = f"{chain[0].source_concept}({chain[0].source_domain})"
                for a in chain:
                    path += f" -> {a.target_concept}({a.target_domain})"
                lines.append(f"  {i}. {path}")
            return "\n".join(lines)
        if action == "domains":
            domains = cdc.list_domains()
            lines = ["Scientific Domains:", ""]
            for d in domains:
                lines.append(f"  {d['name']}: {', '.join(d['concepts'][:5])}")
            return "\n".join(lines)
        if action == "history":
            analogies = cdc.get_historical_analogies()
            lines = ["Historical Cross-Domain Transfers:", ""]
            for a in analogies:
                lines.append(f"  {a['source']} -> {a['target']}: {a['concept']}")
                lines.append(f"    Impact: {a['impact']} | Strength: {a['strength']}")
            return "\n".join(lines)
        return "Actions: analogy, hypothesis, chain, domains, history"

    @register_tool("scientist_lab_notebook")
    async def _tool_scientist_lab_notebook(self, args):
        """Digital lab notebook for experiment tracking."""
        if not _scientist_notebook_ok:
            return "lab_notebook module not loaded."
        action = (args or {}).get("action", "list").strip().lower()
        nb = get_lab_notebook()
        if nb is None:
            return "lab notebook unavailable."
        if action == "create":
            title = (args or {}).get("title", "")
            hyp = (args or {}).get("hypothesis", "")
            method = (args or {}).get("method", "")
            domain = (args or {}).get("domain", "")
            tags = (args or {}).get("tags", [])
            if not title:
                return "Provide an entry title."
            entry = nb.create_entry(title, hyp, method, domain, tags)
            return f"Created entry: {entry.title} (id={entry.id})"
        if action == "observe":
            entry_id = (args or {}).get("entry_id", "")
            text = (args or {}).get("text", "")
            obs_type = (args or {}).get("obs_type", "note")
            entry = nb.get_entry(entry_id)
            if not entry:
                return f"Entry '{entry_id}' not found."
            entry.add_observation(text, obs_type)
            nb._save_state()
            return f"Observation recorded: {text[:80]}"
        if action == "measure":
            entry_id = (args or {}).get("entry_id", "")
            name = (args or {}).get("name", "")
            value = float((args or {}).get("value", 0))
            unit = (args or {}).get("unit", "")
            entry = nb.get_entry(entry_id)
            if not entry:
                return f"Entry '{entry_id}' not found."
            entry.add_measurement(name, value, unit)
            nb._save_state()
            return f"Measurement recorded: {name} = {value} {unit}"
        if action == "complete":
            entry_id = (args or {}).get("entry_id", "")
            results = (args or {}).get("results", "")
            conclusion = (args or {}).get("conclusion", "")
            entry = nb.get_entry(entry_id)
            if not entry:
                return f"Entry '{entry_id}' not found."
            if results:
                entry.results = results
            if conclusion:
                entry.conclusion = conclusion
            entry.set_status("completed")
            nb._save_state()
            return f"Entry completed: {entry.title}"
        if action == "search":
            query = (args or {}).get("query", "")
            status = (args or {}).get("status", "")
            domain = (args or {}).get("domain", "")
            entries = nb.search_entries(query, status, domain)
            return nb.format_search_results(entries)
        if action == "recent":
            days = int((args or {}).get("days", 7))
            entries = nb.get_recent(days)
            return nb.format_search_results(entries)
        if action == "show":
            entry_id = (args or {}).get("entry_id", "")
            entry = nb.get_entry(entry_id)
            if not entry:
                return f"Entry '{entry_id}' not found."
            return nb.format_entry(entry)
        if action == "summary":
            date = (args or {}).get("date", "")
            summary = nb.get_daily_summary(date)
            return json.dumps(summary, indent=2, default=str)
        if action == "stats":
            stats = nb.get_stats()
            return json.dumps(stats, indent=2)
        return "Actions: create, observe, measure, complete, search, recent, show, summary, stats"

    async def _process_tool_calls_bg(self, tool_call):
        session = self.session
        if not session:
            return
        fcs = list(tool_call.function_calls)
        if not fcs:
            return

        self._tool_executing = True
        self.ui._is_busy = True
        self.ui._interrupt_requested.clear()

        # Single tool — run directly (no overhead)
        if len(fcs) == 1:
            try:
                resp = await self._execute_tool(fcs[0])
                fn_responses = [resp]
            except Exception as e:
                print(f"[RUMI] {fcs[0].name} error: {e}", flush=True)
                fn_responses = [types.FunctionResponse(
                    id=fcs[0].id, name=fcs[0].name,
                    response={"result": f"Tool crashed: {e}"})]
        else:
            # Multiple tools — run ALL in parallel via asyncio.gather
            print(f"[RUMI] Parallel dispatch: {len(fcs)} tools — "
                  f"{', '.join(fc.name for fc in fcs)}", flush=True)

            async def _safe_exec(fc):
                try:
                    return await self._execute_tool(fc)
                except Exception as e:
                    print(f"[RUMI] {fc.name} error: {e}", flush=True)
                    return types.FunctionResponse(
                        id=fc.id, name=fc.name,
                        response={"result": f"Tool crashed: {e}"})

            fn_responses = list(await asyncio.gather(
                *[_safe_exec(fc) for fc in fcs],
                return_exceptions=False,
            ))

            # Log any errors
            for fc, resp in zip(fcs, fn_responses):
                if isinstance(resp, types.FunctionResponse):
                    r = resp.response.get("result", "") if resp.response else ""
                    if "[TOOL_ERROR]" in r:
                        print(f"[RUMI] {fc.name} returned error", flush=True)

        if self._session_dead or not self.session:
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            self._tool_executing = False
            self.ui._is_busy = False
            self.ui._message_queue_count = 0
            return
        try:
            await session.send_tool_response(function_responses=fn_responses)
            self._last_send_time = time.time()
        except Exception as e:
            err_str = str(e).lower()
            if "1008" in err_str:
                print(f"[RUMI] 1008 on tool response — session may recover", flush=True)
            elif _is_ws_dead_error(err_str):
                self._session_dead = True
            else:
                print(f"[RUMI] Tool response error: {e}", flush=True)
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            # v10.6 FIX-19: Check shutdown flag even when response send fails
            if self._schedule_shutdown:
                self._schedule_shutdown = False
                def _shutdown_err():
                    time.sleep(2)
                    try:
                        if _brain_coordinator_ok and get_memory_coordinator:
                            get_memory_coordinator().save_all()
                        elif get_brain:
                            brain = get_brain()
                            if brain:
                                brain.save()
                    except Exception:
                        pass
                    self._write_health()
                    self._session_dead = True
                threading.Thread(target=_shutdown_err, daemon=True).start()
            self._tool_executing = False
            self.ui._is_busy = False
            self.ui._message_queue_count = 0
            return
        if self._schedule_shutdown:
            self._schedule_shutdown = False
            def _shutdown():
                time.sleep(2)
                try:
                    if hasattr(self.telegram, 'send_response'):
                        self.telegram.send_response("RUMI shutting down.")
                except Exception:
                    pass
                try:
                    if _brain_coordinator_ok and get_memory_coordinator:
                        get_memory_coordinator().save_all()
                    elif get_brain:
                        brain = get_brain()
                        if brain:
                            brain.save()
                except Exception:
                    pass
                self._write_health()
                self._session_dead = True
            threading.Thread(target=_shutdown, daemon=True).start()

        # ── Cleanup: reset busy, drain message queue ──
        self._tool_executing = False
        self.ui._is_busy = False
        self.ui._message_queue_count = 0
        if self._queued_texts:
            q = list(self._queued_texts)
            self._queued_texts.clear()
            for qt in q:
                self._on_text_command(qt)

    async def _send_realtime(self):
        try:
            while True:
                if self._session_dead:
                    raise _SessionDead("session_dead")
                msg = await self.out_queue.get()
                if self._session_dead or self.session is None:
                    raise _SessionDead("session dead after queue get")
                try:
                    async with self._send_lock:
                        await self.session.send_realtime_input(media=msg)
                    self._last_send_time = time.time()
                    self._audio_drop_count = 0
                except Exception as e:
                    err_str = str(e).lower()
                    if _is_ws_dead_error(err_str):
                        self._session_dead = True
                        raise _SessionDead(str(e))
                    self._audio_drop_count += 1
                    if self._audio_drop_count > 20:
                        self._session_dead = True
                        raise _SessionDead(f"Too many send errors: {e}")
                    await asyncio.sleep(0.5)
        except _SessionDead:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._session_dead = True
            raise _SessionDead(str(e))

    async def _keepalive(self):
        silence = {"data": b'\x00' * (CHUNK_SIZE * 2), "mime_type": "audio/pcm"}
        try:
            while True:
                if self.session is None or self._session_dead:
                    raise _SessionDead("keepalive: session ended")
                await asyncio.sleep(KEEPALIVE_INTERVAL)
                if self.session is None or self._session_dead:
                    raise _SessionDead("keepalive: session ended")
                now = time.time()
                if now - self._last_send_time < KEEPALIVE_INTERVAL - 1:
                    continue
                if now - self._last_audio_time < KEEPALIVE_INTERVAL:
                    continue
                with self._speaking_lock:
                    if self._is_speaking:
                        continue
                try:
                    async with self._send_lock:
                        await self.session.send_realtime_input(media=silence)
                    self._last_send_time = time.time()
                except Exception as e:
                    err_str = str(e).lower()
                    if _is_ws_dead_error(err_str):
                        self._session_dead = True
                        raise _SessionDead(f"keepalive: {err_str[:50]}")
        except asyncio.CancelledError:
            raise

    async def _listen_audio(self):
        loop = asyncio.get_running_loop()
        while True:
            if self._session_dead or self.session is None:
                raise _SessionDead("listen_audio: session ended")

            def callback(indata, frames, time_info, status):
                if self.session is None or self._session_dead:
                    return
                with self._speaking_lock:
                    if self._is_speaking or self.ui.muted:
                        return
                    if time.time() - self._speaking_ended_at < 0.5:
                        return
                chunk = indata.tobytes()
                try:
                    loop.call_soon_threadsafe(
                        _safe_queue_put, self.out_queue,
                        {"data": chunk, "mime_type": "audio/pcm"})
                except RuntimeError:
                    return

            try:
                with sd.InputStream(
                    samplerate=SEND_SAMPLE_RATE, channels=CHANNELS,
                    dtype="int16", blocksize=CHUNK_SIZE, callback=callback,
                ):
                    while True:
                        if self.session is None or self._session_dead:
                            raise _SessionDead("listen_audio: session ended")
                        await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise
            except _SessionDead:
                raise
            except Exception as e:
                if self._session_dead or self.session is None:
                    raise _SessionDead("listen_audio: session ended")
                print(f"[RUMI] Mic stream error: {e} — retrying in 2s", flush=True)
                try:
                    self.speak("Sir, microphone stream interrupted. Reconnecting.")
                except Exception:
                    pass
                await asyncio.sleep(2)

    async def _receive_audio(self):
        out_buf, in_buf = [], []
        _audio_buf = []
        count = 0
        try:
            while True:
                async for response in self.session.receive():
                    count += 1
                    if self._shutdown_event and self._shutdown_event.is_set():
                        return

                    if response.data:
                        self._last_audio_time = time.time()
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        if self._modes["focus"]:
                            _audio_buf.append(response.data)
                        else:
                            try:
                                self.audio_in_queue.put_nowait(response.data)
                            except asyncio.queues.QueueFull:
                                pass

                    if response.server_content:
                        sc = response.server_content
                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)
                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)
                        if sc.turn_complete:
                            full_in = " ".join(in_buf).strip()

                            # Publish USER_INPUT from mic to Global Workspace
                            if full_in and self._workspace and _brain_workspace_ok:
                                try:
                                    await self._workspace.publish(
                                        WorkspaceEvent(
                                            source="mic_input", type=WsEventType.USER_INPUT,
                                            content={"text": full_in, "source": "mic"},
                                        ),
                                        urgency=0.7, goal_relevance=0.5, emotional_salience=0.3,
                                    )
                                except Exception:
                                    pass

                            should_play = True
                            if self._modes["focus"]:
                                if "rumi" not in full_in.lower():
                                    should_play = False
                                    _audio_buf.clear()
                                    if full_in:
                                        self.ui.write_log(f"[Focus] Ignored: {full_in}")

                            if should_play:
                                for chunk in _audio_buf:
                                    try:
                                        self.audio_in_queue.put_nowait(chunk)
                                    except asyncio.QueueFull:
                                        break
                                _audio_buf.clear()
                                full_out = " ".join(out_buf).strip()
                                if full_out:
                                    self.ui.write_log(f"Rumi: {full_out}")
                                    try:
                                        if hasattr(self.telegram, 'send_response'):
                                            self.telegram.send_response(full_out)
                                    except Exception:
                                        pass

                                in_snapshot = list(in_buf)
                                async def _flush_input(b):
                                    await asyncio.sleep(0.5)
                                    try:
                                        full_in_text = " ".join(b).strip()
                                        if full_in_text:
                                            self.ui.write_log(f"You: {full_in_text}")
                                    except Exception:
                                        pass
                                asyncio.create_task(_flush_input(in_snapshot))

                                # v10.6 — track user interests for curiosity mirroring
                                try:
                                    if (self._curiosity
                                            and not isinstance(self._curiosity, _NullModule)
                                            and full_in):
                                        self._curiosity.track_user_topic(full_in)
                                except Exception:
                                    pass

                                # Self-awareness: observe voice input through theory of mind
                                try:
                                    if (self._self_awareness
                                            and not isinstance(self._self_awareness, _NullModule)
                                            and full_in):
                                        self._self_awareness.process_interaction(
                                            CognitiveEvent.USER_INPUT if CognitiveEvent else "user_input",
                                            {"text": full_in, "source": "mic"},
                                        )
                                except Exception:
                                    pass

                            _audio_buf.clear()
                            out_buf.clear()
                            in_buf = []

                            if self._turn_done_event:
                                self._turn_done_event.set()

                    if response.tool_call:
                        task = asyncio.create_task(
                            self._process_tool_calls_bg(response.tool_call))
                        self._pending_tool_tasks.add(task)
                        task.add_done_callback(self._pending_tool_tasks.discard)

                    try:
                        if hasattr(self.telegram, 'pending_response') and self.telegram.pending_response:
                            if hasattr(self.telegram, 'send_response'):
                                self.telegram.send_response("Done.")
                    except Exception:
                        pass

        except asyncio.CancelledError:
            raise
        except Exception as e:
            err_str = str(e).lower()
            if "1008" in err_str:
                print(f"[RUMI] 1008 policy violation — server rejected message", flush=True)
            elif not _is_ws_dead_error(err_str):
                print(f"[RUMI] Recv: {e}", flush=True)
            self._session_dead = True
            raise _SessionDead("receive_audio: error")
        finally:
            out_buf.clear()
            in_buf.clear()
            _audio_buf.clear()
            if self._pending_tool_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._pending_tool_tasks, return_exceptions=True),
                        timeout=10.0)
                except asyncio.TimeoutError:
                    for t in self._pending_tool_tasks:
                        t.cancel()
                    self._pending_tool_tasks.clear()

        self._session_dead = True
        raise _SessionDead("receive_audio: connection closed")

    async def _play_audio(self):
        loop = asyncio.get_running_loop()
        _last_chunk_time = 0.0
        while True:
            if self.session is None or self._session_dead:
                self.set_speaking(False)
                raise _SessionDead("play_audio: session ended")
            try:
                stream = sd.RawOutputStream(
                    samplerate=RECEIVE_SAMPLE_RATE, channels=CHANNELS,
                    dtype="int16", blocksize=CHUNK_SIZE)
                stream.start()
                try:
                    while True:
                        if self._shutdown_event and self._shutdown_event.is_set():
                            self.set_speaking(False)
                            return
                        if self.session is None or self._session_dead:
                            self.set_speaking(False)
                            raise _SessionDead("play_audio: session ended")
                        try:
                            chunk = await asyncio.wait_for(
                                self.audio_in_queue.get(), timeout=0.1)
                        except asyncio.TimeoutError:
                            if self._is_speaking and _last_chunk_time > 0:
                                if time.time() - _last_chunk_time > 30.0:
                                    self.set_speaking(False)
                            if (self._turn_done_event
                                    and self._turn_done_event.is_set()
                                    and self.audio_in_queue.empty()):
                                self.set_speaking(False)
                                self._turn_done_event.clear()
                            continue
                        self._last_audio_time = time.time()
                        _last_chunk_time = time.time()
                        self.set_speaking(True)
                        await loop.run_in_executor(
                            self._audio_executor, stream.write, chunk)
                finally:
                    try:
                        stream.stop()
                    except Exception:
                        pass
                    try:
                        stream.close()
                    except Exception:
                        pass
                    self.set_speaking(False)
            except asyncio.CancelledError:
                self.set_speaking(False)
                raise
            except _SessionDead:
                raise
            except Exception as e:
                self.set_speaking(False)
                if self._session_dead:
                    raise _SessionDead("play_audio: session ended after error")
                await asyncio.sleep(2)

    async def _telegram_poll_safe(self):
        while True:
            try:
                if self._session_dead:
                    raise _SessionDead("telegram: session dead")
                if hasattr(self.telegram, 'poll'):
                    result = self.telegram.poll()
                    if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                        await result
                else:
                    await asyncio.sleep(60)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except _SessionDead:
                raise
            except Exception as e:
                if self._session_dead:
                    raise _SessionDead("telegram: session dead after error")
                await asyncio.sleep(30)

    async def run(self):
        try:
            api_key = _get_api_key()
        except Exception as e:
            self.ui.write_log(f"FATAL: API key error — {e}")
            return

        client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1beta"})
        reconnect_delay = 1.0
        consecutive_failures = 0

        while True:
            session_cm = None
            session_start = time.time()
            try:
                self._session_dead = False
                self.ui.set_state("THINKING")

                try:
                    config = self._build_config()
                except Exception:
                    config = types.LiveConnectConfig(
                        response_modalities=["AUDIO"],
                        system_instruction=_load_system_prompt(),
                        tools=[{"function_declarations": TOOL_DECLARATIONS}],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name="Aoede")
                            )
                        ),
                    )

                session_cm = client.aio.live.connect(model=LIVE_MODEL, config=config)
                try:
                    session = await asyncio.wait_for(
                        session_cm.__aenter__(), timeout=30.0)
                except asyncio.TimeoutError:
                    session_cm = None
                    raise

                self.session = session
                self._loop = asyncio.get_running_loop()
                self._send_lock = asyncio.Lock()
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=1000)
                self._turn_done_event = asyncio.Event()
                self._shutdown_event = asyncio.Event()
                self._action_source = "mic"
                self._last_audio_time = 0.0
                self._last_send_time = time.time()
                self._last_send_content_time = 0.0
                self._pending_tool_tasks = set()
                self._audio_drop_count = 0
                self._session_count += 1

                self._health["status"] = "connected"
                self._health["connected"] = True
                self._health["session_count"] = self._session_count
                self._write_health()

                reconnect_delay = 1.0
                consecutive_failures = 0

                try:
                    if self._self_model and not isinstance(self._self_model, _NullModule):
                        self._self_model.start_session()
                        self._self_model.update_state(
                            current_status="connected",
                            focus_mode=False, think_mode=False)
                except Exception:
                    pass
                try:
                    if self._curiosity and not isinstance(self._curiosity, _NullModule):
                        self._curiosity.update_curiosity_queue(
                            active_inference_engine=self._active_inference
                                if not isinstance(self._active_inference, _NullModule)
                                else None)
                except Exception:
                    pass

                # Index vector memory on session start (background)
                try:
                    if _brain_vector_ok and get_vector_memory:
                        def _index_vectors():
                            try:
                                vm = get_vector_memory()
                                if vm:
                                    vm.index_all_stores()
                            except Exception:
                                pass
                        threading.Thread(target=_index_vectors, daemon=True).start()
                except Exception:
                    pass

                self.ui.set_state("LISTENING")
                self.ui.write_log("SYS: RUMI online.")
                self.ui.on_focus_mode_toggle = self.set_focus_mode
                self.ui.on_think_mode_toggle = self.set_think_mode
                self.ui.on_deep_dive_toggle = self.set_deep_dive_mode

                try:
                    self._audit.log(
                        action="session_connected", status="ok",
                        source="system",
                        reason="Gemini Live session established")
                except Exception:
                    pass

                # v10.6 — idle exploration task
                async def _idle_exploration():
                    """Check periodically if RUMI should explore during idle."""
                    while self.session and not self._session_dead:
                        await asyncio.sleep(300)
                        try:
                            if (self._curiosity
                                    and not isinstance(self._curiosity, _NullModule)
                                    and self._curiosity.should_idle_explore()):
                                task = self._curiosity.get_idle_exploration_task()
                                if task:
                                    self.ui.write_log(
                                        f"SYS: Idle exploration — {task['target']}")
                        except Exception:
                            pass

                results = await asyncio.gather(
                    self._send_realtime(),
                    self._listen_audio(),
                    self._receive_audio(),
                    self._play_audio(),
                    self._keepalive(),
                    self._telegram_poll_safe(),
                    _idle_exploration(),
                    return_exceptions=True,
                )

                session_life = time.time() - session_start
                task_names = [
                    "_send_realtime", "_listen_audio", "_receive_audio",
                    "_play_audio", "_keepalive", "_telegram_poll_safe",
                    "_idle_exploration"
                ]
                for tname, res in zip(task_names, results):
                    if isinstance(res, _SessionDead):
                        self.ui.write_log(f"SYS: {tname} ended session")
                    elif isinstance(res, Exception):
                        self.ui.write_log(f"ERR: {tname}: {type(res).__name__}: {res}")
                        traceback.print_exception(type(res), res, res.__traceback__)

                if session_life < 30:
                    self.ui.write_log(f"WARN: Short session ({session_life:.1f}s)")

            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError:
                consecutive_failures += 1
                self.ui.write_log("ERR: Connect timed out (30s)")
            except Exception as e:
                consecutive_failures += 1
                err_str = str(e).lower()
                self.ui.write_log(f"ERR: {str(e)[:200]}")
                if any(k in err_str for k in ("api_key", "invalid", "quota", "permission")):
                    self.ui.write_log(f"FATAL: {e}")
                    self._health["status"] = "fatal_error"
                    self._write_health()
                    return
            finally:
                if session_cm is not None:
                    try:
                        await session_cm.__aexit__(None, None, None)
                    except Exception:
                        pass
                try:
                    if _brain_coordinator_ok and get_memory_coordinator:
                        get_memory_coordinator().save_all()
                    elif get_brain:
                        brain = get_brain()
                        if brain:
                            brain.save()
                except Exception:
                    pass
                tasks_to_cancel = list(self._pending_tool_tasks)
                self._pending_tool_tasks.clear()
                for task in tasks_to_cancel:
                    task.cancel()
                if tasks_to_cancel:
                    await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
                self.session = None
                self.set_speaking(False)
                for q_name in ("audio_in_queue", "out_queue"):
                    q = getattr(self, q_name, None)
                    if q:
                        while not q.empty():
                            try:
                                q.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                self._health["connected"] = False
                self._health["status"] = "reconnecting"
                self._write_health()

            delay = min(
                max(reconnect_delay, 5.0) * (2 ** max(0, consecutive_failures - 1)),
                MAX_RECONNECT_DELAY)
            self.ui.write_log(f"SYS: Reconnecting in {delay:.0f}s...")
            await asyncio.sleep(delay)


    # ── Clap listener ─────────────────────────────────────────────────────
    def start_clap_listener(ui):
        import numpy as np

        THRESHOLD = 8000
        SETTLE_TIME = 0.6  # Wait this long after last clap before acting
        clap_times = []
        _clap_lock = threading.Lock()
        _pending_timer = [None]  # mutable container for timer reference

        def _act_on_claps(count):
            """Execute action based on number of claps detected."""
            try:
                if count == 1:
                    # 1-clap: toggle mute
                    ui.toggle_mute()
                elif count == 2:
                    # 2-clap: wake up (unmute if muted)
                    if ui.muted:
                        ui.toggle_mute()  # unmute
                        ui.write_log("SYS: Woken up by double clap.")
                        ui.show_toast("WAKE UP", 1.5)
                    else:
                        # Already unmuted — toggle mute off as fallback
                        ui.toggle_mute()
                elif count >= 3:
                    # 3-clap: toggle focus mode
                    ui._toggle_focus_mode()
            except Exception:
                pass

        def _settle_and_act():
            """Called after settle timer expires — count claps and act."""
            with _clap_lock:
                now = time.time()
                # Keep only claps from the last 2 seconds
                recent = [t for t in clap_times if now - t < 2.0]
                clap_times.clear()
                clap_times.extend(recent)
                cnt = len(clap_times)
                _pending_timer[0] = None
            if cnt > 0:
                _act_on_claps(cnt)

        def callback(indata, frames, time_info, status):
            try:
                if indata is None or indata.size == 0:
                    return
                chunk = indata[:, 0].astype(np.float32)
                peak = np.max(np.abs(chunk))
                avg = np.mean(np.abs(chunk))
                if peak < THRESHOLD or peak < avg * 10:
                    return
                fft = np.abs(np.fft.rfft(chunk))
                freqs = np.fft.rfftfreq(len(chunk), d=1.0 / 16000)
                low = np.mean(fft[(freqs >= 100) & (freqs < 1000)])
                mid = np.mean(fft[(freqs >= 1000) & (freqs < 4000)])
                high = np.mean(fft[(freqs >= 4000) & (freqs < 8000)])
                broadband = (mid > low * 0.5) and (high > low * 0.3)
                if not broadband:
                    return
                now = time.time()
                with _clap_lock:
                    # Always record the clap — no cooldown blocking
                    clap_times.append(now)
                    # Cancel pending timer and restart
                    if _pending_timer[0] is not None:
                        _pending_timer[0].cancel()
                    _pending_timer[0] = threading.Timer(SETTLE_TIME, _settle_and_act)
                    _pending_timer[0].daemon = True
                    _pending_timer[0].start()
            except Exception:
                pass

        with sd.InputStream(samplerate=16000, channels=1, dtype="int16", callback=callback):
            while True:
                time.sleep(0.1)


    # ── Entry point ───────────────────────────────────────────────────────
    def main():
        if init_learnings_file:
            try:
                init_learnings_file()
            except Exception:
                pass
        if get_learning_engine:
            try:
                get_learning_engine()
            except Exception:
                pass

        ui = RumiUI("rumi_face.png")

        try:
            _get_api_key()
            ui.write_log("SYS: API key validated")
        except Exception as e:
            ui.write_log(f"ERR: API key invalid — {e}")

        has_input, has_output = _check_audio_devices()
        if not has_input:
            ui.write_log("SYS: No microphone detected. Use text input.")
        if not has_output:
            ui.write_log("SYS: No speaker detected. Responses text-only.")

        rumi_instance = None

        def runner():
            nonlocal rumi_instance
            try:
                ui.wait_for_api_key()
                rumi_instance = RumiLive(ui)
                asyncio.run(rumi_instance.run())
                # v10.6 FIX-20: Log when run() exits normally (fatal error)
                ui.write_log("SYS: RUMI session ended. Check API key and restart.")
            except Exception as e:
                traceback.print_exc()
                try:
                    ui.write_log(f"Fatal: {e}")
                except Exception:
                    pass

        # clap listener skipped (requires class method access in static context)
        t = threading.Thread(target=runner, daemon=True)
        t.start()

        def on_closing():
            if rumi_instance:
                try:
                    rumi_instance._audit.log(
                        action="session_end", status="ok",
                        source="system", reason="Window closed")
                except Exception:
                    pass
                # v10.6 — flush audit logger on shutdown
                try:
                    rumi_instance._audit.shutdown()
                except Exception:
                    pass
                # v10.6 — stop permission manager cleanup thread
                try:
                    rumi_instance._perm_mgr.shutdown()
                except Exception:
                    pass
                try:
                    if get_brain:
                        brain = get_brain()
                        if brain:
                            brain.save()
                    if update_memory and get_brain:
                        b = get_brain()
                        if b:
                            update_memory(b.all_memories())
                except Exception:
                    pass
                rumi_instance._write_health()
                try:
                    rumi_instance.shutdown_executors()
                except Exception:
                    pass
                # Shutdown Global Workspace
                if rumi_instance._workspace:
                    try:
                        rumi_instance._workspace.shutdown()
                    except Exception:
                        pass
            try:
                ui._running = False
            except AttributeError:
                pass

        try:
            import time as _t
            while getattr(ui, '_running', False):
                _t.sleep(0.5)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    RumiLive.main()


def main():
    """Module-level entry point for the rumi CLI."""
    RumiLive.main()
