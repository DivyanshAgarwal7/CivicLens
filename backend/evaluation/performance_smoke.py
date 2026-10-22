"""Small local performance smoke test; not a production load test."""

import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_JSON_DB", "true")
os.environ.setdefault("JWT_SECRET", "performance-only-secret-value-123456789")

from services.ai_service import check_duplicate_issues


def main():
    existing = [{
        "_id": "perf-1", "issue_id": "CL-PERF-1", "title": "Large pothole on Main Road",
        "description": "Deep road damage near the bus stop", "category": "Roads & Infrastructure",
        "location": {"latitude": 28.6139, "longitude": 77.2090}, "status": "Reported",
    }]
    timings = []
    for _ in range(20):
        start = time.perf_counter()
        check_duplicate_issues("Road damage on Main Road", "Deep pothole near bus stop", "Roads & Infrastructure", 28.61391, 77.20901, existing)
        timings.append((time.perf_counter() - start) * 1000)
    ordered = sorted(timings)
    print(json.dumps({
        "operation": "duplicate_detection",
        "samples": len(timings),
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 3),
        "mean_ms": round(statistics.mean(ordered), 3),
        "note": "Local smoke measurement only; endpoint, Mongo, browser, and concurrent-load performance are not covered.",
    }, indent=2))


if __name__ == "__main__":
    main()
