from __future__ import annotations

import argparse
import json
import os
import re
import requests
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "react_experiment"))

from dotenv import load_dotenv
from openai import OpenAI


DATA = ROOT / "pilot" / "pilot_dataset.json"
OUTPUT = ROOT / "pilot" / "model_plans.jsonl"


def tool_catalog(task: dict[str, Any]) -> list[dict[str, Any]]:
    reference = task["reference_plan"]
    tools = []
    seen = set()
    for node in reference["nodes"]:
        if node["tool"] not in seen:
            tools.append(
                {
                    "name": node["tool"],
                    "preconditions": node.get("preconditions", []),
                    "effects": node.get("effects", []),
                }
            )
            seen.add(node["tool"])

    first = reference["nodes"][0]
    tools.append(
        {
            "name": f"retrieve_{task['domain']}_primary",
            "preconditions": first.get("preconditions", []),
            "effects": first.get("effects", []),
        }
    )
    tools.append(
        {
            "name": f"audit_{task['domain']}",
            "preconditions": [f"{task['domain']}_combined"],
            "effects": [f"{task['domain']}_audited"],
        }
    )
    return tools


def extract_json(text: str) -> dict[str, Any]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I | re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def materialize_plan(
    raw: dict[str, Any], catalog: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    specs = {tool["name"]: tool for tool in catalog}
    errors: list[str] = []
    nodes = []
    used_ids = set()
    for index, item in enumerate(raw.get("nodes", []), 1):
        node_id = str(item.get("id", f"n{index}"))
        if node_id in used_ids:
            node_id = f"n{index}"
            errors.append("duplicate_node_id")
        used_ids.add(node_id)
        tool_name = str(item.get("tool", "unknown_tool"))
        spec = specs.get(tool_name)
        if spec is None:
            errors.append(f"unknown_tool:{tool_name}")
            nodes.append(
                {
                    "id": node_id,
                    "tool": tool_name,
                    "preconditions": ["__unknown_tool__"],
                    "effects": [],
                }
            )
        else:
            nodes.append({"id": node_id, **spec, "tool": tool_name})

    valid_ids = {node["id"] for node in nodes}
    edges = []
    for edge in raw.get("edges", []):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source in valid_ids and target in valid_ids:
            edges.append({"source": source, "target": target})
        else:
            errors.append("edge_with_unknown_node")
    return {"nodes": nodes, "edges": edges}, errors


def build_prompt(task: dict[str, Any], tools: list[dict[str, Any]]) -> str:
    return f"""Create an executable tool plan for the task below.

Task: {task['instruction']}
Initial state: {json.dumps(task['initial_state'])}
Required final state: {json.dumps(task['goal'])}
Available tools: {json.dumps(tools)}

Return JSON only, using exactly this schema:
{{
  "nodes": [{{"id": "n1", "tool": "one exact available tool name"}}],
  "edges": [{{"source": "n1", "target": "n2"}}]
}}

An edge means the target depends on the source. Use only listed tools. Include
every tool needed to satisfy the final state, respect preconditions/effects,
and omit unnecessary calls. Independent calls need no edge.
/no_think"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--model")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    load_dotenv(ROOT.parent / "react_experiment" / ".env")
    base_url = os.environ["LLM_BASE_URL"]
    api_key = os.environ["LLM_API_KEY"]
    model = args.model or os.environ["LLM_MODEL"]
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=180)
    tasks = json.loads(DATA.read_text(encoding="utf-8"))
    if args.limit:
        tasks = tasks[: args.limit]

    records = []
    for task in tasks:
        catalog = tool_catalog(task)
        prompt = build_prompt(task, catalog)
        for run in range(1, args.runs + 1):
            started = time.perf_counter()
            try:
                messages = [
                    {
                        "role": "system",
                        "content": "You generate dependency-aware plans as strict JSON.",
                    },
                    {"role": "user", "content": prompt},
                ]
                if "localhost:11434" in base_url:
                    native_url = base_url.replace("/v1", "/api/chat")
                    native = requests.post(
                        native_url,
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": False,
                            "think": False,
                            "options": {
                                "temperature": args.temperature,
                                "seed": run,
                                "num_predict": 1200,
                            },
                        },
                        timeout=180,
                    )
                    native.raise_for_status()
                    text = native.json()["message"]["content"]
                else:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=args.temperature,
                        max_tokens=1200,
                        extra_body={"seed": run},
                    )
                    text = response.choices[0].message.content or ""
                raw = extract_json(text)
                plan, errors = materialize_plan(raw, catalog)
                error = None
            except Exception as exc:  # recorded as experimental failure
                text = locals().get("text", "")
                plan = {"nodes": [], "edges": []}
                errors = []
                error = f"{type(exc).__name__}:{exc}"

            record = {
                "task_id": task["task_id"],
                "domain": task["domain"],
                "model": model,
                "run": run,
                "temperature": args.temperature,
                "latency_seconds": round(time.perf_counter() - started, 3),
                "parse_error": error,
                "validation_errors": errors,
                "raw_response": text,
                "plan": plan,
            }
            records.append(record)
            print(
                f"{task['task_id']} run={run}: nodes={len(plan['nodes'])}, "
                f"edges={len(plan['edges'])}, error={error}"
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} model plans to {args.output}")


if __name__ == "__main__":
    main()
