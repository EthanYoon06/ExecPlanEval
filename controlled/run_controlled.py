from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluate import structural_scores
from src.execplaneval import score_plan
from src.statistics import auroc, cluster_bootstrap_interval, spearman
from src.symbolic_executor import execute_plan


DATA = ROOT / "controlled" / "controlled_dataset.json"
RESULTS = ROOT / "controlled" / "controlled_results.csv"
SUMMARY = ROOT / "controlled" / "controlled_summary.json"


def main() -> None:
    tasks = json.loads(DATA.read_text(encoding="utf-8"))
    rows = []
    for task in tasks:
        for candidate in task["candidates"]:
            plan = candidate["plan"]
            structural = structural_scores(task["reference_plan"], plan)
            proposed = score_plan(task, plan)
            execution = execute_plan(task, plan)
            rows.append(
                {
                    "task_id": task["task_id"],
                    "domain": task["domain"],
                    "topology": task["topology"],
                    "variant": candidate["variant"],
                    "expected_valid": candidate["expected_valid"],
                    "execution_success": execution.success,
                    "node_f1": round(structural["node_f1"], 6),
                    "edge_f1": round(structural["edge_f1"], 6),
                    "dependency_validity": round(float(proposed["dependency_validity"]), 6),
                    "goal_coverage": round(float(proposed["goal_coverage"]), 6),
                    "executability": round(float(proposed["executability"]), 6),
                    "pre_execution_score": round(
                        float(proposed["pre_execution_score"]), 6
                    ),
                    "execplaneval_score": round(
                        float(proposed["execplaneval_score"]), 6
                    ),
                    "without_dependency": round(
                        (
                            float(proposed["goal_coverage"])
                            + float(proposed["executability"])
                            + float(proposed["outcome_success"])
                        )
                        / 3,
                        6,
                    ),
                    "without_static_executability": round(
                        (
                            float(proposed["goal_coverage"])
                            + float(proposed["dependency_validity"])
                            + float(proposed["outcome_success"])
                        )
                        / 3,
                        6,
                    ),
                    "without_outcome": round(
                        (
                            float(proposed["goal_coverage"])
                            + float(proposed["dependency_validity"])
                            + float(proposed["executability"])
                        )
                        / 3,
                        6,
                    ),
                    "dependency_only": round(
                        float(proposed["dependency_validity"]), 6
                    ),
                    "static_executability_only": round(
                        float(proposed["executability"]), 6
                    ),
                    "failure_reason": execution.failure_reason or "",
                }
            )

    with RESULTS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    labels = [bool(row["execution_success"]) for row in rows]
    metrics = [
        "node_f1",
        "edge_f1",
        "pre_execution_score",
        "dependency_only",
        "static_executability_only",
    ]
    analysis = {}
    numeric_labels = [float(label) for label in labels]
    # Each task contributes seven dependent candidate variants. Resample whole
    # tasks so variants derived from the same reference remain together while
    # retaining the 50 independently instantiated task units. Topology is a
    # fixed design factor (five levels), not the sampling unit.
    clusters = [str(row["task_id"]) for row in rows]
    for metric in metrics:
        values = [float(row[metric]) for row in rows]
        rho = spearman(values, numeric_labels)
        auc = auroc(values, labels)
        rho_ci = cluster_bootstrap_interval(
            values,
            labels,
            clusters,
            lambda sampled_scores, sampled_labels: spearman(
                sampled_scores, [float(label) for label in sampled_labels]
            ),
        )
        auc_ci = cluster_bootstrap_interval(values, labels, clusters, auroc)
        analysis[metric] = {
            "spearman_with_execution": rho,
            "spearman_95ci": list(rho_ci),
            "auroc": auc,
            "auroc_95ci": list(auc_ci),
        }

    by_topology = defaultdict(list)
    by_variant = defaultdict(list)
    for row in rows:
        by_topology[row["topology"]].append(row)
        by_variant[row["variant"]].append(row)

    summary = {
        "tasks": len(tasks),
        "candidates": len(rows),
        "label_execution_agreement": sum(
            row["expected_valid"] == row["execution_success"] for row in rows
        )
        / len(rows),
        "metric_analysis": analysis,
        "strict_reference_match": {
            "valid_alternative_rejection_rate": sum(
                row["expected_valid"]
                and row["variant"] != "reference"
                and (row["node_f1"] < 1.0 or row["edge_f1"] < 1.0)
                for row in rows
            )
            / sum(
                row["expected_valid"] and row["variant"] != "reference"
                for row in rows
            ),
            "invalid_plan_false_acceptance_rate": sum(
                not row["expected_valid"]
                and row["node_f1"] == 1.0
                and row["edge_f1"] == 1.0
                for row in rows
            )
            / sum(not row["expected_valid"] for row in rows),
        },
        "by_topology": {
            key: {
                "count": len(items),
                "success_rate": sum(item["execution_success"] for item in items)
                / len(items),
                "mean_edge_f1": sum(item["edge_f1"] for item in items) / len(items),
            }
            for key, items in sorted(by_topology.items())
        },
        "by_variant": {
            key: {
                "count": len(items),
                "success_rate": sum(item["execution_success"] for item in items)
                / len(items),
                "mean_node_f1": sum(item["node_f1"] for item in items) / len(items),
                "mean_edge_f1": sum(item["edge_f1"] for item in items) / len(items),
                "mean_pre_execution_score": sum(
                    item["pre_execution_score"] for item in items
                )
                / len(items),
            }
            for key, items in sorted(by_variant.items())
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
