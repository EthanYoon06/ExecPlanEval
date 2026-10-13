from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import alfworld
from alfworld.info import ALFRED_PDDL_PATH, ALFRED_TWL2_PATH


ARCHIVES = [
    Path("/mnt/c/Users/YKJ/Downloads/json_2.1.1_json.zip"),
    Path("/mnt/c/Users/YKJ/Downloads/json_2.1.1_pddl.zip"),
    Path("/mnt/c/Users/YKJ/Downloads/json_2.1.2_tw-pddl.zip"),
]
DESTINATION = Path("/opt/alfworld-data")


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    if not (DESTINATION / "json_2.1.1").exists():
        for archive in ARCHIVES:
            with zipfile.ZipFile(archive) as zipped:
                corrupt = zipped.testzip()
                if corrupt:
                    raise RuntimeError(f"CRC failure in {archive}: {corrupt}")
                print(f"Extracting {archive.name}: {len(zipped.namelist())} entries")
                zipped.extractall(DESTINATION)
    else:
        print("Data directories already extracted; skipping archives")

    logic_dir = DESTINATION / "logic"
    logic_dir.mkdir(exist_ok=True)
    shutil.copy2(ALFRED_PDDL_PATH, logic_dir / "alfred.pddl")
    shutil.copy2(ALFRED_TWL2_PATH, logic_dir / "alfred.twl2")
    print(f"ALFWorld text data ready at {DESTINATION}")


if __name__ == "__main__":
    main()
