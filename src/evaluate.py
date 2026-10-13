from __future__ import annotations

from collections import Counter
from typing import Any, Hashable


def _f1(reference: list[Hashable], prediction: list[Hashable]) -> dict[str, float]:
    ref = Counter(reference)
    pred = Counter(prediction)
    true_positive = sum((ref & pred).values())
    predicted = sum(pred.values())
    relevant = sum(ref.values())
    precision = true_positive / predicted if predicted else 0.0
    recall = true_positive / relevant if relevant else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def structural_scores(
    reference: dict[str, Any], prediction: dict[str, Any]
) -> dict[str, float]:
    ref_nodes = [node["tool"] for node in reference["nodes"]]
    pred_nodes = [node["tool"] for node in prediction["nodes"]]

    def edge_labels(plan: dict[str, Any]) -> list[tuple[str, str]]:
        tools = {node["id"]: node["tool"] for node in plan["nodes"]}
        return [
            (tools[edge["source"]], tools[edge["target"]])
            for edge in plan["edges"]
            if edge["source"] in tools and edge["target"] in tools
        ]

    node = _f1(ref_nodes, pred_nodes)
    edge = _f1(edge_labels(reference), edge_labels(prediction))
    return {
        "node_precision": node["precision"],
        "node_recall": node["recall"],
        "node_f1": node["f1"],
        "edge_precision": edge["precision"],
        "edge_recall": edge["recall"],
        "edge_f1": edge["f1"],
    }

