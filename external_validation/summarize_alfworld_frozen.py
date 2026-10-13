from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.statistics import auroc, spearman


BASE = ROOT / "external_validation/results/alfworld_frozen"
REACTIVE = ROOT / "external_validation/results"
OUT = BASE / "summary.json"


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> list[float] | None:
    if n == 0:
        return None
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    margin = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denominator
    return [centre - margin, centre + margin]


def exact_mcnemar_p(left_only: int, right_only: int) -> float | None:
    """Two-sided exact sign/binomial test for discordant matched pairs."""
    discordant = left_only + right_only
    if discordant == 0:
        return None
    smaller = min(left_only, right_only)
    tail = sum(__import__("math").comb(discordant, k) for k in range(smaller + 1)) / (2**discordant)
    return min(1.0, 2 * tail)


def main() -> None:
    rows = []
    for path in sorted(BASE.glob("*/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("protocol", "").startswith("single-shot frozen"):
            rows.append(data)
    by_model = defaultdict(list)
    for row in rows:
        by_model[row["model"]].append(row)
    summaries = {}
    for model, group in sorted(by_model.items()):
        labels = [bool(row["success"]) for row in group]
        scores = [float(row["pre_execution_score"]) for row in group]
        metrics = {
            "spearman_with_success": float(spearman(scores, [float(value) for value in labels])) if len(set(labels)) == 2 else None,
            "auroc": float(auroc(scores, labels)) if len(set(labels)) == 2 else None,
        }
        matched_reactive = []
        paired = []
        for row in group:
            path = REACTIVE / f"alfworld_live_trajectory_{row['task_type']}_{row['game_index']:03d}.json"
            if path.exists():
                reactive_success = bool(json.loads(path.read_text(encoding="utf-8"))["success"])
                matched_reactive.append(reactive_success)
                paired.append((bool(row["success"]), reactive_success))
        frozen_only = sum(frozen and not reactive for frozen, reactive in paired)
        reactive_only = sum(reactive and not frozen for frozen, reactive in paired)
        per_type = {}
        for task_type in sorted({row["task_type"] for row in group}):
            subset = [row for row in group if row["task_type"] == task_type]
            type_successes = sum(bool(row["success"]) for row in subset)
            per_type[task_type] = {
                "n": len(subset),
                "successes": type_successes,
                "success_rate": type_successes / len(subset),
                "mean_pre_execution_score": sum(float(row["pre_execution_score"]) for row in subset) / len(subset),
                "mean_admissible_action_rate": sum(float(row["admissible_action_rate"]) for row in subset) / len(subset),
            }
        summaries[model] = {
            "n": len(group),
            "successes": sum(labels),
            "success_rate": sum(labels) / len(group),
            "success_rate_wilson_95_ci": wilson_interval(sum(labels), len(group)),
            "mean_planned_actions": sum(row["planned_action_count"] for row in group) / len(group),
            "parse_success_rate": sum(bool(row.get("parse_success", True)) for row in group) / len(group),
            "mean_admissible_action_rate": sum(row["admissible_action_rate"] for row in group) / len(group),
            "mean_schema_validity": sum(row["schema_validity"] for row in group) / len(group),
            "mean_dependency_validity": sum(row["abstract_dependency_validity"] for row in group) / len(group),
            "mean_pre_execution_score": sum(scores) / len(group),
            "matched_reactive_n": len(matched_reactive),
            "matched_reactive_successes": sum(matched_reactive),
            "matched_reactive_success_rate": sum(matched_reactive) / len(matched_reactive) if matched_reactive else None,
            "matched_reactive_success_rate_wilson_95_ci": wilson_interval(sum(matched_reactive), len(matched_reactive)),
            "paired_frozen_only_successes": frozen_only,
            "paired_reactive_only_successes": reactive_only,
            "paired_exact_mcnemar_p": exact_mcnemar_p(frozen_only, reactive_only),
            "spearman_pre_score_with_admissible_rate": float(spearman(
                scores, [float(row["admissible_action_rate"]) for row in group]
            )),
            "per_task_type": per_type,
            **metrics,
        }
    result = {
        "protocol": "single-shot frozen open-loop action sequence generated from the initial ALFWorld state; no replanning or action substitution",
        "models": summaries,
        "task_type_counts": dict(Counter(row["task_type"] for row in rows)),
        "limitations": [
            "Initial observations do not reveal hidden object locations, making open-loop execution deliberately difficult.",
            "The abstract dependency checker encodes only common navigation, inventory, and appliance preconditions.",
            "Static-score AUROC is undefined when a model has no successful frozen plans.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
