from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluate import structural_scores
from src.execplaneval import score_plan
from src.statistics import auroc, spearman
from src.symbolic_executor import execute_plan


TASKS = ROOT / "pilot" / "pilot_dataset.json"
PLANS = ROOT / "pilot" / "model_plans.jsonl"
OUTPUT = ROOT / "pilot" / "model_plan_results.csv"
SUMMARY = ROOT / "pilot" / "model_plan_summary.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plans", type=Path, default=PLANS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--summary", type=Path, default=SUMMARY)
    args = parser.parse_args()
    tasks = {
        task["task_id"]: task
        for task in json.loads(TASKS.read_text(encoding="utf-8"))
    }
    records = [
        json.loads(line)
        for line in args.plans.read_text(encoding="utf-8").splitlines()
    ]
    rows = []
    for record in records:
        task = tasks[record["task_id"]]
        plan = record["plan"]
        structural = structural_scores(task["reference_plan"], plan)
        proposed = score_plan(task, plan)
        execution = execute_plan(task, plan)
        rows.append(
            {
                "task_id": record["task_id"],
                "domain": record["domain"],
                "model": record["model"],
                "run": record["run"],
                "parse_success": record["parse_error"] is None,
                "validation_error_count": len(record["validation_errors"]),
                "execution_success": execution.success,
                "node_f1": round(structural["node_f1"], 6),
                "edge_f1": round(structural["edge_f1"], 6),
                "dependency_validity": round(float(proposed["dependency_validity"]), 6),
                "executability": round(float(proposed["executability"]), 6),
                "pre_execution_score": round(
                    float(proposed["pre_execution_score"]), 6
                ),
                "execplaneval_score": round(
                    float(proposed["execplaneval_score"]), 6
                ),
                "latency_seconds": record["latency_seconds"],
                "failure_reason": execution.failure_reason or "",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    labels = [bool(row["execution_success"]) for row in rows]
    metrics = ["node_f1", "edge_f1", "pre_execution_score", "execplaneval_score"]
    analysis = {}
    if any(labels) and not all(labels):
        for metric in metrics:
            values = [float(row[metric]) for row in rows]
            analysis[metric] = {
                "spearman_with_execution": spearman(
                    values, [float(label) for label in labels]
                ),
                "auroc": auroc(values, labels),
            }

    summary = {
        "plans": len(rows),
        "parse_success_rate": sum(row["parse_success"] for row in rows) / len(rows),
        "execution_success_rate": sum(labels) / len(labels),
        "mean_latency_seconds": sum(row["latency_seconds"] for row in rows) / len(rows),
        "metric_analysis": analysis,
    }
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
