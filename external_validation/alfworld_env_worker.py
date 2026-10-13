from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import textworld
from textworld import EnvInfos
from alfworld.agents.environment.alfred_tw_env import AlfredDemangler


DATA = Path("/opt/alfworld-data/json_2.1.1")


def state_payload(state, objective: str, score=0, done=False) -> dict:
    return {
        "objective": objective,
        "observation": state.feedback,
        "admissible_commands": list(state.admissible_commands),
        "score": score,
        "done": done,
        "won": state.won,
        "lost": state.lost,
    }


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-index", type=int, default=0)
    parser.add_argument("--task-type")
    parser.add_argument("--count-only", action="store_true")
    args = parser.parse_args()
    games = sorted((DATA / "valid_unseen").glob("**/game.tw-pddl"))
    if args.task_type:
        games = [game for game in games if game.parents[1].name.startswith(args.task_type + "-")]
    if args.count_only:
        emit({"count": len(games)})
        return
    game = games[args.game_index]
    infos = EnvInfos(admissible_commands=True, description=True, objective=True, score=True, won=True, lost=True)
    env = textworld.start(str(game), request_infos=infos, wrappers=[AlfredDemangler])
    objective = ""
    try:
        for line in sys.stdin:
            request = json.loads(line)
            command = request.get("command")
            if command == "reset":
                state = env.reset()
                match = re.search(r"Your task is to:\s*(.+?)(?:\n|$)", state.feedback, flags=re.I)
                objective = match.group(1).strip() if match else str(state.objective or "")
                emit({"game": str(game), **state_payload(state, objective)})
            elif command == "step":
                state, score, done = env.step(str(request.get("action", "")))
                emit(state_payload(state, objective, score, done))
            elif command == "close":
                emit({"closed": True})
                break
            else:
                emit({"error": f"unknown command: {command}"})
    finally:
        env.close()


if __name__ == "__main__":
    main()
