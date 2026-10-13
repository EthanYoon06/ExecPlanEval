from __future__ import annotations

import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "external_validation/data/external_tasks.jsonl"
PLANS = ROOT / "external_validation/results/natural_plans.jsonl"
OUTPUT = ROOT / "external_validation/results/chinese_translations.jsonl"


def stable_hash(text: str) -> int:
    value = 2166136261
    for char in text:
        value = ((value ^ ord(char)) * 16777619) & 0xFFFFFFFF
    return value


def request_translation(instruction: str, plan_text: str) -> dict[str, str]:
    prompt = f"""你是一名科研数据翻译员。把下面用于任务规划标注的英文内容准确翻译成简体中文。
要求：
1. 不评价计划，不补充或删除步骤，不暗示正确答案。
2. 工具名、API名、模型名、参数名和ID保留英文，可在后面加中文解释。
3. source、target和依赖边编号原样保留。
4. URL和JSON图片元数据可简写为“[图片信息]”，但其后有动作文字时必须翻译。
5. 仅返回JSON对象，键必须是 instruction_zh 和 candidate_plan_zh。

任务说明：
{instruction}

候选计划：
{plan_text}
"""
    schema = {
        "type": "object",
        "properties": {
            "instruction_zh": {"type": "string"},
            "candidate_plan_zh": {"type": "string"},
        },
        "required": ["instruction_zh", "candidate_plan_zh"],
    }
    for attempt in range(3):
        payload = json.dumps({
            "model": "qwen3:8b",
            "prompt": prompt,
            "stream": False,
            "think": False,
            "format": schema,
            "options": {"temperature": 0, "num_predict": 4000 + attempt * 1000},
        }).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
        try:
            translated = json.loads(result["response"])
            return {
                "instruction_zh": str(translated["instruction_zh"]).strip(),
                "candidate_plan_zh": str(translated["candidate_plan_zh"]).strip(),
            }
        except (json.JSONDecodeError, KeyError):
            if attempt == 2:
                raise
    raise RuntimeError("translation failed")


def main() -> None:
    tasks = {
        row["task_id"]: row
        for row in (
            json.loads(line) for line in TASKS.read_text(encoding="utf-8").splitlines() if line
        )
    }
    plans = [
        json.loads(line)
        for line in PLANS.read_text(encoding="utf-8").splitlines()
        if line
    ]
    run1 = sorted(
        (row for row in plans if int(row["run"]) == 1),
        key=lambda row: stable_hash(row["task_id"]),
    )
    completed = {}
    if OUTPUT.exists():
        for line in OUTPUT.read_text(encoding="utf-8").splitlines():
            if line:
                row = json.loads(line)
                completed[row["task_id"]] = row

    with OUTPUT.open("a", encoding="utf-8") as handle:
        for index, record in enumerate(run1, start=1):
            task_id = record["task_id"]
            if task_id in completed:
                continue
            plan = record.get("plan") or {"nodes": [], "edges": []}
            node_text = "\n".join(
                f'{node.get("id", "")}. {node.get("label", node.get("tool", ""))}'
                for node in plan.get("nodes", [])
            )
            edge_text = "; ".join(
                f'{edge.get("source", "")} -> {edge.get("target", "")}'
                for edge in plan.get("edges", [])
            ) or "No dependency edges"
            plan_text = f"{node_text}\nDependency edges: {edge_text}"
            translated = request_translation(tasks[task_id]["instruction"], plan_text)
            output = {
                "annotation_id": f"P{index:04d}",
                "task_id": task_id,
                **translated,
            }
            handle.write(json.dumps(output, ensure_ascii=False) + "\n")
            handle.flush()
            print(f"translated {index}/120 {task_id}", flush=True)


if __name__ == "__main__":
    main()
