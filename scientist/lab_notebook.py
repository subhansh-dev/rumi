"""
lab_notebook.py — Digital Lab Notebook for Scientific Research

Persistent, structured experiment tracking. Every scientist needs a lab notebook.

Capabilities:
  [LN-1] Create experiment entries with hypothesis, method, results
  [LN-2] Track experiment status (planned, running, completed, failed)
  [LN-3] Record observations, measurements, and raw data
  [LN-4] Link entries to hypotheses, papers, and other entries
  [LN-5] Search and filter by date, status, tags, domain
  [LN-6] Export entries as structured reports
  [LN-7] Attach plots, tables, and code snippets
  [LN-8] Version tracking for iterative experiments
  [LN-9] Daily summary generation
  [LN-10] Tags and cross-referencing

Thread-safe. Persistent state in lab_notebook_state.json.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()
STATE_FILE = SCIENTIST_DIR / "lab_notebook_state.json"

STATUS_PLANNED = "planned"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_ABANDONED = "abandoned"


class NotebookEntry:
    """A single lab notebook entry."""

    def __init__(
        self,
        title: str,
        hypothesis: str = "",
        method: str = "",
        domain: str = "",
    ):
        self.id = f"NB-{int(time.time() * 1000)}"
        self.title = title
        self.hypothesis = hypothesis
        self.method = method
        self.domain = domain
        self.status = STATUS_PLANNED
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.completed_at: str = ""

        # Content
        self.observations: list[dict] = []  # [{timestamp, text, type}]
        self.measurements: list[dict] = []  # [{name, value, unit, timestamp}]
        self.results: str = ""
        self.conclusion: str = ""

        # Attachments
        self.code_snippets: list[dict] = []  # [{language, code, description}]
        self.tables: list[dict] = []  # [{name, headers, rows}]
        self.figures: list[dict] = []  # [{name, description, path}]

        # Linking
        self.tags: list[str] = []
        self.related_entries: list[str] = []  # entry IDs
        self.hypothesis_id: str = ""  # link to hypothesis engine
        self.paper_refs: list[str] = []  # paper titles or DOIs

        # Versioning
        self.version = 1
        self.parent_entry_id: str = ""  # for iterative experiments

    def add_observation(self, text: str, obs_type: str = "note"):
        """Record an observation."""
        self.observations.append({
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "type": obs_type,  # note, anomaly, warning, insight
        })
        self.updated_at = datetime.now().isoformat()

    def add_measurement(self, name: str, value: float, unit: str = ""):
        """Record a measurement."""
        self.measurements.append({
            "name": name,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now().isoformat()

    def add_code(self, code: str, language: str = "python", description: str = ""):
        """Attach a code snippet."""
        self.code_snippets.append({
            "language": language,
            "code": code,
            "description": description,
        })
        self.updated_at = datetime.now().isoformat()

    def add_table(self, name: str, headers: list[str], rows: list[list]):
        """Attach a data table."""
        self.tables.append({
            "name": name,
            "headers": headers,
            "rows": rows,
        })
        self.updated_at = datetime.now().isoformat()

    def set_status(self, status: str):
        """Update entry status."""
        self.status = status
        self.updated_at = datetime.now().isoformat()
        if status in (STATUS_COMPLETED, STATUS_FAILED, STATUS_ABANDONED):
            self.completed_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "hypothesis": self.hypothesis,
            "method": self.method,
            "domain": self.domain,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "observations": self.observations,
            "measurements": self.measurements,
            "results": self.results,
            "conclusion": self.conclusion,
            "code_snippets": self.code_snippets,
            "tables": self.tables,
            "figures": self.figures,
            "tags": self.tags,
            "related_entries": self.related_entries,
            "hypothesis_id": self.hypothesis_id,
            "paper_refs": self.paper_refs,
            "version": self.version,
            "parent_entry_id": self.parent_entry_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NotebookEntry":
        e = cls(d["title"], d.get("hypothesis", ""), d.get("method", ""), d.get("domain", ""))
        e.id = d["id"]
        e.status = d.get("status", STATUS_PLANNED)
        e.created_at = d.get("created_at", e.created_at)
        e.updated_at = d.get("updated_at", e.updated_at)
        e.completed_at = d.get("completed_at", "")
        e.observations = d.get("observations", [])
        e.measurements = d.get("measurements", [])
        e.results = d.get("results", "")
        e.conclusion = d.get("conclusion", "")
        e.code_snippets = d.get("code_snippets", [])
        e.tables = d.get("tables", [])
        e.figures = d.get("figures", [])
        e.tags = d.get("tags", [])
        e.related_entries = d.get("related_entries", [])
        e.hypothesis_id = d.get("hypothesis_id", "")
        e.paper_refs = d.get("paper_refs", [])
        e.version = d.get("version", 1)
        e.parent_entry_id = d.get("parent_entry_id", "")
        return e


class LabNotebook:
    """
    Digital lab notebook for structured experiment tracking.

    Persistent, searchable, and linkable to other scientist modules.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._entries: dict[str, NotebookEntry] = {}
        self._load_state()

    def _load_state(self):
        with self._lock:
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    for e in data.get("entries", []):
                        entry = NotebookEntry.from_dict(e)
                        self._entries[entry.id] = entry
                except Exception:
                    pass

    def _save_state(self):
        with self._lock:
            data = {
                "entries": [e.to_dict() for e in self._entries.values()],
                "saved_at": datetime.now().isoformat(),
            }
            STATE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def create_entry(
        self,
        title: str,
        hypothesis: str = "",
        method: str = "",
        domain: str = "",
        tags: list[str] | None = None,
    ) -> NotebookEntry:
        """Create a new notebook entry."""
        with self._lock:
            entry = NotebookEntry(title, hypothesis, method, domain)
            if tags:
                entry.tags = tags
            self._entries[entry.id] = entry
            self._save_state()
            return entry

    def get_entry(self, entry_id: str) -> NotebookEntry | None:
        """Get an entry by ID."""
        with self._lock:
            return self._entries.get(entry_id)

    def update_entry(self, entry_id: str, **kwargs) -> NotebookEntry | None:
        """Update entry fields."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if not entry:
                return None
            for key, value in kwargs.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            entry.updated_at = datetime.now().isoformat()
            self._save_state()
            return entry

    def search_entries(
        self,
        query: str = "",
        status: str = "",
        domain: str = "",
        tags: list[str] | None = None,
        date_from: str = "",
        date_to: str = "",
        limit: int = 20,
    ) -> list[NotebookEntry]:
        """Search and filter entries."""
        with self._lock:
            results = []
            for entry in self._entries.values():
                if status and entry.status != status:
                    continue
                if domain and entry.domain != domain:
                    continue
                if tags and not any(t in entry.tags for t in tags):
                    continue
                if date_from and entry.created_at < date_from:
                    continue
                if date_to and entry.created_at > date_to:
                    continue
                if query:
                    text = (
                        entry.title + " " + entry.hypothesis + " " +
                        entry.method + " " + entry.results + " " +
                        entry.conclusion + " " + " ".join(entry.tags)
                    ).lower()
                    if query.lower() not in text:
                        continue
                results.append(entry)

            # Sort by most recent
            results.sort(key=lambda e: e.updated_at, reverse=True)
            return results[:limit]

    def get_recent(self, days: int = 7, limit: int = 20) -> list[NotebookEntry]:
        """Get entries from the last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return self.search_entries(date_from=cutoff, limit=limit)

    def get_by_status(self, status: str) -> list[NotebookEntry]:
        """Get all entries with a given status."""
        return self.search_entries(status=status)

    def get_daily_summary(self, date: str = "") -> dict:
        """Generate a summary for a given day."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        with self._lock:
            day_entries = [
                e for e in self._entries.values()
                if e.created_at.startswith(date)
            ]

            return {
                "date": date,
                "total_entries": len(day_entries),
                "by_status": {
                    s: len([e for e in day_entries if e.status == s])
                    for s in [STATUS_PLANNED, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, STATUS_ABANDONED]
                },
                "entries": [
                    {"id": e.id, "title": e.title, "status": e.status}
                    for e in day_entries
                ],
                "observations_count": sum(len(e.observations) for e in day_entries),
                "measurements_count": sum(len(e.measurements) for e in day_entries),
            }

    def format_entry(self, entry: NotebookEntry) -> str:
        """Format an entry as readable text."""
        lines = [
            f"=== {entry.title} ===",
            f"ID: {entry.id} | Status: {entry.status} | Version: {entry.version}",
            f"Domain: {entry.domain or 'N/A'} | Tags: {', '.join(entry.tags) or 'none'}",
            f"Created: {entry.created_at} | Updated: {entry.updated_at}",
            "",
        ]
        if entry.hypothesis:
            lines.append(f"Hypothesis: {entry.hypothesis}")
            lines.append("")
        if entry.method:
            lines.append(f"Method: {entry.method}")
            lines.append("")
        if entry.observations:
            lines.append(f"Observations ({len(entry.observations)}):")
            for obs in entry.observations[-5:]:
                lines.append(f"  [{obs['type']}] {obs['text'][:100]}")
            lines.append("")
        if entry.measurements:
            lines.append(f"Measurements ({len(entry.measurements)}):")
            for m in entry.measurements[-5:]:
                lines.append(f"  {m['name']}: {m['value']} {m['unit']}")
            lines.append("")
        if entry.results:
            lines.append(f"Results: {entry.results[:200]}")
            lines.append("")
        if entry.conclusion:
            lines.append(f"Conclusion: {entry.conclusion[:200]}")
        return "\n".join(lines)

    def format_search_results(self, entries: list[NotebookEntry]) -> str:
        """Format search results."""
        if not entries:
            return "No entries found."
        lines = [f"Lab Notebook — {len(entries)} entries:", ""]
        for e in entries:
            status_icon = {
                STATUS_PLANNED: "[ ]",
                STATUS_RUNNING: "[~]",
                STATUS_COMPLETED: "[x]",
                STATUS_FAILED: "[-]",
                STATUS_ABANDONED: "[/]",
            }.get(e.status, "[?]")
            lines.append(f"  {status_icon} {e.title}")
            lines.append(f"    ID: {e.id} | {e.domain or 'no domain'} | {e.created_at[:10]}")
            if e.observations:
                lines.append(f"    {len(e.observations)} observations, {len(e.measurements)} measurements")
            lines.append("")
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Get notebook statistics."""
        with self._lock:
            entries = list(self._entries.values())
            return {
                "total_entries": len(entries),
                "by_status": {
                    s: len([e for e in entries if e.status == s])
                    for s in [STATUS_PLANNED, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, STATUS_ABANDONED]
                },
                "total_observations": sum(len(e.observations) for e in entries),
                "total_measurements": sum(len(e.measurements) for e in entries),
                "domains": list(set(e.domain for e in entries if e.domain)),
                "all_tags": list(set(t for e in entries for t in e.tags)),
            }

    def reset(self):
        """Clear all entries."""
        with self._lock:
            self._entries.clear()
            self._save_state()


# ── Singleton ─────────────────────────────────────────────────────────────────

_notebook: Optional[LabNotebook] = None
_notebook_lock = threading.Lock()


def get_lab_notebook() -> LabNotebook:
    global _notebook
    with _notebook_lock:
        if _notebook is None:
            _notebook = LabNotebook()
        return _notebook
