from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "pilot" / "pilot_dataset.json"


TASK_TEMPLATES = [
    ("travel", "Prepare a trip summary", ["profile_ready"], ["trip_ready"]),
    ("weather", "Create a weather-aware reminder", ["location_known"], ["reminder_ready"]),
    ("shopping", "Prepare a purchase recommendation", ["request_known"], ["purchase_ready"]),
    ("media", "Create an accessible media summary", ["media_available"], ["media_summary_ready"]),
    ("document", "Translate and archive a document", ["document_available"], ["document_archived"]),
    ("meeting", "Schedule and notify meeting participants", ["participants_known"], ["meeting_notified"]),
    ("finance", "Prepare a verified expense report", ["receipts_available"], ["expense_report_ready"]),
    ("support", "Resolve and document a support ticket", ["ticket_open"], ["ticket_resolved"]),
    ("research", "Collect evidence and prepare a research note", ["question_known"], ["research_note_ready"]),
    ("security", "Investigate and report a security alert", ["alert_open"], ["security_report_ready"]),
]


def node(
    node_id: str,
    tool: str,
    preconditions: list[str],
    effects: list[str],
) -> dict[str, Any]:
    return {
        "id": node_id,
        "tool": tool,
        "preconditions": preconditions,
        "effects": effects,
    }


def build_reference(
    domain: str, initial: list[str], goal: list[str]
) -> dict[str, Any]:
    fact_a = f"{domain}_evidence_a"
    fact_b = f"{domain}_evidence_b"
    combined = f"{domain}_combined"
    return {
        "nodes": [
            node("n1", f"collect_{domain}_a", initial, [fact_a]),
            node("n2", f"collect_{domain}_b", initial, [fact_b]),
            node("n3", f"combine_{domain}", [fact_a, fact_b], [combined]),
            node("n4", f"finalize_{domain}", [combined], goal),
        ],
        "edges": [
            {"source": "n1", "target": "n3"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n4"},
        ],
    }


def variants(domain: str, reference: dict[str, Any]) -> list[dict[str, Any]]:
    exact = copy.deepcopy(reference)

    serialized = copy.deepcopy(reference)
    serialized["edges"].append({"source": "n1", "target": "n2"})

    alternative = copy.deepcopy(reference)
    alternative["nodes"][0]["tool"] = f"retrieve_{domain}_primary"

    redundant = copy.deepcopy(reference)
    redundant["nodes"].append(
        node("n5", f"audit_{domain}", [f"{domain}_combined"], [f"{domain}_audited"])
    )
    redundant["edges"].append({"source": "n3", "target": "n5"})

    missing = copy.deepcopy(reference)
    missing["nodes"] = [item for item in missing["nodes"] if item["id"] != "n2"]
    missing["edges"] = [
        edge
        for edge in missing["edges"]
        if edge["source"] != "n2" and edge["target"] != "n2"
    ]

    reversed_dependency = copy.deepcopy(reference)
    reversed_dependency["edges"] = [
        {"source": "n3", "target": "n1"},
        {"source": "n2", "target": "n3"},
        {"source": "n3", "target": "n4"},
    ]

    return [
        {"variant": "reference", "expected_valid": True, "plan": exact},
        {"variant": "valid_serialization", "expected_valid": True, "plan": serialized},
        {"variant": "valid_equivalent_tool", "expected_valid": True, "plan": alternative},
        {"variant": "valid_redundant_audit", "expected_valid": True, "plan": redundant},
        {"variant": "invalid_missing_branch", "expected_valid": False, "plan": missing},
        {
            "variant": "invalid_reversed_dependency",
            "expected_valid": False,
            "plan": reversed_dependency,
        },
    ]


def main() -> None:
    tasks = []
    for index, (domain, instruction, initial, goal) in enumerate(TASK_TEMPLATES, 1):
        reference = build_reference(domain, initial, goal)
        tasks.append(
            {
                "task_id": f"pilot_{index:02d}",
                "domain": domain,
                "instruction": instruction,
                "initial_state": initial,
                "goal": goal,
                "reference_plan": reference,
                "tool_catalog": [
                    {
                        "name": item["tool"],
                        "preconditions": item["preconditions"],
                        "effects": item["effects"],
                    }
                    for item in reference["nodes"]
                ]
                + [
                    {
                        "name": f"retrieve_{domain}_primary",
                        "preconditions": reference["nodes"][0]["preconditions"],
                        "effects": reference["nodes"][0]["effects"],
                    },
                    {
                        "name": f"audit_{domain}",
                        "preconditions": [f"{domain}_combined"],
                        "effects": [f"{domain}_audited"],
                    },
                ],
                "candidates": variants(domain, reference),
            }
        )
    OUTPUT.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    print(f"Wrote {len(tasks)} tasks and {sum(len(t['candidates']) for t in tasks)} candidates")
    print(OUTPUT)


if __name__ == "__main__":
    main()
