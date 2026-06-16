"""
structured_report.py - Generate Nature/Science-style structured reports.

Takes the raw pipeline report dict and produces a clean, readable,
publication-style structured report as a SEPARATE .txt file.

The raw JSON dump is NEVER modified - this is purely additive.
Domain-agnostic: works for all 17 domains.
"""

import textwrap
from datetime import datetime

DOMAIN_VALIDATION = {
    "physics": {"label": "Experimental / Observational Tests", "methods": [
        "Detector-based measurement with signal-to-noise analysis",
        "Numerical simulation (Monte Carlo, lattice, N-body)",
        "Astrophysical observation of predicted signatures",
        "Dimensional analysis and consistency checks"]},
    "space_astronomy": {"label": "Observational Verification Plan", "methods": [
        "Telescope observation at predicted wavelengths",
        "Spectroscopic analysis of predicted spectral features",
        "Time-domain monitoring for predicted variability",
        "Cross-matching with archival survey data (SDSS, Gaia, JWST)"]},
    "drug_discovery": {"label": "Experimental Validation Plan", "methods": [
        "In vitro binding assay (SPR, ITC, FP) to measure affinity",
        "Cellular degradation assay (DC50, Dmax, Western blot)",
        "Structural biology (cryo-EM, X-ray) of ternary complex",
        "Proteomics (mass spectrometry) for selectivity profiling",
        "In vivo pharmacokinetics and efficacy in animal models"]},
    "neuroscience": {"label": "Experimental Validation Plan", "methods": [
        "Electrophysiology (patch-clamp, multi-electrode array)",
        "Functional imaging (fMRI, calcium imaging)",
        "Optogenetic/chemogenetic manipulation for causal testing",
        "Behavioral assays with appropriate statistical power"]},
    "ecology": {"label": "Field Study Design", "methods": [
        "Field survey with stratified random sampling",
        "Long-term monitoring (minimum 3-5 year dataset)",
        "Experimental manipulation (exclosure, transplant)",
        "Statistical analysis with null models and power analysis",
        "Remote sensing / GIS for landscape-scale patterns"]},
    "materials_science": {"label": "Synthesis and Characterization Plan", "methods": [
        "Material synthesis under predicted conditions",
        "Structural characterization (XRD, TEM, SEM, AFM)",
        "Property measurement (mechanical, thermal, electrical)",
        "Computational validation (DFT, MD simulation)"]},
    "chemistry": {"label": "Experimental Verification Plan", "methods": [
        "Reaction optimization under predicted conditions",
        "Spectroscopic characterization (NMR, IR, MS)",
        "Kinetic measurement (rate constants, activation energy)",
        "Computational chemistry (DFT, ab initio)"]},
    "mathematics": {"label": "Proof and Verification Strategy", "methods": [
        "Formal proof construction with explicit axioms",
        "Computational verification on specific cases",
        "Counterexample search to test necessity of assumptions",
        "Connection to existing theorems and known results"]},
    "climate_energy": {"label": "Validation Plan", "methods": [
        "Climate model simulation (GCM, ESM)",
        "Paleoclimate proxy data comparison",
        "Satellite observation of predicted patterns",
        "Energy balance analysis and flux measurements"]},
    "public_health": {"label": "Epidemiological Validation Plan", "methods": [
        "Cohort study design with appropriate controls",
        "Statistical analysis (survival, regression, causal inference)",
        "Systematic review and meta-analysis",
        "Intervention trial design (RCT or quasi-experimental)"]},
}

DEFAULT_VALIDATION = {"label": "Validation Plan", "methods": [
    "Design domain-appropriate experiment or observation",
    "Collect data with appropriate controls and sample size",
    "Analyze with appropriate statistical framework",
    "Compare predictions against measured outcomes"]}


def _wrap(text, width=76, indent=0):
    if not text:
        return ""
    prefix = " " * indent
    lines = textwrap.wrap(str(text), width=width - indent)
    return "\n".join(prefix + line for line in lines) if lines else ""


