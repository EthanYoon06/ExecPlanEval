from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.statistics import auroc, spearman


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "external_validation/results"
HUMAN = RESULTS / "human_annotations"
RAW_ADJUDICATION = HUMAN / "raw/adjudication_completed.csv"
ANNOTATOR_A = HUMAN / "annotator_a.jsonl"
ANNOTATOR_B = HUMAN / "annotator_b.jsonl"
SCORES = RESULTS / "external_scores.csv"
OUT_LABELS = HUMAN / "adjudicated_labels.json"
OUT_ANALYSIS = HUMAN / "adjudicated_analysis.json"

FIELDS = [
    "overall_validity",
    "tool_selection",
    "dependency_validity",
    "executability",
    "goal_completion",
    "alternative_valid_plan",
    "primary_error_type",
]

ALLOWED = {
    "overall_validity": {"Valid", "Partially valid", "Invalid"},
    "tool_selection": {"Correct", "Partially correct", "Incorrect"},
    "dependency_validity": {"Correct", "Incorrect dependencies", "Missing dependencies"},
    "executability": {"Executable", "Uncertain", "Not executable"},
    "goal_completion": {"Complete", "Partial", "Not complete"},
    "alternative_valid_plan": {"Yes", "No", "Uncertain"},
    "primary_error_type": {
        "None", "Wrong tool", "Missing node", "Extra node", "Wrong edge",
        "Missing edge", "Wrong order", "Hallucination", "Other",
    },
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    return values[int(probability * (len(values) - 1))]


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        rank = (start + 1 + stop) / 2
        for position in range(start, stop):
            ranks[order[position]] = rank
        start = stop
    return ranks


def ordinal_rho(rows: list[dict], metric: str) -> float | None:
    x = [float(row[metric]) for row in rows]
    y = [float(row["ordinal_label"]) for row in rows]
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return float(spearman(x, y))


def binary_auc(rows: list[dict], metric: str) -> float | None:
    labels = [bool(row["binary_label"]) for row in rows]
    if len(set(labels)) < 2:
        return None
    return float(auroc([float(row[metric]) for row in rows], labels))


def centered_rho(rows: list[dict], metric: str) -> float | None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["subset_key"]].append(row)
    x_residuals, y_residuals = [], []
    for group in grouped.values():
        x = rankdata([float(row[metric]) for row in group])
        y = rankdata([float(row["ordinal_label"]) for row in group])
        x_mean, y_mean = sum(x) / len(x), sum(y) / len(y)
        x_residuals.extend(value - x_mean for value in x)
        y_residuals.extend(value - y_mean for value in y)
    if len(set(x_residuals)) < 2 or len(set(y_residuals)) < 2:
        return None
    return float(spearman(x_residuals, y_residuals))


def bootstrap(rows: list[dict], metric: str, statistic, seed: int = 20260827) -> list[float | None]:
    rng = random.Random(seed)
    values = []
    for _ in range(2000):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        value = statistic(sample, metric)
        if value is not None and math.isfinite(value):
            values.append(value)
    return [percentile(values, 0.025), percentile(values, 0.975)]


