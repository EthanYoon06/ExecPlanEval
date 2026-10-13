from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "external_validation" / "results"
TASK_TYPES = [
    "pick_and_place_simple",
    "look_at_obj_in_light",
    "pick_clean_then_place_in_recep",
    "pick_heat_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_two_obj_and_place",
]


def task_type(game: str) -> str:
    folder = Path(game).parents[1].name
    return next((name for name in TASK_TYPES if folder.startswith(name + "-")), "unknown")


def main() -> None:
    paths = sorted(RESULTS.glob("alfworld_live_trajectory_*.json"))
    records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    rows = []
    for index, record in enumerate(records):
        trajectory = record["trajectory"]
        rows.append({
            "episode": index,
            "game": record["game"],
            "objective": record["objective"],
            "task_type": task_type(record["game"]),
            "success": record["success"],
            "terminated": record["terminated"],
            "score": record["final_score"],
            "steps": record["steps"],
            "admissible_rate": statistics.mean(step["action_was_admissible"] for step in trajectory) if trajectory else 0,
            "latency_seconds": record["latency_seconds"],
        })
    output = RESULTS / "alfworld_live_summary.csv"
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    stratified = []
    for name in TASK_TYPES:
        candidates = [row for row in rows if row["task_type"] == name]
        if candidates:
            stratified.append(candidates[-1])
    stratified_output = RESULTS / "alfworld_live_stratified.csv"
    with stratified_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(stratified)
    print(json.dumps({
        "episodes": len(rows),
        "success_rate": statistics.mean(row["success"] for row in rows),
        "mean_steps": statistics.mean(row["steps"] for row in rows),
        "mean_admissible_rate": statistics.mean(row["admissible_rate"] for row in rows),
        "stratified_episodes": len(stratified),
        "stratified_success_rate": statistics.mean(row["success"] for row in stratified),
    }))


if __name__ == "__main__":
    main()
