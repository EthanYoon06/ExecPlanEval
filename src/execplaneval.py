from __future__ import annotations

from typing import Any

import networkx as nx

from .symbolic_executor import ExecutionResult, execute_plan


def _build_graph(plan: dict[str, Any]) -> tuple[nx.DiGraph, dict[str, dict[str, Any]]]:
    nodes = {node["id"]: node for node in plan["nodes"]}
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from((edge["source"], edge["target"]) for edge in plan["edges"])
    return graph, nodes


def dependency_validity(task: dict[str, Any], plan: dict[str, Any]) -> float:
    """Score whether produced preconditions are connected by dependency paths."""
    graph, nodes = _build_graph(plan)
    if not nx.is_directed_acyclic_graph(graph):
        return 0.0

    initial = set(task["initial_state"])
    producers: dict[str, set[str]] = {}
    for node_id, node in nodes.items():
        for effect in node.get("effects", []):
            producers.setdefault(effect, set()).add(node_id)

    checks: list[bool] = []
    for consumer_id, node in nodes.items():
        for precondition in node.get("preconditions", []):
            if precondition in initial:
                checks.append(True)
                continue
            valid_producers = producers.get(precondition, set()) - {consumer_id}
            checks.append(
                any(nx.has_path(graph, producer, consumer_id) for producer in valid_producers)
            )
    return sum(checks) / len(checks) if checks else 1.0


def goal_coverage(task: dict[str, Any], execution: ExecutionResult) -> float:
    goal = set(task["goal"])
    if not goal:
        return 1.0
    return len(goal & execution.final_state) / len(goal)


def static_executability(task: dict[str, Any], plan: dict[str, Any]) -> float:
    """Validate plan structure and tool schemas without running the executor."""
    nodes = plan.get("nodes", [])
    if not nodes:
        return 0.0
    catalog = {item["name"]: item for item in task.get("tool_catalog", [])}
    node_ids = [str(node.get("id", "")) for node in nodes]
    unique_ids = set(node_ids)
    valid_edges = all(
        edge.get("source") in unique_ids and edge.get("target") in unique_ids
        for edge in plan.get("edges", [])
    )
    graph = nx.DiGraph()
    graph.add_nodes_from(unique_ids)
    graph.add_edges_from(
        (edge.get("source"), edge.get("target")) for edge in plan.get("edges", [])
    )
    structure_valid = (
        len(unique_ids) == len(node_ids)
        and all(node_ids)
        and valid_edges
        and nx.is_directed_acyclic_graph(graph)
    )
    schema_checks = []
    for node in nodes:
        spec = catalog.get(node.get("tool"))
        schema_checks.append(
            spec is not None
            and set(node.get("preconditions", [])) == set(spec.get("preconditions", []))
            and set(node.get("effects", [])) == set(spec.get("effects", []))
        )
    return (sum(schema_checks) / len(schema_checks)) if structure_valid else 0.0


def score_plan_static(task: dict[str, Any], plan: dict[str, Any]) -> dict[str, float]:
    """Compute the deployable score without executing the candidate plan."""
    dependency = dependency_validity(task, plan)
    executable = static_executability(task, plan)
    pre_execution_score = (dependency + executable) / 2
    return {
        "dependency_validity": dependency,
        "executability": executable,
        "pre_execution_score": pre_execution_score,
    }


def score_plan(task: dict[str, Any], plan: dict[str, Any]) -> dict[str, float | str | None]:
    """Return static diagnostics together with explicitly post-execution fields."""
    static = score_plan_static(task, plan)
    execution = execute_plan(task, plan)
    goal = goal_coverage(task, execution)
    dependency = static["dependency_validity"]
    executable = static["executability"]
    outcome = float(execution.success)
    pre_execution_score = static["pre_execution_score"]
    full_score = (goal + dependency + executable + outcome) / 4
    return {
        "goal_coverage": goal,
        "dependency_validity": dependency,
        "executability": executable,
        "outcome_success": outcome,
        "pre_execution_score": pre_execution_score,
        "execplaneval_score": full_score,
        "failure_reason": execution.failure_reason,
    }
