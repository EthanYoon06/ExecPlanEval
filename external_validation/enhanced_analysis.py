from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.statistics import auroc, spearman


ROOT = Path(__file__).resolve().parents[1]
SCORES = ROOT / "external_validation/results/external_scores.csv"
TASKS = ROOT / "external_validation/data/external_tasks.jsonl"
PLANS = ROOT / "external_validation/results/natural_plans.jsonl"
LABELS = ROOT / "external_validation/results/ai_annotations/audited_labels.json"
CONTROLLED = ROOT / "controlled/controlled_results.csv"
OUT_JSON = ROOT / "external_validation/results/enhanced_analysis.json"
OUT_CSV = ROOT / "external_validation/results/enhanced_analysis_by_subset.csv"
WEIGHTS_CSV = ROOT / "controlled/weight_sensitivity.csv"


def stable_hash(text: str) -> int:
    value = 2166136261
    for char in text:
        value = ((value ^ ord(char)) * 16777619) & 0xFFFFFFFF
    return value


def bootstrap_ci(rows: list[dict], metric: str, statistic, seed: int = 20260827) -> list[float | None]:
    rng = random.Random(seed)
    values = []
    for _ in range(2000):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        try:
            value = statistic(sample, metric)
            if value is not None and math.isfinite(value):
                values.append(value)
        except ValueError:
            pass
    if not values:
        return [None, None]
    values.sort()
    return [values[int(0.025 * (len(values) - 1))], values[int(0.975 * (len(values) - 1))]]


def ordinal_rho(rows: list[dict], metric: str) -> float | None:
    x = [float(row[metric]) for row in rows]
    y = [float(row["ordinal_label"]) for row in rows]
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return float(spearman(x, y))


def binary_auc(rows: list[dict], metric: str) -> float | None:
    y = [int(row["binary_label"]) for row in rows]
    if len(set(y)) < 2:
        return None
    return float(auroc([float(row[metric]) for row in rows], [bool(value) for value in y]))


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position + 1
        while end < len(order) and values[order[end]] == values[order[position]]:
            end += 1
        average_rank = (position + 1 + end) / 2
        for location in range(position, end):
            ranks[order[location]] = average_rank
        position = end
    return ranks


def centered_rho(rows: list[dict], metric: str) -> float | None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["subset_key"]].append(row)
    x_resid, y_resid = [], []
    for group in grouped.values():
        xs = rankdata([float(row[metric]) for row in group])
        ys = rankdata([float(row["ordinal_label"]) for row in group])
        x_mean, y_mean = sum(xs) / len(xs), sum(ys) / len(ys)
        x_resid.extend(value - x_mean for value in xs)
        y_resid.extend(value - y_mean for value in ys)
    if len(set(x_resid)) < 2 or len(set(y_resid)) < 2:
        return None
    return float(spearman(x_resid, y_resid))


def summarize(rows: list[dict], metric: str) -> dict:
    return {
        "rho": ordinal_rho(rows, metric),
        "rho_task_bootstrap_95ci": bootstrap_ci(rows, metric, ordinal_rho),
        "auroc_valid_vs_other": binary_auc(rows, metric),
        "auroc_task_bootstrap_95ci": bootstrap_ci(rows, metric, binary_auc),
    }


