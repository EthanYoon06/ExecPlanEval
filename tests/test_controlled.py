from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.symbolic_executor import execute_plan
from src.execplaneval import score_plan_static


def main() -> None:
    tasks = json.loads((ROOT / "controlled" / "controlled_dataset.json").read_text())
    assert len(tasks) == 50
    assert sum(len(task["candidates"]) for task in tasks) == 350
    for task in tasks:
        for candidate in task["candidates"]:
            result = execute_plan(task, candidate["plan"])
            assert result.success == candidate["expected_valid"], (
                task["task_id"],
                task["topology"],
                candidate["variant"],
                result.failure_reason,
            )
            static = score_plan_static(task, candidate["plan"])
            assert 0.0 <= static["pre_execution_score"] <= 1.0
    print("controlled benchmark tests passed")


if __name__ == "__main__":
    main()
