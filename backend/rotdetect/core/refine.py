from __future__ import annotations

import numpy as np

from .data import PeriodSpacingSequence


def refine_period_spacing_trend(sequence: PeriodSpacingSequence) -> PeriodSpacingSequence:
    periods = np.asarray(sequence.periods, dtype=float)
    orders = np.asarray(sequence.radial_orders, dtype=int)
    if len(periods) < 3:
        return sequence

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
    beta, *_ = np.linalg.lstsq(design * np.sqrt(weights)[:, None], delta_values * np.sqrt(weights), rcond=None)

    return PeriodSpacingSequence(
        delta_p=sequence.delta_p,
        delta_p_error=sequence.delta_p_error,
        p0=sequence.p0,
        periods=sequence.periods,
        radial_orders=sequence.radial_orders,
        residuals=sequence.residuals,
        slope=float(beta[1]),
        n_modes=sequence.n_modes,
        coverage=sequence.coverage,
        confidence_score=sequence.confidence_score,
    )
