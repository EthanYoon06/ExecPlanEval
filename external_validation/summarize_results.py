from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORES = ROOT / "external_validation" / "results" / "external_scores.csv"
PLANS = ROOT / "external_validation" / "results" / "natural_plans.jsonl"
SUMMARY = ROOT / "external_validation" / "results" / "summary_by_subset.csv"


def mean_sd(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def jaccard(left: set, right: set) -> float:
    return len(left & right) / len(left | right) if left | right else 1.0


def main() -> None:
    score_rows = list(csv.DictReader(SCORES.open(encoding="utf-8-sig")))
    plan_rows = [json.loads(line) for line in PLANS.read_text(encoding="utf-8").splitlines() if line]
    runs_by_task: dict[str, list[dict]] = defaultdict(list)
    for row in plan_rows:
        runs_by_task[row["task_id"]].append(row)

    stability = {}
    for task_id, runs in runs_by_task.items():
        node_scores, edge_scores = [], []
        for left, right in combinations(runs, 2):
            left_nodes = {str(n.get("label", "")).strip().casefold() for n in left["plan"].get("nodes", [])}
            right_nodes = {str(n.get("label", "")).strip().casefold() for n in right["plan"].get("nodes", [])}
            left_edges = {(str(e.get("source")), str(e.get("target"))) for e in left["plan"].get("edges", [])}
            right_edges = {(str(e.get("source")), str(e.get("target"))) for e in right["plan"].get("edges", [])}
            node_scores.append(jaccard(left_nodes, right_nodes))
            edge_scores.append(jaccard(left_edges, right_edges))
        stability[task_id] = (
            statistics.mean(node_scores) if node_scores else 1.0,
            statistics.mean(edge_scores) if edge_scores else 1.0,
        )

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in score_rows:
        groups[(row["benchmark"], row["subset"])].append(row)
    groups[("ALL", "ALL")] = score_rows

    fields = ["benchmark", "subset", "n", "parse_success_rate", "graph_valid_rate", "node_f1_mean", "node_f1_sd", "edge_f1_mean", "edge_f1_sd", "fuzzy_node_f1_mean", "catalog_validity_mean", "node_stability", "edge_stability", "latency_mean_seconds"]
    output = []
    for (benchmark, subset), rows in groups.items():
        node = [float(r["node_f1"]) for r in rows]
        edge = [float(r["edge_f1"]) for r in rows]
        fuzzy = [float(r["fuzzy_node_f1"]) for r in rows]
        catalog = [float(r["catalog_validity"]) for r in rows]
        unique_tasks = sorted({r["task_id"] for r in rows})
        node_stability = [stability[task][0] for task in unique_tasks]
        edge_stability = [stability[task][1] for task in unique_tasks]
        node_mean, node_sd = mean_sd(node)
        edge_mean, edge_sd = mean_sd(edge)
        output.append({
            "benchmark": benchmark,
            "subset": subset,
            "n": len(rows),
            "parse_success_rate": statistics.mean(r["parse_success"] == "True" for r in rows),
            "graph_valid_rate": statistics.mean(r["graph_valid"] == "True" for r in rows),
            "node_f1_mean": node_mean,
            "node_f1_sd": node_sd,
            "edge_f1_mean": edge_mean,
            "edge_f1_sd": edge_sd,
            "fuzzy_node_f1_mean": statistics.mean(fuzzy),
            "catalog_validity_mean": statistics.mean(catalog),
            "node_stability": statistics.mean(node_stability),
            "edge_stability": statistics.mean(edge_stability),
            "latency_mean_seconds": statistics.mean(float(r["latency_seconds"]) for r in rows),
        })
    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in output:
            writer.writerow({key: round(value, 6) if isinstance(value, float) else value for key, value in row.items()})
    print(f"Wrote {len(output)} summary rows to {SUMMARY}")


if __name__ == "__main__":
    main()
