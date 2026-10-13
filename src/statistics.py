from __future__ import annotations

from math import sqrt
from random import Random
from typing import Callable


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        rank = (index + 1 + end) / 2
        for position in range(index, end):
            ranks[order[position]] = rank
        index = end
    return ranks


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or not x:
        raise ValueError("x and y must be non-empty and have equal length")
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    denominator = sqrt(
        sum((a - mean_x) ** 2 for a in x) * sum((b - mean_y) ** 2 for b in y)
    )
    return numerator / denominator if denominator else 0.0


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(average_ranks(x), average_ranks(y))


def auroc(scores: list[float], labels: list[bool]) -> float:
    positives = [score for score, label in zip(scores, labels) if label]
    negatives = [score for score, label in zip(scores, labels) if not label]
    if not positives or not negatives:
        raise ValueError("AUROC requires positive and negative labels")
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            wins += positive > negative
            wins += 0.5 * (positive == negative)
    return wins / (len(positives) * len(negatives))


def bootstrap_interval(
    scores: list[float],
    labels: list[bool],
    statistic: Callable[[list[float], list[bool]], float],
    samples: int = 2000,
    seed: int = 20260826,
) -> tuple[float, float]:
    rng = Random(seed)
    estimates: list[float] = []
    population = list(range(len(scores)))
    while len(estimates) < samples:
        indices = [rng.choice(population) for _ in population]
        sampled_scores = [scores[index] for index in indices]
        sampled_labels = [labels[index] for index in indices]
        if all(sampled_labels) or not any(sampled_labels):
            continue
        estimates.append(statistic(sampled_scores, sampled_labels))
    estimates.sort()
    lower = estimates[int(0.025 * samples)]
    upper = estimates[min(int(0.975 * samples), samples - 1)]
    return lower, upper


def cluster_bootstrap_interval(
    scores: list[float],
    labels: list[bool],
    clusters: list[str],
    statistic: Callable[[list[float], list[bool]], float],
    samples: int = 2000,
    seed: int = 20260826,
) -> tuple[float, float]:
    """Bootstrap whole clusters so dependent observations stay together."""
    if not (len(scores) == len(labels) == len(clusters)):
        raise ValueError("scores, labels, and clusters must have equal length")
    members: dict[str, list[int]] = {}
    for index, cluster in enumerate(clusters):
        members.setdefault(cluster, []).append(index)
    cluster_names = sorted(members)
    rng = Random(seed)
    estimates: list[float] = []
    while len(estimates) < samples:
        sampled_clusters = [rng.choice(cluster_names) for _ in cluster_names]
        indices = [index for cluster in sampled_clusters for index in members[cluster]]
        sampled_scores = [scores[index] for index in indices]
        sampled_labels = [labels[index] for index in indices]
        if all(sampled_labels) or not any(sampled_labels):
            continue
        estimates.append(statistic(sampled_scores, sampled_labels))
    estimates.sort()
    lower = estimates[int(0.025 * samples)]
    upper = estimates[min(int(0.975 * samples), samples - 1)]
    return lower, upper
