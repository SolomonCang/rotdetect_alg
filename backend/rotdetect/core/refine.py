from __future__ import annotations

from dataclasses import replace

import numpy as np

from .data import PeriodSpacingSequence


def refine_period_spacing_trend(
        sequence: PeriodSpacingSequence) -> PeriodSpacingSequence:
    periods = np.asarray(sequence.periods, dtype=float)
    orders = np.asarray(sequence.radial_orders, dtype=int)
    if len(periods) < 3:
        return replace(sequence, delta_p=sequence.delta_p_mid)

    order_gaps = np.diff(orders)
    period_gaps = np.diff(periods)
    valid = order_gaps > 0
    if np.count_nonzero(valid) < 2:
        return sequence

    delta_values = period_gaps[valid] / order_gaps[valid]
    period_mid = 0.5 * (periods[:-1][valid] + periods[1:][valid])
    weights = 1.0 / order_gaps[valid]
    p_ref = float(np.average(period_mid, weights=weights))

    x = period_mid - p_ref
    design = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(design * np.sqrt(weights)[:, None],
                               delta_values * np.sqrt(weights),
                               rcond=None)
    delta_p_mid = float(beta[0])
    slope = float(beta[1])
    delta_p_start = float(
        max(delta_p_mid + slope * (float(periods.min()) - p_ref), 1e-6))
    delta_p_end = float(
        max(delta_p_mid + slope * (float(periods.max()) - p_ref), 1e-6))

    return replace(
        sequence,
        delta_p=delta_p_mid,
        delta_p_start=delta_p_start,
        delta_p_mid=delta_p_mid,
        delta_p_end=delta_p_end,
        slope=slope,
    )
