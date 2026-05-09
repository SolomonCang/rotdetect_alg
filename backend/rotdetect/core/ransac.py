from __future__ import annotations

import numpy as np

from .config import SearchConfig
from .data import PeriodPoint, PeriodSpacingSequence


def fit_sequence_for_delta_p(
    points: list[PeriodPoint],
    scan_candidate: dict,
    config: SearchConfig,
) -> PeriodSpacingSequence | None:
    periods = np.asarray([point.period for point in points], dtype=float)
    amplitudes = np.asarray([point.amplitude for point in points], dtype=float)
    weights = np.asarray([point.weight for point in points], dtype=float)
    delta_p_mid_seed = float(scan_candidate["delta_p_mid"])
    slope_seed = float(scan_candidate.get("slope", 0.0))
    p_ref = float(np.average(periods,
                             weights=weights)) if periods.size else 0.0
    tolerance = max(0.001, config.tolerance_fraction * delta_p_mid_seed)

    tau = _trend_phase_coordinate(periods, delta_p_mid_seed, slope_seed, p_ref)
    if tau is None:
        return None

    best: dict | None = None
    phase_seeds = np.mod(tau, 1.0)

    for phase_seed in phase_seeds:
        orders = np.rint(tau - phase_seed).astype(int)
        if np.unique(orders).size < config.min_modes:
            continue

        predicted_seed = _inverse_trend_coordinate(orders + phase_seed,
                                                   delta_p_mid_seed,
                                                   slope_seed, p_ref)
        if predicted_seed is None:
            continue

        p0 = _weighted_intercept(periods, orders, delta_p_mid_seed, weights)
        residuals = periods - predicted_seed
        inlier_mask = np.abs(residuals) <= tolerance

        if np.count_nonzero(inlier_mask) < config.min_modes:
            continue

        refined_coeffs = _fit_polynomial_in_orders(periods, orders, weights,
                                                   inlier_mask)
        refined_orders = orders.copy()
        refined_p0 = float(refined_coeffs[0])
        refined_delta = _delta_mid_from_coeffs(refined_orders, refined_coeffs)
        refined_tolerance = max(0.001,
                                config.tolerance_fraction * abs(refined_delta))

        refined_residuals = periods - _predict_order_polynomial(
            refined_orders, refined_coeffs)
        refined_mask = np.abs(refined_residuals) <= refined_tolerance

        quad_coeffs = _fit_quadratic_in_orders(periods, refined_orders,
                                               weights, refined_residuals,
                                               refined_tolerance)
        if quad_coeffs is not None:
            quad_pred = _predict_quadratic_in_orders(refined_orders,
                                                     quad_coeffs)
            refined_residuals = periods - quad_pred
            refined_mask = np.abs(refined_residuals) <= refined_tolerance

        chain_candidate_mask = np.abs(refined_residuals) <= max(
            refined_tolerance * 1.35, 0.0012)
        refined_mask = _select_order_chain(
            periods,
            refined_orders,
            refined_residuals,
            weights,
            chain_candidate_mask,
            refined_tolerance,
            quad_coeffs,
            refined_delta,
        )
        refined_mask = _one_per_order_mask(refined_orders, refined_residuals,
                                           weights, refined_mask)

        if np.count_nonzero(refined_mask) < config.min_modes:
            continue

        refined_delta = _representative_delta(refined_orders,
                                              periods,
                                              refined_mask,
                                              fallback=abs(refined_delta))

        score = _model_score(periods, weights, refined_orders,
                             refined_residuals, refined_mask, config)
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
    inlier_amplitudes = amplitudes[mask]
    inlier_weights = weights[mask]
    inlier_orders = best["orders"][mask]
    inlier_residuals = best["residuals"][mask]
    sort_order = np.argsort(inlier_orders)
    inlier_periods = inlier_periods[sort_order]
    inlier_amplitudes = inlier_amplitudes[sort_order]
    inlier_weights = inlier_weights[sort_order]
    inlier_orders = inlier_orders[sort_order]
    inlier_residuals = inlier_residuals[sort_order]

    order_span = int(inlier_orders.max() -
                     inlier_orders.min()) if len(inlier_orders) else 0
    coverage = (float((inlier_periods.max() - inlier_periods.min()) /
                      (config.period_max - config.period_min))
                if len(inlier_periods) > 1 else 0.0)
    delta_p_error = _delta_error(inlier_residuals, order_span)
    amplitude_score = _amplitude_priority_score(inlier_weights, weights)

    return PeriodSpacingSequence(
        delta_p=float(best["delta_p"]),
        delta_p_start=float(best["delta_p"]),
        delta_p_mid=float(best["delta_p"]),
        delta_p_end=float(best["delta_p"]),
        delta_p_error=delta_p_error,
        p0=float(best["p0"]),
        periods=inlier_periods.astype(float).tolist(),
        amplitudes=inlier_amplitudes.astype(float).tolist(),
        radial_orders=(inlier_orders -
                       inlier_orders.min()).astype(int).tolist(),
        residuals=inlier_residuals.astype(float).tolist(),
        slope=None,
        n_modes=int(len(inlier_periods)),
        coverage=max(0.0, min(1.0, coverage)),
        confidence_score=float(best["score"]),
        amplitude_score=amplitude_score,
        amplitude_mean=float(np.mean(inlier_amplitudes)),
        amplitude_median=float(np.median(inlier_amplitudes)),
    )


