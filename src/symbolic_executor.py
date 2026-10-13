from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx


@dataclass
class ExecutionResult:
    success: bool
    final_state: set[str]
    executed_nodes: list[str]
    failure_reason: str | None = None


def execute_plan(task: dict[str, Any], plan: dict[str, Any]) -> ExecutionResult:
    """Execute a plan in a deterministic STRIPS-like symbolic environment."""
    graph = nx.DiGraph()
    nodes = {node["id"]: node for node in plan["nodes"]}
    graph.add_nodes_from(nodes)
    graph.add_edges_from((edge["source"], edge["target"]) for edge in plan["edges"])

    if not nx.is_directed_acyclic_graph(graph):
        return ExecutionResult(False, set(task["initial_state"]), [], "cyclic_plan")

    state = set(task["initial_state"])
    executed: list[str] = []
    remaining = set(nodes)
    while remaining:
        enabled = [
            node_id
            for node_id in remaining
            if set(graph.predecessors(node_id)).issubset(executed)
            and set(nodes[node_id].get("preconditions", [])).issubset(state)
        ]
        if not enabled:
            missing = sorted(
                {
                    precondition
                    for node_id in remaining
                    for precondition in nodes[node_id].get("preconditions", [])
                    if precondition not in state
                }
            )
            return ExecutionResult(
                False,
                state,
                executed,
                f"no_enabled_action:{','.join(missing)}",
            )
        node_id = sorted(enabled)[0]
        node = nodes[node_id]
        state.difference_update(node.get("delete_effects", []))
        state.update(node.get("effects", []))
        executed.append(node_id)
        remaining.remove(node_id)

    goal = set(task["goal"])
    success = goal.issubset(state)
    return ExecutionResult(
        success,
        state,
        executed,
        None if success else f"goal_not_reached:{','.join(sorted(goal - state))}",
    )
