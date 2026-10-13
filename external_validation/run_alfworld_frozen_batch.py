from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "external_validation/run_alfworld_frozen.py"
MANIFEST = ROOT / "external_validation/results/alfworld_formal_manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--per-type", type=int, default=5)
    parser.add_argument("--max-actions", type=int, default=40)
    parser.add_argument("--json-format", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    model_slug = re.sub(r"[^a-z0-9]+", "_", args.model.lower()).strip("_")
    selected = [
        (task_type, game_index)
        for task_type, indices in manifest["selections"].items()
        for game_index in indices[: args.per_type]
    ]
    for position, (task_type, game_index) in enumerate(selected, 1):
        output = ROOT / "external_validation/results/alfworld_frozen" / model_slug / f"{task_type}_{game_index:03d}.json"
        if output.exists():
            print(f"[{position}/{len(selected)}] skip {task_type}:{game_index}", flush=True)
            continue
        command = [
            sys.executable, str(RUNNER), "--model", args.model, "--task-type", task_type,
            "--game-index", str(game_index), "--max-actions", str(args.max_actions),
        ]
        if args.json_format:
            command.append("--json-format")
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        print(f"[{position}/{len(selected)}] rc={completed.returncode} {task_type}:{game_index} {completed.stdout.strip()[-500:]}", flush=True)
        if completed.returncode:
            print(completed.stderr[-1500:], flush=True)


if __name__ == "__main__":
    main()