def _weighted_intercept(periods: np.ndarray, orders: np.ndarray,
                        delta_p: float, weights: np.ndarray) -> float:
    return float(np.average(periods - orders * delta_p, weights=weights))


def _fit_polynomial_in_orders(
    periods: np.ndarray,
    orders: np.ndarray,
    weights: np.ndarray,
    inlier_mask: np.ndarray,
) -> tuple[float, float, float]:
    x = orders[inlier_mask].astype(float)
    y = periods[inlier_mask]
    w = np.sqrt(weights[inlier_mask])

    if np.unique(x).size < 2:
        return float(y.mean()), 0.0, 0.0

    if np.unique(x).size < 4:
        design = np.column_stack([np.ones_like(x), x])
        beta, *_ = np.linalg.lstsq(design * w[:, None], y * w, rcond=None)
        return float(beta[0]), float(beta[1]), 0.0

    design = np.column_stack([np.ones_like(x), x, x * x])
    beta, *_ = np.linalg.lstsq(design * w[:, None], y * w, rcond=None)
    return float(beta[0]), float(beta[1]), float(beta[2])


def _predict_order_polynomial(
    orders: np.ndarray,
    coeffs: tuple[float, float, float],
) -> np.ndarray:
    a, b, c = coeffs
    x = orders.astype(float)
    return a + b * x + c * x * x


def _delta_mid_from_coeffs(
    orders: np.ndarray,
    coeffs: tuple[float, float, float],
) -> float:
    _, linear_term, quadratic_term = coeffs
    center_order = float(np.median(orders)) if orders.size else 0.0
    return float(
        max(abs(linear_term + 2.0 * quadratic_term * center_order), 1e-6))


def _trend_phase_coordinate(
    periods: np.ndarray,
    delta_p_mid: float,
    slope: float,
    p_ref: float,
) -> np.ndarray | None:
    delta_values = delta_p_mid + slope * (periods - p_ref)
    if np.any(delta_values <= 0):
        return None

    if abs(slope) < 1e-10:
        return (periods - p_ref) / delta_p_mid

    return np.log(delta_values / delta_p_mid) / slope


def _inverse_trend_coordinate(
    tau: np.ndarray,
    delta_p_mid: float,
    slope: float,
    p_ref: float,
) -> np.ndarray | None:
    if abs(slope) < 1e-10:
        return p_ref + delta_p_mid * tau

    periods = p_ref + delta_p_mid * np.expm1(slope * tau) / slope
    if np.any(~np.isfinite(periods)):
        return None
    return periods


def _fit_quadratic_in_orders(
    periods: np.ndarray,
    orders: np.ndarray,
    weights: np.ndarray,
    residuals: np.ndarray,
    tolerance: float,
) -> tuple[float, float, float] | None:
    scaled_residual = np.abs(residuals) / max(tolerance, 1e-6)
    soft_mask = scaled_residual <= 3.5
    if np.count_nonzero(soft_mask) < 4:
        return None

    x = orders[soft_mask].astype(float)
    y = periods[soft_mask]
    robust_weights = np.exp(-0.5 * np.square(scaled_residual[soft_mask]))
    w = np.sqrt(weights[soft_mask] * robust_weights)

    if np.unique(x).size < 4:
        return None

    design = np.column_stack([np.ones_like(x), x, x * x])
    beta, *_ = np.linalg.lstsq(design * w[:, None], y * w, rcond=None)
    return float(beta[0]), float(beta[1]), float(beta[2])


def _predict_quadratic_in_orders(
    orders: np.ndarray,
    coeffs: tuple[float, float, float],
) -> np.ndarray:
    a, b, c = coeffs
    x = orders.astype(float)
    return a + b * x + c * x * x


