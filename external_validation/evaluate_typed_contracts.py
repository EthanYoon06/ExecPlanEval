from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

import networkx as nx

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.statistics import auroc, spearman


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "external_validation/data/external_tasks.jsonl"
PLANS = ROOT / "external_validation/results/natural_plans.jsonl"
LABELS = ROOT / "external_validation/results/human_annotations/adjudicated_labels.json"
OUT_ROWS = ROOT / "external_validation/results/typed_contract_scores.csv"
OUT_SUMMARY = ROOT / "external_validation/results/typed_contract_analysis.json"
TOOL_FILES = {
    "multimedia": ROOT / "external/JARVIS/taskbench/data_multimedia/tool_desc.json",
    "huggingface": ROOT / "external/JARVIS/taskbench/data_huggingface/tool_desc.json",
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def percentile(values: list[float], probability: float) -> float:
    values = sorted(values)
    return values[int(probability * (len(values) - 1))]


def statistics(rows: list[dict], field: str) -> dict:
    scores = [float(row[field]) for row in rows]
    ordinal = [float(row["ordinal_label"]) for row in rows]
    binary = [bool(row["binary_label"]) for row in rows]
    rho = float(spearman(scores, ordinal))
    auc = float(auroc(scores, binary))
    rng = random.Random(20260827)
    rho_samples, auc_samples = [], []
    for _ in range(2000):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        sample_scores = [float(row[field]) for row in sample]
        sample_ordinal = [float(row["ordinal_label"]) for row in sample]
        sample_binary = [bool(row["binary_label"]) for row in sample]
        sampled_rho = float(spearman(sample_scores, sample_ordinal))
        if math.isfinite(sampled_rho):
            rho_samples.append(sampled_rho)
        if len(set(sample_binary)) == 2:
            auc_samples.append(float(auroc(sample_scores, sample_binary)))
    return {
        "spearman_rho": rho,
        "spearman_task_bootstrap_95ci": [percentile(rho_samples, 0.025), percentile(rho_samples, 0.975)],
        "auroc_valid_vs_other": auc,
        "auroc_task_bootstrap_95ci": [percentile(auc_samples, 0.025), percentile(auc_samples, 0.975)],
    }


def main() -> None:
    tasks = {row["task_id"]: row for row in read_jsonl(TASKS)}
    plans = {
        row["task_id"]: row
        for row in read_jsonl(PLANS)
        if int(row["run"]) == 1 and row["subset"] in TOOL_FILES
    }
    label_rows = json.loads(LABELS.read_text(encoding="utf-8"))["annotations"]
    labels = {row["task_id"]: row for row in label_rows}
    label_value = {"Invalid": 0, "Partially valid": 1, "Valid": 2}

    catalogs = {}
    for subset, path in TOOL_FILES.items():
        data = json.loads(path.read_text(encoding="utf-8"))
        catalogs[subset] = {
            norm(tool["id"]): {
                "name": tool["id"],
                "inputs": {norm(value) for value in tool.get("input-type", [])},
                "outputs": {norm(value) for value in tool.get("output-type", [])},
            }
            for tool in data["nodes"]
        }

    rows = []
    for task_id, record in sorted(plans.items()):
        task = tasks[task_id]
        label = labels[task_id]
        catalog = catalogs[task["subset"]]
        plan = record["plan"]
        nodes = plan.get("nodes", [])
        node_by_id = {str(node.get("id")): norm(str(node.get("label", node.get("tool", "")))) for node in nodes}
        graph = nx.DiGraph()
        graph.add_nodes_from(node_by_id)
        edges = plan.get("edges", [])
        endpoints_valid = all(str(edge.get("source")) in node_by_id and str(edge.get("target")) in node_by_id for edge in edges)
        if endpoints_valid:
            graph.add_edges_from((str(edge["source"]), str(edge["target"])) for edge in edges)
        graph_validity = float(bool(nodes) and len(node_by_id) == len(nodes) and endpoints_valid and nx.is_directed_acyclic_graph(graph))
        catalog_validity = sum(name in catalog for name in node_by_id.values()) / len(nodes) if nodes else 0.0

        edge_checks = []
        for edge in edges:
            source = catalog.get(node_by_id.get(str(edge.get("source")), ""))
            target = catalog.get(node_by_id.get(str(edge.get("target")), ""))
            edge_checks.append(bool(source and target and source["outputs"] & target["inputs"]))
        edge_type_compatibility = sum(edge_checks) / len(edge_checks) if edge_checks else 1.0
        typed_contract_score = (graph_validity + catalog_validity + edge_type_compatibility) / 3

        rows.append({
            "task_id": task_id,
            "subset": task["subset"],
            "overall_validity": label["overall_validity"],
            "ordinal_label": label_value[label["overall_validity"]],
            "binary_label": int(label["overall_validity"] == "Valid"),
            "graph_validity": graph_validity,
            "catalog_validity": catalog_validity,
            "edge_type_compatibility": edge_type_compatibility,
            "typed_contract_score": typed_contract_score,
            "edge_count": len(edges),
        })

    if len(rows) != 40:
        raise ValueError(f"Expected 40 typed-contract tasks, found {len(rows)}")
    OUT_ROWS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_ROWS.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "scope": "TaskBench multimedia and huggingface run-1 plans with independently supplied tool input/output types",
        "sample_size": len(rows),
        "subsets": dict(sorted(Counter(row["subset"] for row in rows).items())),
        "label_counts": dict(sorted(Counter(row["overall_validity"] for row in rows).items())),
        "metrics": {
            field: statistics(rows, field)
            for field in ["catalog_validity", "edge_type_compatibility", "typed_contract_score"]
        },
        "means": {
            field: sum(float(row[field]) for row in rows) / len(rows)
            for field in ["graph_validity", "catalog_validity", "edge_type_compatibility", "typed_contract_score"]
        },
        "limitations": [
            "Input/output type overlap tests edge compatibility, not whether every required dependency is present.",
            "Candidate nodes contain tool names but not argument bindings, so argument-level validation is unavailable.",
            "No execution outcome is available; overall validity comes from the adjudicated annotation layer.",
            "The score is a typed-contract diagnostic, not the complete ExecPlanEval score.",
        ],
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
