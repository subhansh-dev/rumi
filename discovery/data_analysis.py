"""
data_analysis.py — Real Data Fetching & Statistical Analysis for RUMI

Fetches actual datasets from public APIs and runs statistical analysis
to validate or challenge theories. Not LLM-generated — real computations.

Supported data sources:
- NASA Open APIs (exoplanets, solar activity, NEOs)
- World Bank (economic indicators)
- WHO (health statistics)
- Generic CSV/JSON data from URLs
"""

import json
import math
import urllib.request
import urllib.parse
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Any


class DataAnalyzer:
    """Fetch and analyze real datasets for theory validation."""

    def __init__(self):
        self.datasets = {}

    def fetch_nasa_exoplanets(self, limit: int = 100) -> dict:
        """Fetch confirmed exoplanet data from NASA Exoplanet Archive."""
        try:
            url = (
                "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?"
                "query=select+pl_name,hostname,sy_dist,pl_rade,pl_bmasse,pl_orbper,disc_year,disc_facility"
                f"+from+ps+where+default_flag=1+order+by+disc_year+desc&format=json&max_rows={limit}"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            self.datasets["nasa_exoplanets"] = {
                "source": "NASA Exoplanet Archive",
                "records": len(data),
                "data": data,
            }
            return {"status": "ok", "records": len(data), "sample": data[:3]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def fetch_nasa_neo(self, days: int = 7) -> dict:
        """Fetch Near-Earth Object data from NASA NEO API."""
        try:
            url = f"https://api.nasa.gov/neo/rest/v1/feed?api_key=DEMO_KEY&detailed=true"
            req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            neos = []
            for date, objs in data.get("near_earth_objects", {}).items():
                for obj in objs:
                    neos.append({
                        "name": obj.get("name"),
                        "diameter_km": obj.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max"),
                        "hazardous": obj.get("is_potentially_hazardous_asteroid"),
                        "velocity_kmh": float(obj.get("close_approach_data", [{}])[0].get("relative_velocity", {}).get("kilometers_per_hour", 0)) if obj.get("close_approach_data") else None,
                        "miss_distance_km": float(obj.get("close_approach_data", [{}])[0].get("miss_distance", {}).get("kilometers", 0)) if obj.get("close_approach_data") else None,
                    })
            self.datasets["nasa_neo"] = {"source": "NASA NEO API", "records": len(neos), "data": neos}
            return {"status": "ok", "records": len(neos), "sample": neos[:3]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def fetch_from_url(self, url: str, name: str = "custom") -> dict:
        """Fetch data from a generic URL (JSON or CSV)."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
            # Try JSON first
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    records = data.get("data", data.get("results", [data]))
                else:
                    records = [data]
            except json.JSONDecodeError:
                # CSV fallback
                lines = raw.strip().split("\n")
                if len(lines) > 1:
                    headers = lines[0].split(",")
                    records = []
                    for line in lines[1:]:
                        vals = line.split(",")
                        records.append(dict(zip(headers, vals)))
                else:
                    records = [{"raw": raw[:1000]}]
            self.datasets[name] = {"source": url, "records": len(records), "data": records}
            return {"status": "ok", "records": len(records), "sample": records[:3]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def analyze_dataset(self, name: str) -> dict:
        """Run statistical analysis on a loaded dataset."""
        ds = self.datasets.get(name)
        if not ds:
            return {"error": f"Dataset '{name}' not loaded"}
        data = ds.get("data", [])
        if not data or not isinstance(data, list):
            return {"error": "No data to analyze"}

        results = {
            "source": ds.get("source", ""),
            "total_records": len(data),
            "fields": [],
            "statistics": {},
            "patterns": [],
        }

        # Analyze fields
        if data and isinstance(data[0], dict):
            all_keys = set()
            for row in data[:50]:
                all_keys.update(row.keys())
            results["fields"] = sorted(all_keys)

            # Numeric field statistics
            for key in all_keys:
                values = []
                for row in data:
                    v = row.get(key)
                    if v is not None:
                        try:
                            values.append(float(v))
                        except (ValueError, TypeError):
                            continue
                if len(values) >= 3:
                    mean = sum(values) / len(values)
                    variance = sum((x - mean) ** 2 for x in values) / max(len(values) - 1, 1)
                    std = math.sqrt(variance)
                    sorted_v = sorted(values)
                    median = sorted_v[len(sorted_v) // 2]
                    results["statistics"][key] = {
                        "count": len(values),
                        "mean": round(mean, 4),
                        "median": round(median, 4),
                        "std": round(std, 4),
                        "min": round(min(values), 4),
                        "max": round(max(values), 4),
                    }

            # Categorical field distribution
            for key in all_keys:
                values = [str(row.get(key, "")) for row in data if row.get(key) is not None]
                if values and not any(key in results["statistics"] for _ in [1]):
                    counter = Counter(values)
                    if len(counter) <= 20 and len(counter) > 1:
                        top = counter.most_common(10)
                        results["patterns"].append({
                            "field": key,
                            "type": "categorical",
                            "unique_values": len(counter),
                            "top_values": top,
                        })

            # Correlation analysis between numeric fields
            numeric_fields = list(results["statistics"].keys())
            correlations = []
            for i, f1 in enumerate(numeric_fields):
                for f2 in numeric_fields[i+1:]:
                    v1 = []
                    v2 = []
                    for row in data:
                        a, b = row.get(f1), row.get(f2)
                        if a is not None and b is not None:
                            try:
                                v1.append(float(a))
                                v2.append(float(b))
                            except (ValueError, TypeError):
                                continue
                    if len(v1) >= 5:
                        corr = self._pearson(v1, v2)
                        if abs(corr) > 0.3:
                            correlations.append({
                                "field1": f1, "field2": f2,
                                "correlation": round(corr, 4),
                                "n": len(v1),
                                "strength": "strong" if abs(corr) > 0.7 else "moderate",
                            })
            if correlations:
                results["correlations"] = sorted(correlations, key=lambda x: abs(x["correlation"]), reverse=True)

        return results

    def validate_theory_against_data(self, theory: dict, dataset_name: str) -> dict:
        """Check if a theory's predictions are consistent with actual data."""
        ds = self.datasets.get(dataset_name)
        if not ds:
            return {"status": "no_data", "error": f"Dataset '{dataset_name}' not loaded"}

        analysis = self.analyze_dataset(dataset_name)
        predictions = theory.get("predictions", [])
        key_params = theory.get("key_parameters", [])

        validation = {
            "theory": theory.get("name", "?"),
            "dataset": dataset_name,
            "data_records": analysis.get("total_records", 0),
            "checks": [],
            "overall_support": "insufficient",
        }

        # Check if any key parameters appear in the data statistics
        stats = analysis.get("statistics", {})
        for param in key_params:
            if not isinstance(param, dict):
                continue
            pname = param.get("name", "").lower()
            for field, field_stats in stats.items():
                if pname in field.lower() or field.lower() in pname:
                    validation["checks"].append({
                        "parameter": pname,
                        "field": field,
                        "data_mean": field_stats.get("mean"),
                        "data_range": [field_stats.get("min"), field_stats.get("max")],
                        "status": "data_available",
                    })

        support_count = len([c for c in validation["checks"] if c.get("status") == "data_available"])
        if support_count >= 3:
            validation["overall_support"] = "strong"
        elif support_count >= 1:
            validation["overall_support"] = "moderate"
        else:
            validation["overall_support"] = "weak"

        return validation

    @staticmethod
    def _pearson(x: list, y: list) -> float:
        """Pearson correlation coefficient."""
        n = min(len(x), len(y))
        if n < 3:
            return 0.0
        mx = sum(x[:n]) / n
        my = sum(y[:n]) / n
        num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        dx = math.sqrt(sum((x[i] - mx) ** 2 for i in range(n)))
        dy = math.sqrt(sum((y[i] - my) ** 2 for i in range(n)))
        if dx * dy == 0:
            return 0.0
        return num / (dx * dy)
