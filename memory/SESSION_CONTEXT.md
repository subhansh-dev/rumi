# Session Context — June 11, 2026

## Last Session Summary
- Focus: Multi-provider LLM stack, recurrent discovery loop, math chain, cross-validation, bug fixes
- Duration: ~48 hours (June 9-11, 2026)
- 3 complete runs: Simulation hypothesis (77/100 B), Alzheimer drug discovery (74/100 B), Vacuum energy (67/100 B)
- Added 8 LLM providers: NVIDIA Nemotron 550B, Kimi K2.6, DeepSeek V4 Pro (NVIDIA + Fireworks), Xiaomi MiMo, Cerebras, Groq, Gemini
- Implemented recurrent discovery loop (Phases 6-8, 3 iterations with convergence)
- Implemented Math Chain (Phase 6.5, domain-aware equation derivation)
- Implemented Cross-Validation (Phase 11.6, holdout paper testing)
- Fixed 6 bugs: literature search pollution, domain-aware completeness, loop history, theories scope, novelty filter type error, molecule error message
- Claude Fable 5 used for critical phases (curious questioning) — dramatically better reframe quality

## Provider Stack (8 providers)
  1. NVIDIA Nemotron 3 Ultra 550B (primary) — nvapi key 1
  2. Kimi K2.6 (math reasoning) — nvapi key 2
  3. DeepSeek V4 Pro (NVIDIA) — nvapi key 3
  4. DeepSeek V4 Pro (Fireworks, $6 credits) — fw key
  5. Xiaomi MiMo v2.5 Pro — tp key
  6. Cerebras gpt-oss-120b (6 keys)
  7. Groq llama-3.3-70b (3 keys, 1&2 dead)
  8. Gemini 2.5 Flash (4 keys, 60s timeout)

## Key Files Modified
- discovery/llm_client.py — 8 providers, retry loop, math routing, Gemini timeout
- discovery/discovery_pipeline_v2.py — recurrent loop, math chain, cross-validation
- discovery/mechanism_generator.py — derivation enforcement, LLM reasoning retry
- discovery/missing_variable_generator.py — LLM reasoning retry
- discovery/mechanism_completeness.py — domain-aware criteria
- discovery/empc_pipeline.py — improved mechanism grounding
- discovery/novelty_checker.py — str() guard
- discovery/json_extract.py — ALIAS_MAP + canonical extraction
- discovery/cross_validation.py — NEW MODULE
- discovery/math_chain.py — NEW MODULE
- run_discovery.py — original_topic parameter

## Open Issues
1. Mechanism completeness 0% on Track B (MechanismDiscoveryEngine fallback)
2. EMPC low on Track B (cascading from shallow fallback mechanisms)
3. No intermediate report saving (crash loses all work)
4. Canonical JSON extraction could be smarter (semantic checking needed)
5. NVIDIA 500 errors (temporary, provider recovers)
6. Groq keys 1&2 dead (401) — need replacement

## User Preferences
- Always report bugs before fixing — user decides what to fix
- Don't kill running processes unless absolutely necessary
- Distinguish code bugs from model quality issues
- User wants creative freedom in Phase 0 (curious questioning)
- Domain should be specified with --domain flag for best results
