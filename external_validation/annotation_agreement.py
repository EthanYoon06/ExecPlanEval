from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def kappa(left: list[str], right: list[str]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Two non-empty, equally sized label lists are required")
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    labels = set(left) | set(right)
    lc, rc = Counter(left), Counter(right)
    expected = sum((lc[label] / len(left)) * (rc[label] / len(right)) for label in labels)
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("annotator_a", type=Path)
    parser.add_argument("annotator_b", type=Path)
    args = parser.parse_args()
    a = {row["annotation_id"]: row for row in csv.DictReader(args.annotator_a.open(encoding="utf-8-sig"))}
    b = {row["annotation_id"]: row for row in csv.DictReader(args.annotator_b.open(encoding="utf-8-sig"))}
    shared = sorted(set(a) & set(b))
    for field in ["overall_validity", "tool_selection", "dependency_validity", "executability", "goal_completion"]:
        pairs = [(a[key].get(field, "").strip(), b[key].get(field, "").strip()) for key in shared]
        pairs = [(left, right) for left, right in pairs if left and right]
        print(field, "n=", len(pairs), "kappa=", round(kappa([x[0] for x in pairs], [x[1] for x in pairs]), 4) if pairs else "NA")


if __name__ == "__main__":
    main()
