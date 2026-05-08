from __future__ import annotations

import numpy as np

from .config import SearchConfig
from .data import PeriodPoint, PeriodSpacingSequence


def fit_sequence_for_delta_p(
    points: list[PeriodPoint],
    delta_p: float,
    config: SearchConfig,
) -> PeriodSpacingSequence | None:
    periods = np.asarray([point.period for point in points], dtype=float)
    weights = np.asarray([point.weight for point in points], dtype=float)
    tolerance = max(0.001, config.tolerance_fraction * delta_p)

    best: dict | None = None
    phase_seeds = np.mod(periods, delta_p)

    for phase_seed in phase_seeds:
        orders = np.rint((periods - phase_seed) / delta_p).astype(int)
        if np.unique(orders).size < config.min_modes:
            continue

        p0 = _weighted_intercept(periods, orders, delta_p, weights)
        residuals = periods - (p0 + orders * delta_p)
        inlier_mask = np.abs(residuals) <= tolerance

        if np.count_nonzero(inlier_mask) < config.min_modes:
            continue

        refined = _fit_inliers(periods, orders, weights, inlier_mask)
        refined_p0, refined_delta = refined
        refined_orders = np.rint((periods - refined_p0) / refined_delta).astype(int)
        refined_residuals = periods - (refined_p0 + refined_orders * refined_delta)
        refined_mask = np.abs(refined_residuals) <= max(0.001, config.tolerance_fraction * refined_delta)

        score = _model_score(periods, weights, refined_orders, refined_residuals, refined_mask, config)
        if best is None or score > best["score"]:
            best = {
                "score": score,
                "p0": refined_p0,
                "delta_p": refined_delta,
                "orders": refined_orders,
                "residuals": refined_residuals,
                "mask": refined_mask,
            }

    if best is None:
        return None

    mask = best["mask"]
    inlier_periods = periods[mask]
    inlier_orders = best["orders"][mask]
    inlier_residuals = best["residuals"][mask]
    sort_order = np.argsort(inlier_orders)
    inlier_periods = inlier_periods[sort_order]
    inlier_orders = inlier_orders[sort_order]
    inlier_residuals = inlier_residuals[sort_order]

    order_span = int(inlier_orders.max() - inlier_orders.min()) if len(inlier_orders) else 0
    coverage = (
        float((inlier_periods.max() - inlier_periods.min()) / (config.period_max - config.period_min))
        if len(inlier_periods) > 1
        else 0.0
    )
    delta_p_error = _delta_error(inlier_residuals, order_span)

    return PeriodSpacingSequence(
        delta_p=float(best["delta_p"]),
        delta_p_error=delta_p_error,
        p0=float(best["p0"]),
        periods=inlier_periods.astype(float).tolist(),
        radial_orders=(inlier_orders - inlier_orders.min()).astype(int).tolist(),
        residuals=inlier_residuals.astype(float).tolist(),
        slope=None,
        n_modes=int(len(inlier_periods)),
        coverage=max(0.0, min(1.0, coverage)),
        confidence_score=float(best["score"]),
    )


def _weighted_intercept(periods: np.ndarray, orders: np.ndarray, delta_p: float, weights: np.ndarray) -> float:
    return float(np.average(periods - orders * delta_p, weights=weights))


def _fit_inliers(
    periods: np.ndarray,
    orders: np.ndarray,
    weights: np.ndarray,
    inlier_mask: np.ndarray,
) -> tuple[float, float]:
    x = orders[inlier_mask].astype(float)
    y = periods[inlier_mask]
    w = np.sqrt(weights[inlier_mask])

    if np.unique(x).size < 2:
        return float(y.mean()), 0.0

    design = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(design * w[:, None], y * w, rcond=None)
    return float(beta[0]), float(beta[1])


def _model_score(
    periods: np.ndarray,
    weights: np.ndarray,
    orders: np.ndarray,
    residuals: np.ndarray,
    inlier_mask: np.ndarray,
    config: SearchConfig,
) -> float:
    n_modes = int(np.count_nonzero(inlier_mask))
    if n_modes == 0:
        return 0.0

    tolerance = max(0.001, config.tolerance_fraction * np.median(np.diff(np.sort(periods))) if len(periods) > 1 else 0.001)
    robust_scale = np.median(np.abs(residuals[inlier_mask])) / max(tolerance, 1e-6)
    coherence = max(0.0, 1.0 - robust_scale)
    inlier_periods = periods[inlier_mask]
    coverage = (inlier_periods.max() - inlier_periods.min()) / (config.period_max - config.period_min) if n_modes > 1 else 0.0

    inlier_orders = np.sort(orders[inlier_mask])
    gaps = np.diff(inlier_orders)
    gap_penalty = float(np.sum(np.maximum(0, gaps - 1))) if gaps.size else 0.0
    gap_score = np.exp(-0.12 * gap_penalty)
    weight_score = float(np.mean(weights[inlier_mask]) / max(np.mean(weights), 1e-6))

    raw = (
        0.34 * min(1.0, n_modes / max(config.min_modes * 2, 1))
        + 0.26 * max(0.0, min(1.0, coverage))
        + 0.24 * coherence
        + 0.10 * min(1.5, weight_score) / 1.5
        + 0.06 * gap_score
    )
    if n_modes < config.min_modes:
        raw *= 0.2
    return max(0.0, min(1.0, float(raw)))


def _delta_error(residuals: np.ndarray, order_span: int) -> float | None:
    if len(residuals) < 3 or order_span <= 0:
        return None
    scatter = 1.4826 * float(np.median(np.abs(residuals - np.median(residuals))))
    return float(scatter / max(np.sqrt(len(residuals)) * order_span, 1.0))
