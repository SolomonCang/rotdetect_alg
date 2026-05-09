from __future__ import annotations

import numpy as np

from .config import SearchConfig
from .data import PeriodPoint, TrendScanCandidate


def scan_delta_p(points: list[PeriodPoint], config: SearchConfig) -> dict:
    periods = np.asarray([point.period for point in points], dtype=float)
    weights = np.asarray([point.weight for point in points], dtype=float)
    delta_grid = np.arange(
        config.delta_p_min,
        config.delta_p_max + 0.5 * config.delta_p_grid,
        config.delta_p_grid,
        dtype=float,
    )
    slope_grid = _build_slope_grid(periods, config)
    p_ref = float(np.average(periods,
                             weights=weights)) if periods.size else 0.0

    scores = np.full((slope_grid.size, delta_grid.size), -np.inf, dtype=float)
    if delta_grid.size == 0 or slope_grid.size == 0:
        return {
            "delta_p_mid": [],
            "slope": [],
            "score_grid": [],
            "score_profile": [],
            "selected_candidates": [],
        }

    for slope_index, slope in enumerate(slope_grid):
        for delta_index, delta_p_mid in enumerate(delta_grid):
            tau = _trend_phase_coordinate(periods, delta_p_mid, slope, p_ref)
            if tau is None:
                continue

            phases = np.mod(tau, 1.0)
            rayleigh = abs(np.sum(
                weights * np.exp(2j * np.pi * phases))) / np.sum(weights)

            counts, _ = np.histogram(phases,
                                     bins=24,
                                     range=(0.0, 1.0),
                                     weights=weights)
            probabilities = counts[counts > 0] / np.sum(counts)
            entropy = -float(
                np.sum(probabilities *
                       np.log(probabilities))) if probabilities.size else 0.0
            entropy_score = 1.0 - entropy / np.log(24)

            scores[slope_index,
                   delta_index] = 0.65 * rayleigh + 0.35 * entropy_score

    candidate_indices = _top_distinct_indices(scores, config.top_k_candidates)
    candidates = [
        TrendScanCandidate(
            delta_p_mid=float(delta_grid[delta_index]),
            slope=float(slope_grid[slope_index]),
            score=float(scores[slope_index, delta_index]),
        ) for slope_index, delta_index in candidate_indices
    ]
    return {
        "delta_p_mid":
        delta_grid.astype(float).tolist(),
        "slope":
        slope_grid.astype(float).tolist(),
        "score_grid":
        scores.astype(float).tolist(),
        "score_profile":
        np.nanmax(scores, axis=0).astype(float).tolist(),
        "selected_candidates": [{
            "delta_p_mid": candidate.delta_p_mid,
            "slope": candidate.slope,
            "score": candidate.score,
        } for candidate in candidates],
    }


def _build_slope_grid(periods: np.ndarray, config: SearchConfig) -> np.ndarray:
    period_span = max(
        float(np.ptp(periods)) if periods.size > 1 else 0.0,
        config.period_max - config.period_min, 1e-6)
    slope_abs_max = max(
        0.5 * config.delta_p_grid / period_span,
        1.25 * (config.delta_p_max - config.delta_p_min) / period_span)
    slope_steps = 31
    return np.linspace(-slope_abs_max, slope_abs_max, slope_steps, dtype=float)


def _trend_phase_coordinate(periods: np.ndarray, delta_p_mid: float,
                            slope: float, p_ref: float) -> np.ndarray | None:
    delta_values = delta_p_mid + slope * (periods - p_ref)
    if np.any(delta_values <= 0):
        return None

    if abs(slope) < 1e-10:
        return (periods - p_ref) / delta_p_mid

    return np.log(delta_values / delta_p_mid) / slope


def _top_distinct_indices(scores: np.ndarray,
                          top_k: int) -> list[tuple[int, int]]:
    flat_order = np.argsort(scores, axis=None)[::-1]
    selected: list[tuple[int, int]] = []

    for flat_index in flat_order:
        slope_index, delta_index = np.unravel_index(int(flat_index),
                                                    scores.shape)
        value = scores[slope_index, delta_index]
        if not np.isfinite(value):
            continue
        if all(
                abs(slope_index - s_idx) >= 2 or abs(delta_index - d_idx) >= 2
                for s_idx, d_idx in selected):
            selected.append((int(slope_index), int(delta_index)))
        if len(selected) >= top_k:
            break
    return selected
