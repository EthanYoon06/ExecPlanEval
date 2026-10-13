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
        raise RuntimeError("ALFWorld worker terminated unexpectedly")
    return json.loads(line)


def parse_action(text: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I | re.S)
    try:
        return str(json.loads(cleaned)["action"]).strip()
    except Exception:
        match = re.search(r'"action"\s*:\s*"([^"]+)"', cleaned)
        return match.group(1).strip() if match else cleaned.splitlines()[0].strip()


def choose_action(model: str, objective: str, observation: str, commands: list[str], history: list[dict]) -> tuple[str, str]:
    recent = [{"action": item["action"], "observation": item["observation"]} for item in history[-5:]]
    blocked = {item["action"] for item in history if item.get("before_observation") == observation and not item.get("won")}
    candidates = [command for command in commands if command not in blocked] or commands
    prompt = f"""You control a text environment. Select exactly one command from the admissible command list.
Goal: {objective}
Current observation: {observation}
Recent trajectory: {json.dumps(recent, ensure_ascii=False)}
Actions already tried without progress in this exact state: {json.dumps(sorted(blocked), ensure_ascii=False)}
Admissible commands: {json.dumps(candidates, ensure_ascii=False)}
Explore new locations and objects. Do not repeat a failed state-action pair.
Return JSON only: {{"action":"exact command"}}
/no_think"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Choose one exact admissible action and output strict JSON."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 100},
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = json.loads(response.read().decode())["message"]["content"]
    action = parse_action(raw)
    if action not in candidates:
        action = candidates[0]
    return action, raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--game-index", type=int, default=0)
    parser.add_argument("--task-type")
    args = parser.parse_args()
    worker_command = ["wsl.exe", "-d", "Ubuntu-22.04", "-u", "root", "--", "/opt/alfworld-venv/bin/python", WORKER, "--game-index", str(args.game_index)]
    if args.task_type:
        worker_command.extend(["--task-type", args.task_type])
    process = subprocess.Popen(
        worker_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    trajectory: list[dict] = []
    started = time.perf_counter()
    try:
        state = worker_call(process, {"command": "reset"})
        initial = state.copy()
        for step in range(1, args.max_steps + 1):
            action, raw = choose_action(args.model, state["objective"], state["observation"], state["admissible_commands"], trajectory)
            admissible = action in state["admissible_commands"]
            next_state = worker_call(process, {"command": "step", "action": action})
            trajectory.append({
                "step": step,
                "before_observation": state["observation"],
                "action": action,
                "action_was_admissible": admissible,
                "raw_model_output": raw,
                "observation": next_state["observation"],
                "score": next_state["score"],
                "done": next_state["done"],
                "won": next_state["won"],
            })
            print(step, action, "admissible=" + str(admissible), "score=" + str(next_state["score"]), "done=" + str(next_state["done"]))
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
    dag = {
        "nodes": [{"id": str(item["step"]), "label": item["action"]} for item in trajectory],
        "edges": [{"source": str(i), "target": str(i + 1)} for i in range(1, len(trajectory))],
    }
    result = {
        "model": args.model,
        "environment": "ALFWorld TextWorld valid_unseen",
        "game": initial["game"],
        "objective": initial["objective"],
        "initial_observation": initial["observation"],
        "trajectory": trajectory,
        "trajectory_dag": dag,
        "steps": len(trajectory),
        "final_score": state["score"],
        "success": bool(state["won"]),
        "terminated": bool(state["done"]),
        "latency_seconds": round(time.perf_counter() - started, 3),
    }
    label = args.task_type or "mixed"
    output = ROOT / "external_validation" / "results" / f"alfworld_live_trajectory_{label}_{args.game_index:03d}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"success": result["success"], "steps": result["steps"], "score": result["final_score"]}))


if __name__ == "__main__":
    main()
