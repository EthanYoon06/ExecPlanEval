from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path


METRICS = ("parse_success", "graph_valid", "node_f1", "edge_f1", "fuzzy_node_f1", "catalog_validity")


def as_float(value: str) -> float:
    return float(value) if value not in {"True", "False"} else float(value == "True")


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * q)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=2000)
    args = parser.parse_args()

    rows = []
    for path in args.inputs:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["model"]].append(row)

    summary = {}
    for model, group in sorted(groups.items()):
        run1 = [row for row in group if int(row["run"]) == 1]
        summary[model] = {
            "n": len(group),
            **{f"mean_{metric}": sum(as_float(row[metric]) for row in group) / len(group) for metric in METRICS},
            "run1_n": len(run1),
            **{f"run1_mean_{metric}": sum(as_float(row[metric]) for row in run1) / len(run1) for metric in METRICS},
        }

    paired = {}
    models = sorted(groups)
    if len(models) == 2:
        left, right = models
        left_rows = {row["task_id"]: row for row in groups[left] if int(row["run"]) == 1}
        right_rows = {row["task_id"]: row for row in groups[right] if int(row["run"]) == 1}
        task_ids = sorted(set(left_rows) & set(right_rows))
        rng = random.Random(20260827)
        for metric in METRICS:
            differences = [as_float(right_rows[key][metric]) - as_float(left_rows[key][metric]) for key in task_ids]
            boot = []
            for _ in range(args.bootstrap):
                sample = [differences[rng.randrange(len(differences))] for _ in differences]
                boot.append(sum(sample) / len(sample))
            paired[metric] = {
                "right_minus_left": sum(differences) / len(differences),
                "task_bootstrap_95_ci": [percentile(boot, 0.025), percentile(boot, 0.975)],
            }
        paired = {"left_model": left, "right_model": right, "n_matched_tasks": len(task_ids), "metrics": paired}

    result = {"models": summary, "paired_run1": paired}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
