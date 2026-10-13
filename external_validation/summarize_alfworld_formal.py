from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "external_validation" / "results"


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return centre - margin, centre + margin


def aggregate(rows: list[dict], name: str) -> dict:
    total = len(rows)
    successes = sum(row["success"] for row in rows)
    low, high = wilson(successes, total)
    return {
        "task_type": name,
        "episodes": total,
        "successes": successes,
        "success_rate": successes / total,
        "wilson_95_low": low,
        "wilson_95_high": high,
        "mean_steps": statistics.mean(row["steps"] for row in rows),
        "median_steps": statistics.median(row["steps"] for row in rows),
        "terminated_rate": statistics.mean(row["terminated"] for row in rows),
        "mean_admissible_rate": statistics.mean(row["admissible_rate"] for row in rows),
        "mean_latency_seconds": statistics.mean(row["latency_seconds"] for row in rows),
    }


def main() -> None:
    manifest = json.loads((RESULTS / "alfworld_formal_manifest.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    missing: list[str] = []
    for task_type, indices in manifest["selections"].items():
        for game_index in indices:
            path = RESULTS / f"alfworld_live_trajectory_{task_type}_{game_index:03d}.json"
            if not path.exists():
                missing.append(str(path))
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            trajectory = record["trajectory"]
            rows.append({
                "task_type": task_type,
                "game_index": game_index,
                "game": record["game"],
                "objective": record["objective"],
                "success": bool(record["success"]),
                "terminated": bool(record["terminated"]),
                "score": record["final_score"],
                "steps": record["steps"],
                "admissible_rate": statistics.mean(step["action_was_admissible"] for step in trajectory) if trajectory else 0,
                "latency_seconds": record["latency_seconds"],
                "trajectory_file": path.name,
            })
    if missing or len(rows) != manifest["target_total"]:
        raise SystemExit(f"Formal batch incomplete: rows={len(rows)}, missing={missing}")

    episodes_path = RESULTS / "alfworld_formal_episodes.csv"
    with episodes_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    task_types = list(manifest["selections"])
    grouped = [aggregate([row for row in rows if row["task_type"] == name], name) for name in task_types]
    overall = aggregate(rows, "overall")
    by_type_path = RESULTS / "alfworld_formal_by_task_type.csv"
    with by_type_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(overall))
        writer.writeheader()
        writer.writerows(grouped + [overall])

    summary = {
        "protocol": manifest,
        "model": "qwen3:8b",
        "maximum_steps": 50,
        "overall": overall,
        "by_task_type": grouped,
        "integrity": {
            "expected_episodes": manifest["target_total"],
            "observed_episodes": len(rows),
            "unique_games": len({row["game"] for row in rows}),
            "all_actions_admissible": all(row["admissible_rate"] == 1 for row in rows),
            "missing_files": missing,
        },
    }
    (RESULTS / "alfworld_formal_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
