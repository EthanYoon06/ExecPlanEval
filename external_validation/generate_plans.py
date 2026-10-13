from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "external_validation" / "data" / "external_tasks.jsonl"
OUTPUT = ROOT / "external_validation" / "results" / "natural_plans.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I | re.S)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def prompt(task: dict) -> str:
    actions = task.get("available_actions") or "Use only actions explicitly described in the task."
    return f"""Create a dependency-aware plan for the user task.

User task:
{task['instruction']}

Available actions/tools:
{json.dumps(actions, ensure_ascii=False)}

Do not assume access to a reference answer. Return JSON only:
{{
  "nodes": [{{"id": "1", "label": "specific action or exact tool name"}}],
  "edges": [{{"source": "1", "target": "2"}}]
}}
An edge means the target depends on the source. Include only necessary actions.
/no_think"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DATA)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--json-format", action="store_true", help="Request Ollama JSON-constrained decoding")
    parser.add_argument("--resume", action="store_true", help="Append and skip completed task/model/run keys")
    args = parser.parse_args()
    tasks = read_jsonl(args.input)
    if args.limit:
        tasks = tasks[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    completed = set()
    if args.resume and args.output.exists():
        for record in read_jsonl(args.output):
            completed.add((record["task_id"], record["model"], int(record["run"])))
    mode = "a" if args.resume else "w"
    with args.output.open(mode, encoding="utf-8") as handle:
        for task in tasks:
            for run in range(1, args.runs + 1):
                key = (task["task_id"], args.model, run)
                if key in completed:
                    print(task["task_id"], run, "skipped")
                    continue
                started = time.perf_counter()
                text = ""
                error = None
                plan = {"nodes": [], "edges": []}
                try:
                    payload = {
                            "model": args.model,
                            "messages": [
                                {"role": "system", "content": "You produce concise plan graphs as strict JSON."},
                                {"role": "user", "content": prompt(task)},
                            ],
                            "stream": False,
                            "think": False,
                            "options": {"temperature": args.temperature, "seed": run, "num_predict": 900},
                        }
                    if args.json_format:
                        payload["format"] = "json"
                    request = urllib.request.Request(
                        f"{args.base_url}/api/chat",
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(request, timeout=240) as response:
                        text = json.loads(response.read().decode("utf-8"))["message"]["content"]
                    plan = extract_json(text)
                except Exception as exc:
                    error = f"{type(exc).__name__}:{exc}"
                record = {
                    "task_id": task["task_id"],
                    "benchmark": task["benchmark"],
                    "subset": task["subset"],
                    "model": args.model,
                    "run": run,
                    "temperature": args.temperature,
                    "json_format": args.json_format,
                    "latency_seconds": round(time.perf_counter() - started, 3),
                    "parse_error": error,
                    "raw_output": text,
                    "plan": plan,
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(task["task_id"], run, "ok" if error is None else error)


if __name__ == "__main__":
    main()