def main() -> None:
    a_rows = read_jsonl(ANNOTATOR_A)
    b_rows = read_jsonl(ANNOTATOR_B)
    a_by_id = {row["annotation_id"]: row for row in a_rows}
    b_by_id = {row["annotation_id"]: row for row in b_rows}
    if set(a_by_id) != set(b_by_id) or len(a_by_id) != 120:
        raise ValueError("The two annotation passes do not contain the same 120 IDs.")

    disagreement_ids = {
        annotation_id
        for annotation_id in a_by_id
        if any(a_by_id[annotation_id][field] != b_by_id[annotation_id][field] for field in FIELDS)
    }
    with RAW_ADJUDICATION.open(encoding="utf-8-sig", newline="") as handle:
        adjudication_rows = list(csv.DictReader(handle))
    adjudication_by_id = {row["annotation_id"]: row for row in adjudication_rows}
    if len(adjudication_rows) != len(adjudication_by_id):
        raise ValueError("Duplicate annotation IDs in adjudication file.")
    if set(adjudication_by_id) != disagreement_ids:
        missing = sorted(disagreement_ids - set(adjudication_by_id))
        extra = sorted(set(adjudication_by_id) - disagreement_ids)
        raise ValueError(f"Adjudication ID mismatch; missing={missing}, extra={extra}")

    for annotation_id, row in adjudication_by_id.items():
        for field in FIELDS:
            value = row[f"final_{field}"]
            if value not in ALLOWED[field]:
                raise ValueError(f"Invalid {field} value for {annotation_id}: {value!r}")
        for field in ["adjudication_rationale", "adjudicator_id", "completed_at"]:
            if not row.get(field, "").strip():
                raise ValueError(f"Missing {field} for {annotation_id}")

    final_rows = []
    for annotation_id in sorted(a_by_id):
        source = a_by_id[annotation_id]
        final = {
            key: source[key]
            for key in ["annotation_id", "task_id", "benchmark", "subset", "instruction", "candidate_plan"]
        }
        if annotation_id in adjudication_by_id:
            adjudication = adjudication_by_id[annotation_id]
            for field in FIELDS:
                final[field] = adjudication[f"final_{field}"]
            final["consensus_source"] = "adjudication"
            final["rationale"] = adjudication["adjudication_rationale"]
            final["adjudicator_id"] = adjudication["adjudicator_id"]
            final["completed_at"] = adjudication["completed_at"]
        else:
            for field in FIELDS:
                if a_by_id[annotation_id][field] != b_by_id[annotation_id][field]:
                    raise AssertionError(f"Unexpected unresolved field for {annotation_id}: {field}")
                final[field] = a_by_id[annotation_id][field]
            final["consensus_source"] = "rater_agreement"
            final["rationale"] = a_by_id[annotation_id]["rationale"]
            final["adjudicator_id"] = ""
            final["completed_at"] = ""
        for field in FIELDS:
            if final[field] not in ALLOWED[field]:
                raise ValueError(f"Invalid final {field} value for {annotation_id}: {final[field]!r}")
        final_rows.append(final)

    score_by_task = {
        row["task_id"]: row
        for row in csv.DictReader(SCORES.open(encoding="utf-8-sig", newline=""))
        if int(row["run"]) == 1
    }
    label_value = {"Invalid": 0, "Partially valid": 1, "Valid": 2}
    analysis_rows = []
    for label in final_rows:
        score = dict(score_by_task[label["task_id"]])
        score["overall_validity"] = label["overall_validity"]
        score["ordinal_label"] = label_value[label["overall_validity"]]
        score["binary_label"] = int(label["overall_validity"] == "Valid")
        score["subset_key"] = f'{score["benchmark"]}:{score["subset"]}'
        score["graph_overlap"] = (float(score["node_f1"]) + float(score["edge_f1"])) / 2
        analysis_rows.append(score)

    metrics = ["node_f1", "edge_f1", "fuzzy_node_f1", "graph_overlap", "catalog_validity", "static_external_score"]
    metric_results = {}
    for metric in metrics:
        metric_results[metric] = {
            "spearman_rho": ordinal_rho(analysis_rows, metric),
            "spearman_task_bootstrap_95ci": bootstrap(analysis_rows, metric, ordinal_rho),
            "auroc_valid_vs_other": binary_auc(analysis_rows, metric),
            "auroc_task_bootstrap_95ci": bootstrap(analysis_rows, metric, binary_auc),
            "within_subset_centered_rho": centered_rho(analysis_rows, metric),
        }

    result = {
        "generated_at": "2026-08-27",
        "sample_size": len(final_rows),
        "consensus_construction": {
            "rater_agreement": len(final_rows) - len(adjudication_rows),
            "adjudicated": len(adjudication_rows),
            "unresolved": 0,
        },
        "adjudication_provenance": {
            "adjudicator_ids_in_file": sorted({row["adjudicator_id"] for row in adjudication_rows}),
            "completed_at_values": sorted({row["completed_at"] for row in adjudication_rows}),
            "identity_independence_verified_by_files": False,
        },
        "final_label_counts": {
            field: dict(sorted(Counter(row[field] for row in final_rows).items()))
            for field in FIELDS
        },
        "overall_validity_by_subset": {
            key: dict(sorted(Counter(row["overall_validity"] for row in final_rows if f'{row["benchmark"]}:{row["subset"]}' == key).items()))
            for key in sorted({f'{row["benchmark"]}:{row["subset"]}' for row in final_rows})
        },
        "metric_associations": metric_results,
        "interpretation_guardrail": (
            "The supplied file resolves all categorical disagreements, but file contents alone do not verify "
            "the adjudicator's identity or independence. Associations are therefore reported as adjudicated-label "
            "analyses, not as independently certified human ground truth."
        ),
    }
    OUT_LABELS.write_text(json.dumps({"annotations": final_rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_ANALYSIS.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