def _trunc(text, max_len=300):
    text = str(text or "").strip()
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def _safe(d, key, default=""):
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def generate_structured_report(report):
    """Generate a Nature/Science-style structured report from pipeline output."""
    phases = report.get("phases", {})
    topic = report.get("topic", "Unknown Topic")
    domain = report.get("domain", "general")
    original_topic = report.get("original_topic", topic)
    duration = report.get("duration_seconds", 0)
    mode = report.get("mode", "full")
    timestamp = report.get("completed_at", datetime.now().isoformat())

    dcfg = DOMAIN_VALIDATION.get(domain, DEFAULT_VALIDATION)

    # Extract all data
    lit = phases.get("literature", {})
    papers = _safe(lit, "papers", [])
    if isinstance(papers, list) and papers and isinstance(papers[0], str):
        papers = []

    kg = phases.get("knowledge_graph", {})
    gaps = report.get("gaps", []) or _safe(phases.get("gap_detection", {}), "gaps", [])
    hvs = report.get("hidden_variables", []) or _safe(phases.get("hidden_variables", {}), "proposed", [])
    mechs = report.get("mechanisms", []) or _safe(phases.get("mechanism_generation", {}), "mechanisms", [])
    preds = report.get("accepted_predictions", []) or _safe(phases.get("prediction_engine", {}), "predictions", [])
    theories = report.get("theories", []) or _safe(phases.get("theory_competition", {}), "theories", [])

    theory_ph = phases.get("theory_competition", {})
    winner = _safe(theory_ph, "winner") or {}
    scoring = phases.get("discovery_scoring", {})
    peer = phases.get("peer_review", {})
    skeptic = phases.get("skeptic_review", {})
    conf = phases.get("confidence_scoring", {})
    claim = phases.get("claim_labeling", {})
    mc = phases.get("mechanism_completeness", {})
    classify = phases.get("discovery_classification", {})
    abstract_ph = phases.get("abstraction_compression", {})
    cf_ph = phases.get("counterfactual_reasoning", {})
    exp_ph = phases.get("experimental_validation", {})
    constraint = report.get("constraint", {})

    # Computed values
    disc_score = _safe(scoring, "discovery_score", 0)
    grade = _safe(scoring, "grade", "?")
    scores_d = _safe(scoring, "scores", {})
    strengths = _safe(scoring, "strengths", [])
    weaknesses = _safe(scoring, "weaknesses", [])
    adv_details = _safe(scoring, "adversarial_details", [])

    confidence = _safe(conf, "confidence", 0)
    claim_rel = _safe(claim, "reliability", 0)
    total_claims = _safe(claim, "total_claims", 0)
    validated = _safe(claim, "VALIDATED", 0)
    hypothetical = _safe(claim, "HYPOTHETICAL", 0)

    avg_comp = _safe(mc, "avg_completeness", 0)
    comp_complete = _safe(mc, "complete", 0)
    comp_total = _safe(mc, "total", 0)

    peer_score = _safe(peer, "overall_score", 0)
    peer_rec = _safe(peer, "recommendation", "")
    peer_summary = _safe(peer, "summary", "")
    major_issues = _safe(peer, "major_issues", [])

    skeptic_rec = _safe(skeptic, "recommendation", "")
    skeptic_conf = _safe(skeptic, "revised_confidence", 0)
    loop_hist = report.get("loop_history", [])
    unifying = _safe(abstract_ph, "unifying_principle", "")

    cfs = _safe(cf_ph, "counterfactuals", [])
    cf_supported = _safe(cf_ph, "supported", [])

    entities = _safe(kg, "entities", 0)
    relationships = _safe(kg, "relationships", 0)
    cross_domain = _safe(constraint, "cross_domain_connections", [])
    errors = report.get("errors", [])

    dur_str = f"{duration/3600:.1f}h" if duration > 3600 else f"{duration:.0f}s"

    # BUILD REPORT
    S = []
    eq = "=" * 76
    dash = "-" * 76

    # HEADER
    S.append(eq)
    S.append("  RUMI STRUCTURED DISCOVERY REPORT")
    S.append("  Autonomous AI-Driven Scientific Discovery")
    S.append(eq)
    S.append(f"  Generated: {timestamp[:19]}")
    S.append(f"  Pipeline: RUMI v2 ({mode} mode) | Duration: {dur_str}")
    S.append("")

    # 1. ABSTRACT
    S.append(dash)
    S.append("  1. ABSTRACT")
    S.append(dash)
    S.append("")
    S.append(_wrap(f"Topic: {original_topic}", 76, 2))
    w_name = _safe(winner, "name", "Unnamed theory")
    w_desc = _safe(winner, "description", _safe(winner, "mechanism", ""))
    w_type = _safe(winner, "type", "unknown")
    if w_name != "Unnamed theory":
        S.append(_wrap(f"Lead hypothesis: {w_name}", 76, 2))
    if w_desc:
        S.append(_wrap(_trunc(w_desc, 300), 76, 2))
    S.append(_wrap(f"Based on {len(papers)} papers, {len(hvs)} hidden variables, "
                   f"{len(mechs)} mechanisms, {len(preds)} predictions.", 76, 2))
    S.append(_wrap(f"Score: {disc_score:.0f}/100 (Grade: {grade}) | "
                   f"Confidence: {confidence:.0%}", 76, 2))
    if unifying:
        S.append(_wrap(f"Unifying principle: {_trunc(unifying, 200)}", 76, 2))
    S.append("")

    # 2. CONTEXT & LITERATURE
    S.append(dash)
    S.append("  2. CONTEXT & LITERATURE")
    S.append(dash)
    S.append("")
    S.append(f"  Domain: {domain} | Papers: {len(papers)}")
    sources = {}
    for p in papers:
        if isinstance(p, dict):
            src = p.get("source", "?")
            sources[src] = sources.get(src, 0) + 1
    if sources:
        S.append(f"  Sources: {', '.join(f'{v} {k}' for k, v in sorted(sources.items(), key=lambda x: -x[1]))}")
    S.append("  Key Literature:")
    cited = sorted([p for p in papers if isinstance(p, dict) and (p.get("citation_count") or 0) > 0],
                   key=lambda p: -(p.get("citation_count") or 0))
    for p in cited[:5]:
        S.append(f"    [{p.get('source','?')}] {p.get('title','?')[:55]} ({p.get('year','?')}, {p.get('citation_count',0)} cites)")
    if not cited:
        for p in papers[:5]:
            if isinstance(p, dict):
                S.append(f"    [{p.get('source','?')}] {p.get('title','?')[:65]}")
    if entities or relationships:
        S.append(f"  Knowledge Graph: {entities} entities, {relationships} relationships")
    if gaps:
        S.append(f"  Knowledge Gaps: {len(gaps)} identified")
    S.append("")

    # 3. HYPOTHESIS
    S.append(dash)
    S.append("  3. HYPOTHESIS")
    S.append(dash)
    S.append("")
    S.append(f"  Name: {w_name}")
    S.append(f"  Type: {w_type} | Classification: {_safe(classify, 'classification', 'unknown')}")
    S.append("")
    S.append("  Statement:")
    S.append(_wrap(w_desc, 76, 4))
    S.append("")
    w_explains = _safe(winner, "explains", [])
    if w_explains:
        S.append("  Explains:")
        for exp in w_explains[:5]:
            S.append(f"    - {_trunc(exp, 100)}")
        S.append("")

    # 4. MECHANISMS
    S.append(dash)
    S.append(f"  4. PROPOSED MECHANISM(S) ({len(mechs)})")
    S.append(dash)
    S.append("")
    for i, mech in enumerate(mechs[:5]):
        if not isinstance(mech, dict):
            continue
        m_name = _safe(mech, "name", f"Mechanism {i+1}")
        m_desc = _safe(mech, "description", "")
        m_type = _safe(mech, "type", "unknown")
        m_steps = _safe(mech, "steps", [])
        m_conf = _safe(mech, "confidence", 0)
        m_params = _safe(mech, "key_parameters", [])
        m_fals = _safe(mech, "falsification", "")
        m_preds = _safe(mech, "predictions", [])

        S.append(f"  {i+1}. {m_name} [{m_type}]")
        if m_conf:
            S.append(f"     Confidence: {m_conf:.0%}")
        if m_desc:
            S.append("     Description:")
            S.append(_wrap(_trunc(m_desc, 250), 76, 6))
        if m_steps:
            S.append("     Causal Pathway:")
            for j, step in enumerate(m_steps[:5]):
                S.append(f"       {j+1}. {_trunc(step, 120)}")
        if m_params:
            S.append("     Key Parameters:")
            for kp in m_params[:3]:
                if isinstance(kp, dict):
                    S.append(f"       - {kp.get('name','?')} = {kp.get('expected_value','?')} "
                             f"{kp.get('units','')} [{kp.get('source','')}]")
        if m_fals:
            S.append(f"     Falsification: {_trunc(m_fals, 150)}")
        if m_preds:
            S.append("     Predictions:")
            for mp in m_preds[:3]:
                S.append(f"       - {_trunc(mp, 120)}")
        S.append("")
    if avg_comp > 0:
        S.append(f"  Mechanism Completeness: {avg_comp:.2f}/1.0 ({comp_complete}/{comp_total} complete)")
        if avg_comp < 0.3:
            S.append("  WARNING: Low completeness - treat as preliminary hypotheses")
        S.append("")

    # 5. HIDDEN VARIABLES
    if hvs:
        S.append(dash)
        S.append(f"  5. HIDDEN VARIABLES ({len(hvs)})")
        S.append(dash)
        S.append("")
        for i, hv in enumerate(hvs[:8]):
            if not isinstance(hv, dict):
                continue
            hv_name = _safe(hv, "name", "?")
            hv_desc = _safe(hv, "description", "")
            hv_novelty = _safe(hv, "novelty", "")
            hv_conf = _safe(hv, "confidence", 0)
            tag = f" [{hv_novelty}]" if hv_novelty else ""
            ctag = f" (conf: {hv_conf:.0%})" if hv_conf else ""
            S.append(f"  {i+1}. {hv_name}{tag}{ctag}")
            if hv_desc:
                S.append(_wrap(_trunc(hv_desc, 200), 76, 6))
            S.append("")

    # 6. PREDICTIONS
    S.append(dash)
    S.append(f"  6. TESTABLE PREDICTIONS ({len(preds)})")
    S.append(dash)
    S.append("")
    if preds:
        pn = 0
        for pred in preds[:8]:
            if isinstance(pred, dict):
                stmt = _safe(pred, "statement", _safe(pred, "description", ""))
                ptype = _safe(pred, "type", "unknown")
                fals = _safe(pred, "falsification", "")
                if not stmt or len(str(stmt).strip()) < 10:
                    continue
                pn += 1
                S.append(f"  {pn}. [{ptype.upper()}]")
                S.append(_wrap(_trunc(stmt, 250), 76, 5))
                if fals and len(str(fals)) > 10:
                    S.append(f"     Falsification: {_trunc(fals, 150)}")
                S.append("")
            elif isinstance(pred, str) and len(pred.strip()) > 10:
                pn += 1
                S.append(f"  {pn}. {_trunc(pred, 200)}")
                S.append("")
        if pn == 0:
            S.append("  No predictions with sufficient content.")
            S.append("")
    else:
        S.append("  No predictions generated.")
        S.append("")
    if cf_supported:
        S.append(f"  Counterfactual predictions: {len(cfs)} derived, {len(cf_supported)} supported")
        S.append("")

    # 7. VALIDATION PLAN
    S.append(dash)
    S.append(f"  7. {dcfg['label'].upper()}")
    S.append(dash)
    S.append("")
    S.append(f"  Domain: {domain}")
    for method in dcfg["methods"]:
        S.append(f"    - {method}")
    S.append("")
    if isinstance(exp_ph, dict):
        plans = _safe(exp_ph, "plans", [])
        if plans:
            S.append("  Pipeline-Generated Plans:")
            for j, plan in enumerate(plans[:2]):
                if isinstance(plan, dict):
                    p_design = _safe(plan, "design", _safe(plan, "description", ""))
                    S.append(f"    Plan {j+1}: {_trunc(p_design, 200)}")
                    p_iv = _safe(plan, "independent_variables", _safe(plan, "independent", ""))
                    p_dv = _safe(plan, "dependent_variables", _safe(plan, "dependent", ""))
                    p_confirm = _safe(plan, "confirmatory", _safe(plan, "confirm", ""))
                    if p_iv:
                        S.append(f"      Independent: {str(p_iv)[:120]}")
                    if p_dv:
                        S.append(f"      Dependent: {str(p_dv)[:120]}")
                    if p_confirm:
                        S.append(f"      Confirm: {_trunc(p_confirm, 150)}")
            S.append("")

    # 8. EVIDENCE ASSESSMENT
    S.append(dash)
    S.append("  8. EVIDENCE ASSESSMENT")
    S.append(dash)
    S.append("")
    if scores_d:
        S.append("  Scoring Breakdown:")
        labels = {"novelty": "Novelty", "explanatory_power": "Explanatory Power",
                  "predictive_power": "Predictive Power", "falsifiability": "Falsifiability",
                  "simplicity": "Simplicity", "evidence_strength": "Evidence Strength",
                  "mathematical_rigor": "Math Rigor"}
        wts = {"novelty": 0.25, "explanatory_power": 0.20, "predictive_power": 0.15,
               "falsifiability": 0.12, "simplicity": 0.08, "evidence_strength": 0.12,
               "mathematical_rigor": 0.08}
        for dim, label in labels.items():
            val = scores_d.get(dim, 0)
            w = wts.get(dim, 0)
            filled = int(val / 5)
            bar = "#" * filled + "." * (20 - filled)
            S.append(f"    {label:25s} [{bar}] {val:5.1f}/100 (w={w:.0%})")
        S.append("")
        S.append(f"  Final Score: {disc_score:.0f}/100 (Grade: {grade})")
        if adv_details:
            for d in adv_details:
                S.append(f"    - {d}")
        S.append("")
    if strengths:
        S.append("  Strengths:")
        for s in strengths:
            S.append(f"    + {s}")
        S.append("")
    if weaknesses:
        S.append("  Weaknesses:")
        for w in weaknesses:
            S.append(f"    - {w}")
        S.append("")
    if peer:
        S.append(f"  Peer Review: {peer_score}/10 (recommendation: {peer_rec})")
        if peer_summary:
            S.append(f"    {_trunc(peer_summary, 200)}")
        if major_issues:
            S.append("    Major Issues:")
            for issue in major_issues[:3]:
                S.append(f"      ! {_trunc(str(issue), 120)}")
        S.append("")
    if skeptic:
        S.append(f"  Skeptic Review: {skeptic_rec} (confidence: {skeptic_conf:.0%})")
        S.append("")
    S.append(f"  Confidence: {confidence:.0%}")
    if confidence < 0.15:
        S.append("    WARNING: Very low confidence - treat as preliminary hypothesis")
    elif confidence < 0.30:
        S.append("    NOTE: Low confidence - additional evidence needed")
    S.append("")
    if total_claims > 0:
        S.append(f"  Claim Reliability: {claim_rel:.0%} ({validated}/{total_claims} validated, "
                 f"{hypothetical} hypothetical)")
        S.append("")

    # 9. ALTERNATIVES
    if theories and len(theories) > 1:
        S.append(dash)
        S.append(f"  9. ALTERNATIVE EXPLANATIONS ({len(theories) - 1} runners-up)")
        S.append(dash)
        S.append("")
        for i, t in enumerate(theories[1:5]):
            if not isinstance(t, dict):
                continue
            t_name = _safe(t, "name", f"Theory {i+2}")
            t_score = _safe(t.get("scores", {}), "overall", 0)
            t_desc = _safe(t, "description", _safe(t, "mechanism", ""))
            S.append(f"  {i+2}. {t_name} (score: {t_score:.2f})")
            if t_desc:
                S.append(_wrap(_trunc(t_desc, 180), 76, 5))
            S.append("")

    # 10. CROSS-DOMAIN
    if cross_domain:
        S.append(dash)
        S.append("  10. CROSS-DOMAIN CONNECTIONS")
        S.append(dash)
        S.append("")
        for i, cd in enumerate(cross_domain[:3]):
            if isinstance(cd, dict):
                conn = _safe(cd, "connection", "")
                dom_b = _safe(cd, "domain_b", "other")
                S.append(f"  {i+1}. {domain} <-> {dom_b}: {conn[:120]}")
        S.append("")

    # 11. LIMITATIONS
    S.append(dash)
    S.append("  11. EPISTEMIC LIMITATIONS")
    S.append(dash)
    S.append("")
    limits = [
        f"Literature: {len(papers)} papers analyzed. Field likely has hundreds more.",
        f"Predictions: {len(preds)} untested. Score reflects potential, not validation.",
    ]
    if avg_comp > 0 and avg_comp < 0.5:
        limits.append(f"Mechanism completeness: {avg_comp:.2f}/1.0. Treat as working hypotheses.")
    if confidence < 0.3:
        limits.append(f"Confidence: {confidence:.0%}. Insufficient to distinguish from noise.")
    if peer_rec in ("major_revision", "reject"):
        limits.append(f"Peer review: {peer_rec}. Significant issues identified.")
    if total_claims > 0 and claim_rel < 0.4:
        limits.append(f"Claims: {claim_rel:.0%} validated. {hypothetical}/{total_claims} hypothetical.")
    if domain in ("drug_discovery",):
        limits.append("No in vivo validation. Proposed molecules not synthesized or tested.")
    elif domain in ("physics", "space_astronomy"):
        limits.append("Predictions not compared against observational data.")
    elif domain in ("ecology",):
        limits.append("No field data collected. Predictions from literature patterns only.")
    for lim in limits:
        S.append(f"  - {lim}")
    S.append("")

    # 12. WHAT WOULD CHANGE THIS
    S.append(dash)
    S.append("  12. WHAT WOULD STRENGTHEN OR REFUTE THIS")
    S.append(dash)
    S.append("")
    S.append("  To STRENGTHEN:")
    s_items = ["Experimental confirmation of at least one prediction",
               "Cross-validation against holdout literature",
               "Independent replication by another group"]
    if avg_comp < 0.5:
        s_items.insert(0, "Complete mechanism derivations with explicit equations")
    if peer_score < 5:
        s_items.insert(0, "Address major issues from peer review")
    for item in s_items:
        S.append(f"    + {item}")
    S.append("")
    S.append("  To REFUTE:")
    r_items = []
    for pred in preds[:3]:
        if isinstance(pred, dict):
            fals = _safe(pred, "falsification", "")
            if fals and len(str(fals)) > 10:
                r_items.append(str(fals)[:150])
    for mech in mechs[:2]:
        if isinstance(mech, dict):
            fals = _safe(mech, "falsification", "")
            if fals and len(str(fals)) > 10:
                r_items.append(str(fals)[:150])
    if not r_items:
        r_items = ["Demonstrate a simpler explanation accounts for all observations",
                    "Show predictions are not borne out by experiment"]
    for item in r_items:
        S.append(f"    - {item}")
    S.append("")

    # 13. METADATA
    S.append(dash)
    S.append("  13. PIPELINE METADATA")
    S.append(dash)
    S.append("")
    S.append(f"  Domain: {domain} | Mode: {mode} | Duration: {dur_str}")
    S.append(f"  Papers: {len(papers)} | Entities: {entities} | Relations: {relationships}")
    S.append(f"  Hidden Variables: {len(hvs)} | Mechanisms: {len(mechs)}")
    S.append(f"  Predictions: {len(preds)} | Theories: {len(theories)}")
    if loop_hist:
        S.append(f"  Recurrent Loops: {len(loop_hist)}")
        for lh in loop_hist:
            S.append(f"    Loop {lh.get('loop','?')}: score={lh.get('score',0):.3f}, "
                     f"winner=\"{str(lh.get('winner','?'))[:40]}\", strategy={lh.get('strategy','?')}")
    if errors:
        S.append(f"  Errors: {len(errors)}")
    S.append("")
    S.append(eq)
    S.append("  END OF STRUCTURED REPORT")
    S.append("  Generated by RUMI - Autonomous AI-Driven Scientific Discovery")
    S.append(eq)

    return "\n".join(S)