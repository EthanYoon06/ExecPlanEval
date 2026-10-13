from __future__ import annotations

import json
from pathlib import Path

import textworld
from textworld import EnvInfos


DATA = Path("/opt/alfworld-data/json_2.1.1")
OUTPUT = Path("/mnt/c/Users/YKJ/Documents/New project 2/execplaneval/external_validation/results/alfworld_smoke.json")


def main() -> None:
    game = next((DATA / "valid_train").glob("**/game.tw-pddl"))
    requested = EnvInfos(admissible_commands=True, description=True, objective=True, score=True, won=True, lost=True)
    env = textworld.start(str(game), request_infos=requested)
    try:
        state = env.reset()
        next_state, score, done = env.step("look")
        record = {
            "game": str(game),
            "objective": state.objective,
            "initial_observation": state.feedback,
            "admissible_commands": list(state.admissible_commands),
            "action": "look",
            "observation": next_state.feedback,
            "score": score,
            "done": done,
            "won": next_state.won,
            "lost": next_state.lost,
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"game": record["game"], "commands": len(record["admissible_commands"]), "score": score, "done": done}))
    finally:
        env.close()


if __name__ == "__main__":
    main()
