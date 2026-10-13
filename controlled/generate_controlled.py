from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "controlled" / "controlled_dataset.json"

DOMAINS = [
    "travel",
    "weather",
    "shopping",
    "media",
    "document",
    "meeting",
    "finance",
    "support",
    "research",
    "security",
]

TOPOLOGIES: dict[str, list[tuple[str, str]]] = {
    "chain4": [("n1", "n2"), ("n2", "n3"), ("n3", "n4")],
    "diamond4": [("n1", "n3"), ("n2", "n3"), ("n3", "n4")],
    "fork_join5": [
        ("n1", "n2"),
        ("n1", "n3"),
        ("n1", "n4"),
        ("n2", "n5"),
        ("n3", "n5"),
        ("n4", "n5"),
    ],
    "double_diamond6": [
        ("n1", "n3"),
        ("n2", "n3"),
        ("n3", "n4"),
        ("n3", "n5"),
        ("n4", "n6"),
        ("n5", "n6"),
    ],
    "chain6": [
        ("n1", "n2"),
        ("n2", "n3"),
        ("n3", "n4"),
        ("n4", "n5"),
        ("n5", "n6"),
    ],
}


def build_task(index: int, domain: str, topology: str) -> dict[str, Any]:
    edges = TOPOLOGIES[topology]
    node_ids = sorted({item for edge in edges for item in edge})
    graph = nx.DiGraph(edges)
    initial = [f"{domain}_{topology}_input"]
    goal = [f"{domain}_{topology}_goal"]
    nodes = []
    for node_id in node_ids:
        predecessors = list(graph.predecessors(node_id))
        preconditions = (
            initial
            if not predecessors
            else [f"{domain}_{topology}_{pred}_done" for pred in predecessors]
        )
        effects = [f"{domain}_{topology}_{node_id}_done"]
        if graph.out_degree(node_id) == 0:
            effects.append(goal[0])
        nodes.append(
            {
                "id": node_id,
                "tool": f"{domain}_{topology}_tool_{node_id}",
                "preconditions": preconditions,
                "effects": effects,
            }
        )
    reference = {
        "nodes": nodes,
        "edges": [{"source": source, "target": target} for source, target in edges],
    }
    task = {
        "task_id": f"controlled_{index:03d}",
        "domain": domain,
        "topology": topology,
        "instruction": f"Complete the {domain} workflow with {topology} dependencies.",
        "initial_state": initial,
        "goal": goal,
        "reference_plan": reference,
        "tool_catalog": [
            {"name": node["tool"], "preconditions": node["preconditions"], "effects": node["effects"]}
            for node in nodes
        ]
        + [
            {
                "name": nodes[0]["tool"] + "_equivalent",
                "preconditions": nodes[0]["preconditions"],
                "effects": nodes[0]["effects"],
            },
            {
                "name": f"audit_{domain}_{topology}",
                "preconditions": goal,
                "effects": [f"controlled_{index:03d}_audited"],
            },
        ],
    }
    task["candidates"] = make_variants(task)
    return task


def incomparable_pair(plan: dict[str, Any]) -> tuple[str, str] | None:
    graph = nx.DiGraph((edge["source"], edge["target"]) for edge in plan["edges"])
    ids = sorted(node["id"] for node in plan["nodes"])
    for left_index, left in enumerate(ids):
        for right in ids[left_index + 1 :]:
            if not nx.has_path(graph, left, right) and not nx.has_path(graph, right, left):
                return left, right
    return None


def make_variants(task: dict[str, Any]) -> list[dict[str, Any]]:
    reference = task["reference_plan"]
    variants = []

    def add(name: str, valid: bool, plan: dict[str, Any]) -> None:
        variants.append({"variant": name, "expected_valid": valid, "plan": plan})

    add("reference", True, copy.deepcopy(reference))

    serialized = copy.deepcopy(reference)
    pair = incomparable_pair(serialized)
    if pair:
        serialized["edges"].append({"source": pair[0], "target": pair[1]})
    add("valid_serialization", True, serialized)

    equivalent = copy.deepcopy(reference)
    equivalent["nodes"][0]["tool"] += "_equivalent"
    add("valid_equivalent_tool", True, equivalent)

    redundant = copy.deepcopy(reference)
    sinks = {
        node["id"]
        for node in redundant["nodes"]
        if not any(edge["source"] == node["id"] for edge in redundant["edges"])
    }
    sink = sorted(sinks)[0]
    redundant["nodes"].append(
        {
            "id": "audit",
            "tool": f"audit_{task['domain']}_{task['topology']}",
            "preconditions": task["goal"],
            "effects": [f"{task['task_id']}_audited"],
        }
    )
    redundant["edges"].append({"source": sink, "target": "audit"})
    add("valid_redundant_audit", True, redundant)

    missing = copy.deepcopy(reference)
    graph = nx.DiGraph((edge["source"], edge["target"]) for edge in missing["edges"])
    sink = sorted(node for node in graph if graph.out_degree(node) == 0)[0]
    predecessor = sorted(graph.predecessors(sink))[0]
    missing["nodes"] = [node for node in missing["nodes"] if node["id"] != predecessor]
    missing["edges"] = [
        edge
        for edge in missing["edges"]
        if predecessor not in (edge["source"], edge["target"])
    ]
    add("invalid_missing_required", False, missing)

    reversed_plan = copy.deepcopy(reference)
    first_edge = reversed_plan["edges"][0]
    reversed_plan["edges"][0] = {
        "source": first_edge["target"],
        "target": first_edge["source"],
    }
    add("invalid_reversed_dependency", False, reversed_plan)

    wrong_tool = copy.deepcopy(reference)
    wrong_tool["nodes"][0]["tool"] = "unavailable_tool"
    wrong_tool["nodes"][0]["preconditions"] = ["__unavailable__"]
    wrong_tool["nodes"][0]["effects"] = []
    add("invalid_wrong_tool", False, wrong_tool)
    return variants


def main() -> None:
    tasks = []
    index = 0
    for domain in DOMAINS:
        for topology in TOPOLOGIES:
            index += 1
            tasks.append(build_task(index, domain, topology))
    OUTPUT.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    print(f"Wrote {len(tasks)} tasks and {sum(len(t['candidates']) for t in tasks)} candidates")


if __name__ == "__main__":
    main()
