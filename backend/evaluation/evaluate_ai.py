"""Reproducible demonstration evaluation; fixture labels are synthetic, not real-world performance."""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_JSON_DB", "true")
os.environ.setdefault("JWT_SECRET", "evaluation-only-secret-value-123456789012345")
from services.ai_service import check_duplicate_issues

def compute_binary_metrics(predictions, labels):
    """Compute binary classification metrics without hiding zero-denominator cases."""
    tp = fp = fn = tn = 0
    for predicted, label in zip(predictions, labels):
        if predicted and label: tp += 1
        elif predicted and not label: fp += 1
        elif not predicted and label: fn += 1
        else: tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
    }


def main():
    fixture_path = Path(__file__).with_name("duplicate_pairs.json")
    rows = json.loads(fixture_path.read_text(encoding="utf-8"))
    predictions = []
    labels = []
    latencies = []
    methods = {}
    for row in rows:
        start = time.perf_counter()
        result = check_duplicate_issues(
            row["title"], row["description"], row["category"],
            row["latitude"], row["longitude"], [row["existing"]],
        )
        latencies.append((time.perf_counter() - start) * 1000)
        predictions.append(result["is_duplicate"])
        labels.append(row["label"])
        methods[result.get("method", "unknown")] = methods.get(result.get("method", "unknown"), 0) + 1
    metrics = compute_binary_metrics(predictions, labels)
    print(json.dumps({
        "fixture": str(fixture_path), "fixture_type": "synthetic_demonstration",
        "samples": len(rows), **{key: value if key in {"tp", "fp", "fn", "tn"} else round(value, 4) for key, value in metrics.items()},
        "methods": methods,
        "warning": "Synthetic fixture only; lexical fallback is not a semantic-model benchmark." if "semantic" not in methods else None,
        "mean_latency_ms": round(sum(latencies) / len(latencies), 3),
    }, indent=2))


if __name__ == "__main__":
    main()