def _one_per_order_mask(
    orders: np.ndarray,
    residuals: np.ndarray,
    weights: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    indices = np.where(mask)[0]
    if indices.size == 0:
        return mask

    best_index_by_order: dict[int, int] = {}
    best_score_by_order: dict[int, tuple[float, float]] = {}
    for index in indices:
        order = int(orders[index])
        score = (float(abs(residuals[index])), float(-weights[index]))
        previous = best_score_by_order.get(order)
        if previous is None or score < previous:
            best_score_by_order[order] = score
            best_index_by_order[order] = int(index)

    dedup_mask = np.zeros_like(mask, dtype=bool)
    for index in best_index_by_order.values():
        dedup_mask[index] = True
    return dedup_mask


def _select_order_chain(
    periods: np.ndarray,
    orders: np.ndarray,
    residuals: np.ndarray,
    weights: np.ndarray,
    mask: np.ndarray,
    tolerance: float,
    quad_coeffs: tuple[float, float, float] | None,
    fallback_delta: float,
) -> np.ndarray:
    indices = np.where(mask)[0]
    if indices.size == 0:
        return mask

    candidate_indices = sorted(indices.tolist(),
                               key=lambda idx:
                               (int(orders[idx]), float(periods[idx])))
    dp_scores = np.full(len(candidate_indices), -np.inf, dtype=float)
    parent = np.full(len(candidate_indices), -1, dtype=int)
    chain_lengths = np.ones(len(candidate_indices), dtype=int)
    max_gap = 5

    for i, idx in enumerate(candidate_indices):
        node_score = _chain_node_score(residuals[idx], weights[idx], tolerance)
        dp_scores[i] = node_score

        for j in range(i):
            prev_idx = candidate_indices[j]
            gap = int(orders[idx] - orders[prev_idx])
            if gap <= 0 or gap > max_gap:
                continue

            transition_score = _chain_transition_score(
                periods[prev_idx],
                periods[idx],
                int(orders[prev_idx]),
                int(orders[idx]),
                tolerance,
                quad_coeffs,
                fallback_delta,
            )
            if not np.isfinite(transition_score):
                continue

            score = dp_scores[j] + node_score + transition_score
            next_length = chain_lengths[j] + 1
            if score > dp_scores[i] or (np.isclose(score, dp_scores[i])
                                        and next_length > chain_lengths[i]):
                dp_scores[i] = score
                parent[i] = j
                chain_lengths[i] = next_length

    best_position = int(np.argmax(dp_scores))
    selected = np.zeros_like(mask, dtype=bool)
    while best_position >= 0:
        selected[candidate_indices[best_position]] = True
        best_position = parent[best_position]
    return selected


def _chain_node_score(residual: float, weight: float,
                      tolerance: float) -> float:
    normalized_residual = abs(float(residual)) / max(tolerance, 1e-6)
    weight_term = 0.18 * min(5.0, float(weight))
    return 1.0 + weight_term - 0.85 * normalized_residual


def _chain_transition_score(
    previous_period: float,
    current_period: float,
    previous_order: int,
    current_order: int,
    tolerance: float,
    quad_coeffs: tuple[float, float, float] | None,
    fallback_delta: float,
) -> float:
    gap = current_order - previous_order
    if gap <= 0:
        return float("-inf")

    observed_delta = (current_period - previous_period) / gap
    expected_delta = _expected_delta_between_orders(previous_order,
                                                    current_order, quad_coeffs,
                                                    fallback_delta)
    delta_mismatch = abs(observed_delta - expected_delta)
    mismatch_scale = max(0.18 * max(abs(fallback_delta), 1e-6),
                         tolerance / gap)
    if delta_mismatch > 3.5 * mismatch_scale:
        return float("-inf")

    gap_penalty = 0.24 * max(0, gap - 1)
    smooth_penalty = 0.9 * delta_mismatch / max(mismatch_scale, 1e-6)
    return -gap_penalty - smooth_penalty


def _expected_delta_between_orders(
    previous_order: int,
    current_order: int,
    quad_coeffs: tuple[float, float, float] | None,
    fallback_delta: float,
) -> float:
    if quad_coeffs is None:
        return float(abs(fallback_delta))

    _, linear_term, quadratic_term = quad_coeffs
    midpoint_order = 0.5 * (previous_order + current_order)
    expected = linear_term + 2.0 * quadratic_term * midpoint_order
    return float(max(abs(expected), abs(fallback_delta) * 0.3, 1e-6))


def _representative_delta(
    orders: np.ndarray,
    periods: np.ndarray,
    mask: np.ndarray,
    fallback: float,
) -> float:
    inlier_orders = orders[mask]
    inlier_periods = periods[mask]
    if inlier_orders.size < 2:
        return float(fallback)

    sort_index = np.argsort(inlier_orders)
    inlier_orders = inlier_orders[sort_index]
    inlier_periods = inlier_periods[sort_index]

    gaps = np.diff(inlier_orders)
    valid = gaps > 0
    if not np.any(valid):
        return float(fallback)

    local_delta = np.diff(inlier_periods)[valid] / gaps[valid]
    if local_delta.size == 0:
        return float(fallback)
    return float(np.median(np.abs(local_delta)))


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

    tolerance = max(
        0.001,
        config.tolerance_fraction *
        np.median(np.diff(np.sort(periods))) if len(periods) > 1 else 0.001)
    robust_scale = np.median(np.abs(residuals[inlier_mask])) / max(
        tolerance, 1e-6)
    coherence = max(0.0, 1.0 - robust_scale)
    inlier_periods = periods[inlier_mask]
    coverage = (inlier_periods.max() - inlier_periods.min()) / (
        config.period_max - config.period_min) if n_modes > 1 else 0.0

    inlier_orders = np.sort(orders[inlier_mask])
    gaps = np.diff(inlier_orders)
    gap_penalty = float(np.sum(np.maximum(0, gaps - 1))) if gaps.size else 0.0
    gap_score = np.exp(-0.12 * gap_penalty)
    weight_score = float(
        np.mean(weights[inlier_mask]) / max(np.mean(weights), 1e-6))
    slope_quality = _slope_quality(periods, orders, inlier_mask)

    n_scale = max(config.min_modes * 6, config.min_modes + 10)
    n_score = min(1.0, np.log1p(n_modes) / np.log1p(n_scale))

    raw = (0.30 * n_score + 0.23 * max(0.0, min(1.0, coverage)) +
           0.22 * coherence + 0.11 * gap_score +
           0.08 * min(1.5, weight_score) / 1.5 + 0.06 * slope_quality)
    if n_modes < config.min_modes:
        raw *= 0.2
    return max(0.0, min(1.0, float(raw)))


def _slope_quality(
    periods: np.ndarray,
    orders: np.ndarray,
    inlier_mask: np.ndarray,
) -> float:
    inlier_periods = periods[inlier_mask]
    inlier_orders = orders[inlier_mask]
    if inlier_periods.size < 4:
        return 0.0

    sort_index = np.argsort(inlier_orders)
    inlier_periods = inlier_periods[sort_index]
    inlier_orders = inlier_orders[sort_index]

    gaps = np.diff(inlier_orders)
    valid = gaps > 0
    if np.count_nonzero(valid) < 3:
        return 0.0

    delta_values = np.diff(inlier_periods)[valid] / gaps[valid]
    period_mid = 0.5 * (inlier_periods[:-1][valid] + inlier_periods[1:][valid])
    weights = 1.0 / gaps[valid]

    x = period_mid - float(np.average(period_mid, weights=weights))
    design = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(design * np.sqrt(weights)[:, None],
                               delta_values * np.sqrt(weights),
                               rcond=None)
    predicted = design @ beta

    weighted_sse = float(np.sum(weights * (delta_values - predicted)**2))
    weighted_var = float(
        np.sum(weights *
               (delta_values - np.average(delta_values, weights=weights))**2))
    if weighted_var <= 1e-12:
        return 0.0
    return max(0.0, min(1.0, 1.0 - weighted_sse / weighted_var))


def _delta_error(residuals: np.ndarray, order_span: int) -> float | None:
    if len(residuals) < 3 or order_span <= 0:
        return None
    scatter = 1.4826 * float(
        np.median(np.abs(residuals - np.median(residuals))))
    return float(scatter / max(np.sqrt(len(residuals)) * order_span, 1.0))


def _amplitude_priority_score(selected_weights: np.ndarray,
                              all_weights: np.ndarray) -> float:
    if selected_weights.size == 0 or all_weights.size == 0:
        return 0.0

    top_count = min(selected_weights.size, all_weights.size)
    best_possible = float(np.sum(np.sort(all_weights)[-top_count:]))
    if best_possible <= 0:
        return 0.0
    return max(0.0, min(1.0, float(np.sum(selected_weights) / best_possible)))
