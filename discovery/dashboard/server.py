"""
RUMI Discovery Dashboard — Live API Server

Serves the dashboard UI and provides REST API endpoints that read
actual discovery report data from disk.

Usage:
    python -m discovery.dashboard.server
    python -m discovery.dashboard.server --port 8899

Then open http://localhost:8899
"""

import json
import os
import sys
import glob
import time
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
GRAPH_DIR = PROJECT_ROOT / "discovery" / "graph"
HYP_DIR = PROJECT_ROOT / "discovery" / "hypotheses"
DASHBOARD_DIR = Path(__file__).resolve().parent


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self._handle_api(path, parsed)
            return
        if path == "/" or path == "/index.html":
            self.path = "/index.html"
        super().do_GET()

    def _handle_api(self, path, parsed):
        params = parse_qs(parsed.query)
        try:
            if path == "/api/reports":
                data = self._get_reports()
            elif path == "/api/reports/latest":
                data = self._get_latest_report()
            elif path.startswith("/api/reports/"):
                report_id = path.split("/")[-1]
                data = self._get_report_by_id(report_id)
            elif path == "/api/graph":
                data = self._get_graph()
            elif path == "/api/hypotheses":
                data = self._get_hypotheses()
            elif path == "/api/status":
                data = self._get_pipeline_status()
            elif path == "/api/runs":
                data = self._get_run_history()
            else:
                self._json_response({"error": "Not found"}, 404)
                return
            self._json_response(data)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _json_response(self, data, status=200):
        body = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _get_reports(self):
        reports = []
        for f in sorted(DATA_DIR.glob("discovery_*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                phases = data.get("phases", {})
                reports.append({
                    "id": f.stem,
                    "file": str(f.name),
                    "topic": data.get("topic", ""),
                    "domain": data.get("domain", ""),
                    "score": (phases.get("discovery_scoring", {}) or {}).get("discovery_score", 0),
                    "grade": (phases.get("discovery_scoring", {}) or {}).get("grade", "—"),
                    "duration": data.get("duration_seconds", 0),
                    "papers": (phases.get("literature", {}) or {}).get("papers_found", 0),
                    "entities": (phases.get("knowledge_graph", {}) or {}).get("entities", 0),
                    "modified": os.path.getmtime(f),
                })
            except Exception:
                continue
        return {"reports": reports, "count": len(reports)}

    def _get_latest_report(self):
        files = sorted(DATA_DIR.glob("discovery_*.json"), key=os.path.getmtime)
        if not files:
            return {"error": "No reports found"}
        with open(files[-1], "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_report_by_id(self, report_id):
        f = DATA_DIR / f"{report_id}.json"
        if not f.exists():
            return {"error": f"Report {report_id} not found"}
        with open(f, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _get_graph(self):
        kg_file = GRAPH_DIR / "knowledge_graph.json"
        if kg_file.exists():
            with open(kg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"entities": {}, "relationships": [], "papers": {}}

    def _get_hypotheses(self):
        hyp_file = HYP_DIR / "active.json"
        if hyp_file.exists():
            with open(hyp_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _get_pipeline_status(self):
        log_files = list(PROJECT_ROOT.glob("*.log"))
        latest_activity = 0
        current_phase = None
        for lf in sorted(log_files, key=os.path.getmtime, reverse=True):
            try:
                mtime = os.path.getmtime(lf)
                if mtime > latest_activity:
                    latest_activity = mtime
                if not current_phase:
                    with open(lf, "r", encoding="utf-8", errors="replace") as f:
                        for line in reversed(f.readlines()[-50:]):
                            if "Phase" in line and "/" in line:
                                current_phase = line.strip()
                                break
            except Exception:
                continue
        is_running = (time.time() - latest_activity) < 120
        return {"running": is_running, "current_phase": current_phase, "last_activity": latest_activity}

    def _get_run_history(self):
        reports = []
        for f in sorted(DATA_DIR.glob("discovery_*.json"), key=os.path.getmtime):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                phases = data.get("phases", {})
                reports.append({
                    "id": f.stem,
                    "topic": data.get("topic", "")[:60],
                    "domain": data.get("domain", ""),
                    "score": (phases.get("discovery_scoring", {}) or {}).get("discovery_score", 0),
                    "grade": (phases.get("discovery_scoring", {}) or {}).get("grade", "—"),
                    "time": os.path.getmtime(f),
                    "duration": data.get("duration_seconds", 0),
                })
            except Exception:
                continue
        return {"runs": reports[-20:], "total": len(reports)}

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="RUMI Discovery Dashboard Server")
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), DashboardHandler)
    print(f"RUMI Dashboard: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
