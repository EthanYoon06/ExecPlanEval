from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = "/mnt/c/Users/YKJ/Documents/New project 2/execplaneval/external_validation/alfworld_env_worker.py"


def worker_call(process: subprocess.Popen[str], payload: dict) -> dict:
    assert process.stdin and process.stdout
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()
    line = process.stdout.readline()
    if not line:
        error = process.stderr.read() if process.stderr else ""
        raise RuntimeError(f"ALFWorld worker terminated unexpectedly: {error[-1000:]}")
    return json.loads(line)


def generate_plan(model: str, objective: str, observation: str, initial_commands: list[str], max_actions: int, json_format: bool) -> tuple[list[str], str, bool]:
    prompt = f"""Generate one frozen open-loop action plan for an ALFWorld text game.
You will not receive observations and cannot replan after execution begins.
Goal: {objective}
Initial observation: {observation}
Initially admissible commands (these also demonstrate exact command syntax):
{json.dumps(initial_commands, ensure_ascii=False)}

Return at most {max_actions} concrete commands. You may include exploration of likely receptacles,
but every entry must be a single ALFWorld command with concrete object/receptacle identifiers.
No prose, conditionals, placeholders, comments, or alternatives.
Return strict JSON only: {{"actions":["command 1","command 2"]}}"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Output one strict JSON frozen action sequence."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 1000},
    }
    if json_format:
        payload["format"] = "json"
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        raw = json.loads(response.read().decode())["message"]["content"]
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.S)
    parse_success = True
    try:
        data = json.loads(cleaned)
        actions = data.get("actions", [])
    except json.JSONDecodeError:
        match = re.search(r'"actions"\s*:\s*(\[[\s\S]*?\])', cleaned)
        try:
            actions = json.loads(match.group(1)) if match else []
        except json.JSONDecodeError:
            actions = []
        parse_success = bool(match) and bool(actions)
    actions = [str(action).strip() for action in actions if str(action).strip()]
    return actions[:max_actions], raw, parse_success


def schema_valid(action: str) -> bool:
    patterns = [
        r"go to .+", r"open .+", r"close .+", r"take .+ from .+",
        r"put .+ (?:in|on|in/on) .+", r"clean .+ with .+", r"heat .+ with .+",
        r"cool .+ with .+", r"use .+", r"examine .+", r"move .+ to .+", r"look(?: .+)?",
    ]
    return any(re.fullmatch(pattern, action.strip(), flags=re.I) for pattern in patterns)


def abstract_dependency_score(actions: list[str]) -> float:
    location = None
    inventory: set[str] = set()
    checks: list[bool] = []
    for action in actions:
        lower = action.lower().strip()
        match = re.fullmatch(r"go to (.+)", lower)
        if match:
            location = match.group(1)
            continue
        match = re.fullmatch(r"(?:open|close) (.+)", lower)
        if match:
            checks.append(location == match.group(1))
            continue
        match = re.fullmatch(r"take (.+) from (.+)", lower)
        if match:
            checks.append(location == match.group(2))
            inventory.add(match.group(1))
            continue
        match = re.fullmatch(r"put (.+) (?:in|on|in/on) (.+)", lower)
        if match:
            checks.extend([location == match.group(2), match.group(1) in inventory])
            inventory.discard(match.group(1))
            continue
        match = re.fullmatch(r"(?:clean|heat|cool) (.+) with (.+)", lower)
        if match:
            checks.extend([location == match.group(2), match.group(1) in inventory])
    return sum(checks) / len(checks) if checks else 1.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--task-type", required=True)
    parser.add_argument("--game-index", type=int, required=True)
    parser.add_argument("--max-actions", type=int, default=40)
    parser.add_argument("--json-format", action="store_true", help="Request Ollama JSON-constrained decoding")
    args = parser.parse_args()
    worker_command = [
        "wsl.exe", "-d", "Ubuntu-22.04", "-u", "root", "--",
        "/opt/alfworld-venv/bin/python", WORKER,
        "--task-type", args.task_type, "--game-index", str(args.game_index),
    ]
    process = subprocess.Popen(
        worker_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", bufsize=1,
    )
    started = time.perf_counter()
    trace = []
    try:
        initial = worker_call(process, {"command": "reset"})
        actions, raw, parse_success = generate_plan(
            args.model, initial["objective"], initial["observation"],
            initial["admissible_commands"], args.max_actions, args.json_format,
        )
        state = initial
        for step, action in enumerate(actions, 1):
            admissible = action in state["admissible_commands"]
            next_state = worker_call(process, {"command": "step", "action": action})
            trace.append({
                "step": step,
                "action": action,
                "admissible_before_step": admissible,
                "observation": next_state["observation"],
                "score": next_state["score"],
                "done": next_state["done"],
                "won": next_state["won"],
            })
            state = next_state
            if state["done"]:
                break
        worker_call(process, {"command": "close"})
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    schema = sum(schema_valid(action) for action in actions) / len(actions) if actions else 0.0
    dependency = abstract_dependency_score(actions) if actions else 0.0
    result = {
        "protocol": "single-shot frozen open-loop plan; no replanning or action substitution",
        "model": args.model,
        "task_type": args.task_type,
        "game_index": args.game_index,
        "game": initial["game"],
        "objective": initial["objective"],
        "initial_observation": initial["observation"],
        "initial_admissible_commands": initial["admissible_commands"],
        "raw_model_output": raw,
        "parse_success": parse_success,
        "json_format": args.json_format,
        "planned_actions": actions,
        "executed_trace": trace,
        "planned_action_count": len(actions),
        "executed_action_count": len(trace),
        "admissible_action_rate": sum(item["admissible_before_step"] for item in trace) / len(trace) if trace else 0.0,
        "schema_validity": schema,
        "abstract_dependency_validity": dependency,
        "pre_execution_score": (schema + dependency) / 2,
        "success": bool(state.get("won", False)),
        "final_score": state.get("score", 0),
        "terminated": bool(state.get("done", False)),
        "latency_seconds": round(time.perf_counter() - started, 3),
    }
    model_slug = re.sub(r"[^a-z0-9]+", "_", args.model.lower()).strip("_")
    out = ROOT / "external_validation/results/alfworld_frozen" / model_slug / f"{args.task_type}_{args.game_index:03d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "actions": len(actions), "success": result["success"], "admissible_rate": result["admissible_action_rate"]}))


if __name__ == "__main__":
    main()
