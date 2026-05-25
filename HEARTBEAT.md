# HEARTBEAT.md — Periodic System Checks

_Periodic proactive checks performed during idle time. These keep RUMI aware of system health, user activity, and research opportunities._

---

## Schedule

| Check | Frequency | Window | Duration |
|-------|-----------|--------|----------|
| User activity | Every heartbeat | ~30 min | Instant |
| System health | Every heartbeat | ~30 min | ~2s |
| Knowledge gap scan | Every 2-3 heartbeats | ~1-2 hours | ~10s |
| Hypothesis review | Every 2-3 heartbeats | ~1-2 hours | ~5s |
| Memory consolidation | Every 2-3 days | During idle | ~30s |
| Daily log rotation | Daily | End of day | ~5s |
| Literature check | Every 3-4 heartbeats | ~2 hours | ~15s |

---

## Tasks to Rotate Through (2-4 per day)

### 1. System Health
- [ ] **CPU usage** — Any processes consuming abnormal resources?
- [ ] **RAM usage** — Available memory sufficient?
- [ ] **Disk space** — Any partitions nearing capacity?
- [ ] **Network** — Internet connectivity status?
- [ ] **Tools** — All action modules loaded and functional?

### 2. Memory Maintenance
- [ ] **Daily log review** — Read recent memory/YYYY-MM-DD.md entries
- [ ] **MEMORY.md update** — Consolidate important facts from daily logs
- [ ] **USER.md update** — Any new preferences or details to capture?
- [ ] **Hypothesis aging** — Review active hypotheses; mark stale ones

### 3. Knowledge & Research
- [ ] **Knowledge graph review** — Any entities needing updates or connections?
- [ ] **Experiment status** — Any running experiments to check?
- [ ] **Paper search** — New papers in tracked research areas?
- [ ] **Cross-domain scan** — Interesting analogies between recent topics?

### 4. Proactive Suggestions
- [ ] **Context-aware suggestions** — Based on current projects, what might help?
- [ ] **Tool improvements** — Any patterns in how tools are used that suggest optimizations?
- [ ] **Learning reflection** — Any lessons from recent sessions to record?

---

## When to Reach Out

- Important system issue detected (disk full, high memory pressure)
- Significant research finding discovered
- Experiment completed with notable results
- Knowledge gap found matching user's known interests
- New paper in tracked research area
- It's been >8h since last interaction
- Something genuinely interesting or unexpected

## When to Stay Quiet (HEARTBEAT_OK)

- Late night (23:00-08:00) unless urgent
- User is clearly busy or in focus mode
- Nothing new since last check
- Just checked <30 minutes ago
- User explicitly asked not to be disturbed

---

## Track State

Maintain `memory/heartbeat-state.json`:
```json
{
  "lastChecks": {
    "system_health": null,
    "memory_maintenance": null,
    "knowledge_review": null,
    "literature_check": null,
    "proactive_suggest": null
  },
  "lastContactTime": null,
  "consecutiveSilentChecks": 0
}
```

---

## Health Metrics

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| CPU usage | <50% | 50-80% | >80% |
| RAM usage | <60% | 60-85% | >85% |
| Disk space | >20% free | 10-20% free | <10% free |
| Module load rate | >90% | 70-90% | <70% |
| Memory size | <10MB | 10-50MB | >50MB |
