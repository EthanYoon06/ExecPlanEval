from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "external_validation" / "data" / "external_tasks.jsonl"
PLANS = ROOT / "external_validation" / "results" / "natural_plans.jsonl"
OUTPUT = ROOT / "external_validation" / "results" / "external_scores.csv"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_ ]", " ", text.lower())).strip()


def f1(reference: list[str], prediction: list[str]) -> float:
    ref, pred = Counter(reference), Counter(prediction)
    tp = sum((ref & pred).values())
    precision = tp / sum(pred.values()) if pred else 0.0
    recall = tp / sum(ref.values()) if ref else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def fuzzy_node_f1(reference: list[str], prediction: list[str], threshold: float = 0.65) -> float:
    unmatched = prediction[:]
    matched = 0
    for ref in reference:
        if not unmatched:
            break
        scores = [SequenceMatcher(None, ref, item).ratio() for item in unmatched]
        best = max(range(len(scores)), key=scores.__getitem__)
        if scores[best] >= threshold:
            matched += 1
            unmatched.pop(best)
    precision = matched / len(prediction) if prediction else 0.0
    recall = matched / len(reference) if reference else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def graph_fields(plan: dict) -> tuple[list[str], list[tuple[str, str]], bool]:
    nodes = plan.get("nodes", []) if isinstance(plan, dict) else []
    labels = {str(node.get("id", "")): norm(str(node.get("label", node.get("tool", "")))) for node in nodes}
    edges = []
    graph = nx.DiGraph()
    graph.add_nodes_from(labels)
    edge_valid = True
    for edge in plan.get("edges", []) if isinstance(plan, dict) else []:
        source, target = str(edge.get("source", "")), str(edge.get("target", ""))
        if source not in labels or target not in labels:
            edge_valid = False
            continue
        graph.add_edge(source, target)
        edges.append((labels[source], labels[target]))
    valid = bool(labels) and len(labels) == len(nodes) and edge_valid and nx.is_directed_acyclic_graph(graph)
    return list(labels.values()), edges, valid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plans", type=Path, default=PLANS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    tasks = {task["task_id"]: task for task in read_jsonl(TASKS)}
    rows = []
    for record in read_jsonl(args.plans):
        task = tasks[record["task_id"]]
        ref_nodes, ref_edges, _ = graph_fields(task["reference_plan"])
        pred_nodes, pred_edges, graph_valid = graph_fields(record["plan"])
        catalog = {norm(item["name"]) for item in task.get("available_actions", [])}
        catalog_validity = (
            sum(node in catalog for node in pred_nodes) / len(pred_nodes)
            if catalog and pred_nodes
            else float(graph_valid)
        )
        rows.append(
            {
                "task_id": task["task_id"],
                "benchmark": task["benchmark"],
                "subset": task["subset"],
                "model": record["model"],
                "run": record["run"],
                "parse_success": record.get("parse_error") is None,
                "graph_valid": graph_valid,
                "reference_nodes": len(ref_nodes),
                "predicted_nodes": len(pred_nodes),
                "node_f1": round(f1(ref_nodes, pred_nodes), 6),
                "edge_f1": round(f1([str(x) for x in ref_edges], [str(x) for x in pred_edges]), 6),
                "fuzzy_node_f1": round(fuzzy_node_f1(ref_nodes, pred_nodes), 6),
                "catalog_validity": round(catalog_validity, 6),
                "static_external_score": round((float(graph_valid) + catalog_validity) / 2, 6),
                "latency_seconds": record["latency_seconds"],
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} scored plans to {args.output}")


if __name__ == "__main__":
    main()
