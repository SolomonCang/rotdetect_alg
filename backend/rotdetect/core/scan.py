from __future__ import annotations

import numpy as np

from .config import SearchConfig
from .data import PeriodPoint


def scan_delta_p(points: list[PeriodPoint], config: SearchConfig) -> dict:
    periods = np.asarray([point.period for point in points], dtype=float)
    weights = np.asarray([point.weight for point in points], dtype=float)
    delta_grid = np.arange(
        config.delta_p_min,
        config.delta_p_max + 0.5 * config.delta_p_grid,
        config.delta_p_grid,
        dtype=float,
    )

    scores = np.zeros_like(delta_grid)
    if delta_grid.size == 0:
        return {"delta_p": [], "score": [], "selected_candidates": []}

    for idx, delta_p in enumerate(delta_grid):
        phases = np.mod(periods / delta_p, 1.0)
        rayleigh = abs(np.sum(weights * np.exp(2j * np.pi * phases))) / np.sum(weights)

        counts, _ = np.histogram(phases, bins=24, range=(0.0, 1.0), weights=weights)
        probabilities = counts[counts > 0] / np.sum(counts)
        entropy = -float(np.sum(probabilities * np.log(probabilities))) if probabilities.size else 0.0
        entropy_score = 1.0 - entropy / np.log(24)

        scores[idx] = 0.65 * rayleigh + 0.35 * entropy_score

    candidate_indices = _top_distinct_indices(delta_grid, scores, config.top_k_candidates)
    candidates = [float(delta_grid[index]) for index in candidate_indices]
    return {
        "delta_p": delta_grid.astype(float).tolist(),
        "score": scores.astype(float).tolist(),
        "selected_candidates": candidates,
    }


def _top_distinct_indices(delta_grid: np.ndarray, scores: np.ndarray, top_k: int) -> list[int]:
    order = np.argsort(scores)[::-1]
    selected: list[int] = []
    min_separation = max(2, int(round(0.001 / (delta_grid[1] - delta_grid[0])))) if len(delta_grid) > 1 else 1

    for index in order:
        if all(abs(int(index) - existing) >= min_separation for existing in selected):
            selected.append(int(index))
        if len(selected) >= top_k:
            break
    return selected