def main() -> None:
    run1 = {
        row["task_id"]: row
        for row in csv.DictReader(SCORES.open(encoding="utf-8-sig"))
        if int(row["run"]) == 1
    }
    tasks = [json.loads(line) for line in TASKS.read_text(encoding="utf-8").splitlines() if line]
    task_by_id = {row["task_id"]: row for row in tasks}
    ordered_ids = sorted(run1, key=stable_hash)
    label_data = json.loads(LABELS.read_text(encoding="utf-8"))["annotations"]
    label_by_id = {row["annotation_id"]: row for row in label_data}
    label_value = {"Invalid": 0, "Partially valid": 1, "Valid": 2}

    rows = []
    for index, task_id in enumerate(ordered_ids, start=1):
        annotation = label_by_id[f"P{index:04d}"]
        score = dict(run1[task_id])
        task = task_by_id[task_id]
        score["overall_validity"] = annotation["overall_validity"]
        score["ordinal_label"] = label_value[annotation["overall_validity"]]
        score["binary_label"] = int(annotation["overall_validity"] == "Valid")
        score["subset_key"] = f'{score["benchmark"]}:{score["subset"]}'
        score["graph_overlap"] = (
            float(score["node_f1"]) + float(score["edge_f1"])
        ) / 2
        score["reference_size"] = len(task["reference_plan"]["nodes"])
        rows.append(score)

    metrics = ["node_f1", "edge_f1", "fuzzy_node_f1", "graph_overlap", "catalog_validity"]
    overall = {metric: summarize(rows, metric) for metric in metrics}
    for metric in metrics:
        overall[metric]["within_subset_centered_rho"] = centered_rho(rows, metric)

    subset_rows = []
    by_subset: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_subset[row["subset_key"]].append(row)
    for key, group in sorted(by_subset.items()):
        counts = Counter(row["overall_validity"] for row in group)
        for metric in metrics:
            summary = summarize(group, metric)
            subset_rows.append({
                "subset": key,
                "n": len(group),
                "valid": counts["Valid"],
                "partial": counts["Partially valid"],
                "invalid": counts["Invalid"],
                "metric": metric,
                "rho": summary["rho"],
                "auroc_valid_vs_other": summary["auroc_valid_vs_other"],
            })

    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(subset_rows[0]))
        writer.writeheader()
        writer.writerows(subset_rows)

    controlled = list(csv.DictReader(CONTROLLED.open(encoding="utf-8-sig")))
    labels = [row["execution_success"].lower() == "true" for row in controlled]
    weight_rows = []
    for dep_weight_int in range(0, 21):
        dep_weight = dep_weight_int / 20
        scores = [
            dep_weight * float(row["dependency_validity"])
            + (1 - dep_weight) * float(row["executability"])
            for row in controlled
        ]
        weight_rows.append({
            "dependency_weight": dep_weight,
            "executability_weight": 1 - dep_weight,
            "spearman": float(spearman(scores, [float(v) for v in labels])),
            "auroc": float(auroc(scores, labels)),
        })
    with WEIGHTS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(weight_rows[0]))
        writer.writeheader()
        writer.writerows(weight_rows)

    result = {
        "label_source": "assistant-audited AI-assisted labels; not human ground truth",
        "sample_size": len(rows),
        "overall": overall,
        "label_counts_by_subset": {
            key: dict(Counter(row["overall_validity"] for row in group))
            for key, group in sorted(by_subset.items())
        },
        "weight_sensitivity": weight_rows,
        "diagnostic_cases": {
            "lowest_node_f1_labeled_valid": min(
                (
                    {
                        "task_id": row["task_id"],
                        "subset": row["subset_key"],
                        "node_f1": float(row["node_f1"]),
                        "edge_f1": float(row["edge_f1"]),
                    }
                    for row in rows
                    if row["overall_validity"] == "Valid"
                ),
                key=lambda row: row["node_f1"],
            ),
            "highest_node_f1_labeled_invalid": max(
                (
                    {
                        "task_id": row["task_id"],
                        "subset": row["subset_key"],
                        "node_f1": float(row["node_f1"]),
                        "edge_f1": float(row["edge_f1"]),
                    }
                    for row in rows
                    if row["overall_validity"] == "Invalid"
                ),
                key=lambda row: row["node_f1"],
            ),
        },
        "interpretation_guardrail": (
            "Pooled estimates are exploratory. Within-subset centered correlations remove "
            "between-subset rank shifts but do not make AI labels independent ground truth."
        ),
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
