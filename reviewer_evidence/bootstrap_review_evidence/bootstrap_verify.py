from __future__ import annotations

import argparse
import collections
import csv
import json
import random
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score


METRICS = ["node_f1", "edge_f1", "pre_execution_score", "dependency_only", "static_executability_only"]


def fixed_index_interval(values: list[float]) -> list[float]:
    """Match the manuscript's non-interpolated 2,000-replicate definition."""
    ordered = sorted(values)
    return [ordered[50], ordered[1950]]


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Independently verify the controlled task-cluster bootstrap.")
    parser.add_argument("--dataset", type=Path, default=base / "controlled_dataset.json")
    parser.add_argument("--results", type=Path, default=base / "controlled_results.csv")
    parser.add_argument("--summary", type=Path, default=base / "controlled_summary.json")
    parser.add_argument("--output", type=Path, default=base / "bootstrap_independent_verification_rerun.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = list(csv.DictReader(args.results.open(newline="", encoding="utf-8")))
    tasks = json.loads(args.dataset.read_text(encoding="utf-8"))
    summary = json.loads(args.summary.read_text(encoding="utf-8"))

    counts = collections.Counter(row["task_id"] for row in rows)
    variants = {task["task_id"]: {candidate["variant"] for candidate in task["candidates"]} for task in tasks}
    assert len(tasks) == 50 and len(rows) == 350 and len(counts) == 50
    assert set(counts.values()) == {7}
    assert all(len(value) == 7 for value in variants.values())
    assert set(counts) == set(variants)
    assert all(str(row["expected_valid"]).lower() == str(row["execution_success"]).lower() for row in rows)

    labels = np.array([row["execution_success"] == "True" for row in rows], dtype=int)
    task_ids = sorted(counts)
    indices = {task_id: np.array([index for index, row in enumerate(rows) if row["task_id"] == task_id]) for task_id in task_ids}

    rng = random.Random(20260826)
    replicates = [
        [index for task_id in [rng.choice(task_ids) for _ in task_ids] for index in indices[task_id]]
        for _ in range(2000)
    ]

    by_topology: dict[str, list[str]] = collections.defaultdict(list)
    for task in tasks:
        by_topology[task["topology"]].append(task["task_id"])
    rng = random.Random(20260826)
    stratified = [
        [index for topology in sorted(by_topology) for task_id in [rng.choice(sorted(by_topology[topology])) for _ in by_topology[topology]] for index in indices[task_id]]
        for _ in range(2000)
    ]

    results: dict[str, dict[str, object]] = {}
    for metric in METRICS:
        values = np.array([float(row[metric]) for row in rows])
        rho = float(spearmanr(values, labels).statistic)
        auc = float(roc_auc_score(labels, values))
        saved = summary["metric_analysis"][metric]
        rho_replicates = [float(spearmanr(values[ix], labels[ix]).statistic) for ix in replicates]
        auc_replicates = [float(roc_auc_score(labels[ix], values[ix])) for ix in replicates]
        stratified_rho = [float(spearmanr(values[ix], labels[ix]).statistic) for ix in stratified]
        stratified_auc = [float(roc_auc_score(labels[ix], values[ix])) for ix in stratified]
        independent_rho_ci = fixed_index_interval(rho_replicates)
        independent_auc_ci = fixed_index_interval(auc_replicates)
        results[metric] = {
            "rho": rho,
            "auc": auc,
            "rho_saved": saved["spearman_with_execution"],
            "auc_saved": saved["auroc"],
            "point_matches": abs(rho - saved["spearman_with_execution"]) < 1e-12 and abs(auc - saved["auroc"]) < 1e-12,
            "independent_task_cluster_ci": {"rho": independent_rho_ci, "auc": independent_auc_ci},
            "saved_ci": {"rho": saved["spearman_95ci"], "auc": saved["auroc_95ci"]},
            "ci_matches": np.allclose(independent_rho_ci, saved["spearman_95ci"], rtol=0.0, atol=1e-12) and np.allclose(independent_auc_ci, saved["auroc_95ci"], rtol=0.0, atol=1e-12),
            "topology_stratified_task_cluster_ci": {"rho": fixed_index_interval(stratified_rho), "auc": fixed_index_interval(stratified_auc)},
        }

    output = {
        "integrity": {
            "tasks": len(tasks), "rows": len(rows), "clusters": len(counts), "rows_per_cluster": 7,
            "topologies": dict(collections.Counter(task["topology"] for task in tasks)),
            "label_execution_agreement": float(np.mean([row["expected_valid"] == row["execution_success"] for row in rows])),
        },
        "resampling": {
            "replicates": 2000, "seed": 20260826,
            "method": "non-interpolated percentile indices 50 and 1950",
            "note": "Independent random.choices, scipy.stats.spearmanr, and sklearn.metrics.roc_auc_score implementation; the original src/statistics.py is not imported.",
        },
        "metrics": results,
    }
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
