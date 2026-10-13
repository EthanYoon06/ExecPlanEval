from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluate import structural_scores
from src.execplaneval import score_plan, score_plan_static
from src.symbolic_executor import execute_plan


def main() -> None:
    tasks = json.loads((ROOT / "pilot" / "pilot_dataset.json").read_text())
    assert len(tasks) == 10
    assert sum(len(task["candidates"]) for task in tasks) == 60

    for task in tasks:
        for candidate in task["candidates"]:
            result = execute_plan(task, candidate["plan"])
            assert result.success == candidate["expected_valid"], (
                task["task_id"],
                candidate["variant"],
                result.failure_reason,
            )
            proposed = score_plan(task, candidate["plan"])
            static = score_plan_static(task, candidate["plan"])
            assert proposed["pre_execution_score"] == static["pre_execution_score"]
            if candidate["expected_valid"]:
                assert proposed["execplaneval_score"] == 1.0
            else:
                assert proposed["execplaneval_score"] < 1.0

        alternative = next(
            item for item in task["candidates"] if item["variant"] == "valid_equivalent_tool"
        )
        score = structural_scores(task["reference_plan"], alternative["plan"])
        assert score["node_f1"] < 1.0
        assert execute_plan(task, alternative["plan"]).success

    print("pilot tests passed")


if __name__ == "__main__":
    main()
