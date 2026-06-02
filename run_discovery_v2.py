#!/usr/bin/env python3
"""
RUMI Discovery Pipeline v2.1 — Entry Point

Usage:
    python run_discovery_v2.py "Hubble tension"
    python run_discovery_v2.py "KRAS G12C resistance" --domain drug_discovery
    python run_discovery_v2.py "anomalous stellar dimming" --mode quick
    python run_discovery_v2.py "Hubble tension" --enhance  (adds novelty/falsification/simulation)
"""
import sys
import argparse
from pathlib import Path

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def main():
    parser = argparse.ArgumentParser(description="RUMI Discovery Pipeline v2.1")
    parser.add_argument("topic", nargs="?", default="",
                        help="Research topic to investigate")
    parser.add_argument("--domain", default="",
                        help="Research domain (auto-detected if omitted)")
    parser.add_argument("--mode", default="full",
                        choices=["quick", "standard", "full"],
                        help="Pipeline depth (default: full)")
    parser.add_argument("--enhance", action="store_true", default=True,
                        help="Run enhancement layer (novelty, falsification, simulation, Bayesian)")
    args = parser.parse_args()

    if not args.topic:
        print("RUMI Discovery Pipeline v2.1")
        print("=" * 40)
        args.topic = input("Enter research topic: ").strip()
        if not args.topic:
            print("No topic provided. Exiting.")
            sys.exit(1)

    from discovery.discovery_pipeline_v2 import run_discovery_pipeline

    # Run main pipeline
    result = run_discovery_pipeline(
        topic=args.topic,
        domain=args.domain,
        mode=args.mode,
    )

    # Run enhancement layer
    if args.enhance:
        try:
            from discovery.discovery_enhancer import enhance_discovery
            domain = result.get("domain", args.domain)
            papers = []  # Papers are embedded in the graph
            graph = None  # Graph is created inside pipeline

            # Try to load the graph from the pipeline
            try:
                from discovery.graph import KnowledgeGraph
                graph = KnowledgeGraph(persist=False)
            except Exception:
                pass

            result = enhance_discovery(result, args.topic, domain, papers, graph)
        except Exception as e:
            print(f"\n[WARN] Enhancement layer failed: {e}")
            result["enhancement_error"] = str(e)

    return result


if __name__ == "__main__":
    main()
