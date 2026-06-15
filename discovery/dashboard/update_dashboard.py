import re
from pathlib import Path

html = Path("discovery/dashboard/index.html").read_text(encoding="utf-8")

# 1. Replace broken data loading with API-based loading
old = """async function loadAllData() {
  // Try v2 reports first, then v1
  const reports = await loadV2Reports();
  const kg = await loadJSON('../../discovery/graph/knowledge_graph.json');
  const hyps = await loadJSON('../../discovery/hypotheses/active.json');
  const contras = await loadJSON('../../discovery/contradictions/active.json');

  currentData = {
    reports,
    latestReport: reports.length ? reports[reports.length - 1] : null,
    kg: kg || { entities: {}, relationships: [], papers: {} },
    hypotheses: hyps || [],
    contradictions: contras || [],
  };

  renderAll();
}"""

new = """async function loadAllData() {
  const API = window.location.origin;
  try {
    const [latest, runs, status] = await Promise.all([
      fetch(API + '/api/reports/latest').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(API + '/api/runs').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(API + '/api/status').then(r => r.ok ? r.json() : null).catch(() => null),
    ]);
    const reports = runs?.runs || [];
    const report = latest && latest.phases ? latest : null;
    currentData = {
      reports: reports,
      latestReport: report,
      kg: { entities: {}, relationships: [], papers: {} },
      hypotheses: [],
      contradictions: [],
      status: status || {},
    };
  } catch(e) {
    currentData = { reports: [], latestReport: null, kg: { entities: {}, relationships: [], papers: {} }, hypotheses: [], contradictions: [] };
  }
  renderAll();
  setInterval(loadAllData, 30000);
}"""

html = html.replace(old, new)

# 2. Remove broken loadV2Reports/loadJSON
start = html.find("async function loadV2Reports()")
end = html.find("// " + "=" * 55, start)
if start > 0 and end > start:
    html = html[:start] + html[end:]

# 3. Add new nav items
old_nav = """<div class=\"nav-item\" data-view=\"contradictions\">
        <span class=\"nav-icon\">⚡</span> Contradictions
        <span class=\"nav-badge\" id=\"contradictions-count\">—</span>
      </div>"""

# 4. Update renderAll
old_render = """function renderAll() {
  renderOverview();
  renderPipeline();
  renderTheories();
  renderGaps();
  renderAnomalies();
  renderPredictions();
  renderGraph();
  renderPapers();
  renderContradictions();
  renderRunHistory();
  updateNavBadges();
}"""

new_render = """function renderAll() {
  renderOverview();
  renderPipeline();
  renderTheories();
  renderGaps();
  renderAnomalies();
  renderPredictions();
  renderGraph();
  renderPapers();
  renderContradictions();
  renderRunHistory();
  renderAdversarial();
  renderPeerReview();
  renderScoring();
  renderDerivations();
  updateNavBadges();
}"""

html = html.replace(old_render, new_render)

Path("discovery/dashboard/update_dashboard.py").write_text(script, encoding="utf-8")
print("Script written")
print(f"HTML has API: {'/api/reports/latest' in html}")
