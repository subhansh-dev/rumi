"""GitHub API — free, 60 req/hr without key, 5000 req/hr with key.

For computer science domain. Provides: repo search, stars, topics, languages.
"""

import json
import time
import urllib.request
import urllib.parse

GITHUB_BASE = "https://api.github.com"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 1.0:
        time.sleep(1.0 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | list | None:
    _rate_limit()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0", "Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def search_repos(query: str, limit: int = 5) -> list[dict]:
    """Search GitHub repositories by topic or keyword."""
    q = urllib.parse.quote(query)
    url = f"{GITHUB_BASE}/search/repositories?q={q}&sort=stars&order=desc&per_page={limit}"
    data = _fetch(url)
    if not data or not isinstance(data, dict):
        return []
    results = []
    for r in data.get("items", [])[:limit]:
        results.append({
            "name": r.get("full_name", ""),
            "description": (r.get("description") or "")[:300],
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "language": r.get("language") or "",
            "topics": r.get("topics", [])[:10],
            "url": r.get("html_url", ""),
        })
    return results


def get_repo_topics(repo_name: str) -> list[str]:
    """Get topics for a specific repository."""
    url = f"{GITHUB_BASE}/repos/{repo_name}/topics"
    _rate_limit()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0", "Accept": "application/vnd.github.mercy-preview+json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("names", [])
    except Exception:
        return []


def enrich_entities(graph, entity_types: set[str] = {"algorithm", "framework", "dataset", "model", "technique", "architecture"}) -> int:
    """Enrich CS entities with GitHub repo data."""
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        repos = search_repos(name, limit=1)
        if repos:
            graph.entities[eid].setdefault("github", repos[0])
            enriched += 1
    return enriched
