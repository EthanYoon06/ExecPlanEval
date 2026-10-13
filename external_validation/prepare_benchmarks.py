from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORF = ROOT / "external" / "WorFBench" / "gold_traj"
TASKBENCH = ROOT / "external" / "JARVIS" / "taskbench"
OUTPUT = ROOT / "external_validation" / "data" / "external_tasks.jsonl"


def parse_worf_graph(text: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    nodes: list[dict[str, str]] = []
    for node_id, label in re.findall(r"(?m)^\s*(\d+)\s*[:.]\s*(.+?)\s*$", text):
        nodes.append({"id": node_id, "label": label.strip()})
    edges = [
        {"source": source.strip(), "target": target.strip()}
        for source, target in re.findall(r"\(([^,()]+),\s*([^()]+)\)", text)
        if source.strip().upper() != "START" and target.strip().upper() != "END"
    ]
    return nodes, edges


def load_worf(source: str) -> list[dict[str, Any]]:
    path = WORF / source / "graph_eval.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    tasks = []
    for record in records:
        conversations = record["conversations"]
        user = next(item["content"] for item in conversations if item["role"] == "user")
        assistant = next(item["content"] for item in conversations if item["role"] == "assistant")
        nodes, edges = parse_worf_graph(assistant)
        if not nodes:
            continue
        tasks.append(
            {
                "task_id": f"worf_{record['id']}",
                "benchmark": "WorFBench",
                "subset": source,
                "instruction": user,
                "available_actions": [],
                "reference_plan": {"nodes": nodes, "edges": edges},
                "source_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            }
        )
    return tasks


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_taskbench(subset: str) -> list[dict[str, Any]]:
    folder = TASKBENCH / f"data_{subset}"
    tasks = []
    for record in read_jsonl(folder / "data.json"):
        tool_nodes = json.loads(record["tool_nodes"])
        if isinstance(tool_nodes, dict):
            tool_nodes = [tool_nodes]
        tool_nodes = [node for node in tool_nodes if isinstance(node, dict) and node.get("task")]
        if not tool_nodes:
            continue
        nodes = [
            {"id": str(index), "label": node["task"]}
            for index, node in enumerate(tool_nodes, 1)
        ]
        by_label = {node["label"]: node["id"] for node in nodes}
        links = json.loads(record["tool_links"])
        edges = []
        for edge in links:
            source = edge.get("source") or edge.get("from")
            target = edge.get("target") or edge.get("to")
            if source in by_label and target in by_label:
                edges.append({"source": by_label[source], "target": by_label[target]})
        sampled = json.loads(record["sampled_nodes"])
        if isinstance(sampled, dict):
            sampled = [sampled]
        sampled = [item for item in sampled if isinstance(item, dict) and item.get("task")]
        actions = [
            {
                "name": item["task"],
                "arguments": item.get("arguments", []),
            }
            for item in sampled
        ]
        tasks.append(
            {
                "task_id": f"taskbench_{subset}_{record['id']}",
                "benchmark": "TaskBench",
                "subset": subset,
                "instruction": record["instruction"],
                "available_actions": actions,
                "reference_plan": {"nodes": nodes, "edges": edges},
                "topology": record.get("type"),
                "source_path": str((folder / "data.json").relative_to(ROOT)).replace("\\", "/"),
            }
        )
    return tasks


def stratified_sample(items: list[dict[str, Any]], count: int, rng: random.Random) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key = str(item.get("topology") or len(item["reference_plan"]["nodes"]))
        groups.setdefault(key, []).append(item)
    selected: list[dict[str, Any]] = []
    keys = sorted(groups)
    while len(selected) < count and any(groups.values()):
        for key in keys:
            if groups[key] and len(selected) < count:
                index = rng.randrange(len(groups[key]))
                selected.append(groups[key].pop(index))
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-subset", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    collections = {
        "worf_wikihow": load_worf("wikihow"),
        "worf_alfworld": load_worf("alfworld"),
        "worf_webshop": load_worf("webshop"),
        "taskbench_dailylifeapis": load_taskbench("dailylifeapis"),
        "taskbench_multimedia": load_taskbench("multimedia"),
        "taskbench_huggingface": load_taskbench("huggingface"),
    }
    selected_batches = []
    for name, records in collections.items():
        sample = stratified_sample(records, min(args.per_subset, len(records)), rng)
        selected_batches.append(sample)
        print(f"{name}: available={len(records)} selected={len(sample)}")
    selected = [batch[index] for index in range(max(map(len, selected_batches))) for batch in selected_batches if index < len(batch)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {len(selected)} tasks to {args.output}")


if __name__ == "__main__":
    main()
