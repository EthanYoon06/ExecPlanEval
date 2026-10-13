from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "external_validation" / "results"
RUNNER = ROOT / "external_validation" / "run_alfworld_agent.py"
WORKER = "/mnt/c/Users/YKJ/Documents/New project 2/execplaneval/external_validation/alfworld_env_worker.py"
TASK_TYPES = [
    "pick_and_place_simple",
    "look_at_obj_in_light",
    "pick_clean_then_place_in_recep",
    "pick_heat_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_two_obj_and_place",
]
FORMAL_QUOTAS = {
    "pick_and_place_simple": 22,
    "look_at_obj_in_light": 18,
    "pick_clean_then_place_in_recep": 21,
    "pick_heat_then_place_in_recep": 21,
    "pick_cool_then_place_in_recep": 21,
    "pick_two_obj_and_place": 17,
}


def game_count(task_type: str) -> int:
    command = [
        "wsl.exe", "-d", "Ubuntu-22.04", "-u", "root", "--",
        "/opt/alfworld-venv/bin/python", WORKER,
        "--task-type", task_type, "--count-only",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=True)
    return int(json.loads(completed.stdout.strip().splitlines()[-1])["count"])


def valid_result(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("environment") == "ALFWorld TextWorld valid_unseen" and isinstance(data.get("trajectory"), list)
    except (OSError, ValueError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-total", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--max-steps", type=int, default=50)
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS / "alfworld_formal_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["target_total"] != args.target_total or manifest["seed"] != args.seed:
            raise SystemExit("Existing manifest does not match --target-total/--seed; preserve it or choose matching arguments.")
    else:
        if args.target_total != sum(FORMAL_QUOTAS.values()):
            raise SystemExit(f"This formal protocol defines {sum(FORMAL_QUOTAS.values())} tasks.")
        selections: dict[str, list[int]] = {}
        counts: dict[str, int] = {}
        for task_type in TASK_TYPES:
            count = game_count(task_type)
            quota = FORMAL_QUOTAS[task_type]
            if count < quota:
                raise SystemExit(f"Only {count} tasks available for {task_type}, quota is {quota}")
            counts[task_type] = count
            rng = random.Random(f"{args.seed}:{task_type}")
            selections[task_type] = sorted(rng.sample(range(count), quota))
        manifest = {
            "benchmark": "ALFWorld TextWorld valid_unseen",
            "sampling": "stratified random sampling without replacement",
            "seed": args.seed,
            "target_total": args.target_total,
            "quotas": FORMAL_QUOTAS,
            "available_counts": counts,
            "selections": selections,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    status_path = RESULTS / "alfworld_batch_status.jsonl"
    total = args.target_total
    position = 0
    for task_type in TASK_TYPES:
        for game_index in manifest["selections"][task_type]:
            position += 1
            output = RESULTS / f"alfworld_live_trajectory_{task_type}_{game_index:03d}.json"
            if valid_result(output):
                print(f"[{position}/{total}] skip {task_type} index={game_index}", flush=True)
                continue
            started = time.perf_counter()
            command = [
                sys.executable, str(RUNNER), "--model", args.model,
                "--max-steps", str(args.max_steps), "--game-index", str(game_index),
                "--task-type", task_type,
            ]
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            record = {
                "task_type": task_type,
                "game_index": game_index,
                "returncode": completed.returncode,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "stdout_tail": completed.stdout.splitlines()[-3:],
                "stderr_tail": completed.stderr.splitlines()[-10:],
                "result_valid": valid_result(output),
            }
            with status_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            state = "done" if record["result_valid"] else "ERROR"
            detail = record["stdout_tail"][-1] if record["stdout_tail"] else "no output"
            print(f"[{position}/{total}] {state} {task_type} index={game_index} {detail}", flush=True)
            if not record["result_valid"]:
                print("stderr: " + " | ".join(record["stderr_tail"]), flush=True)


if __name__ == "__main__":
    main()
