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
from src.statistics import auroc, spearman
from src.symbolic_executor import execute_plan


DATA = ROOT / "pilot" / "pilot_dataset.json"
RESULTS = ROOT / "pilot" / "pilot_results.csv"
SUMMARY = ROOT / "pilot" / "pilot_summary.json"


def main() -> None:
    tasks = json.loads(DATA.read_text(encoding="utf-8"))
    rows = []
    for task in tasks:
        for candidate in task["candidates"]:
            scores = structural_scores(task["reference_plan"], candidate["plan"])
            execution = execute_plan(task, candidate["plan"])
            proposed = score_plan(task, candidate["plan"])
            rows.append(
                {
                    "task_id": task["task_id"],
                    "domain": task["domain"],
                    "variant": candidate["variant"],
                    "expected_valid": candidate["expected_valid"],
                    "execution_success": execution.success,
                    "node_f1": round(scores["node_f1"], 6),
                    "edge_f1": round(scores["edge_f1"], 6),
                    "goal_coverage": round(float(proposed["goal_coverage"]), 6),
                    "dependency_validity": round(
                        float(proposed["dependency_validity"]), 6
                    ),
                    "executability": round(float(proposed["executability"]), 6),
                    "outcome_success": round(float(proposed["outcome_success"]), 6),
                    "pre_execution_score": round(
                        float(proposed["pre_execution_score"]), 6
                    ),
                    "execplaneval_score": round(
                        float(proposed["execplaneval_score"]), 6
                    ),
                    "failure_reason": execution.failure_reason or "",
                }
            )

    with RESULTS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    by_variant = defaultdict(list)
    for row in rows:
        by_variant[row["variant"]].append(row)
    labels = [bool(row["execution_success"]) for row in rows]
    metric_names = [
        "node_f1",
        "edge_f1",
        "pre_execution_score",
        "execplaneval_score",
    ]
    metric_analysis = {
        metric: {
            "spearman_with_execution": spearman(
                [float(row[metric]) for row in rows],
                [float(label) for label in labels],
            ),
            "auroc_for_valid_plan": auroc(
                [float(row[metric]) for row in rows], labels
            ),
        }
        for metric in metric_names
    }
    summary = {
        "tasks": len(tasks),
        "candidates": len(rows),
        "label_execution_agreement": sum(
            row["expected_valid"] == row["execution_success"] for row in rows
        )
        / len(rows),
        "metric_analysis": metric_analysis,
        "by_variant": {
            variant: {
                "count": len(items),
                "execution_success_rate": sum(
                    item["execution_success"] for item in items
                )
                / len(items),
                "mean_node_f1": sum(item["node_f1"] for item in items) / len(items),
                "mean_edge_f1": sum(item["edge_f1"] for item in items) / len(items),
                "mean_execplaneval_score": sum(
                    item["execplaneval_score"] for item in items
                )
                / len(items),
            }
            for variant, items in sorted(by_variant.items())
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
