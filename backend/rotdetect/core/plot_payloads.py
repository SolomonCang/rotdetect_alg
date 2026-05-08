from __future__ import annotations

import numpy as np

from .data import PeriodPoint, PeriodSpacingSequence


def build_plot_payloads(
    points: list[PeriodPoint],
    sequence: PeriodSpacingSequence | None,
    scan_curve: dict,
) -> dict:
    return {
        "echelle": build_echelle_payload(points, sequence),
        "period_spacing": build_period_spacing_payload(sequence),
        "scan": build_scan_payload(scan_curve, sequence),
    }


def build_echelle_payload(points: list[PeriodPoint], sequence: PeriodSpacingSequence | None) -> dict:
    periods = np.asarray([point.period for point in points], dtype=float)
    amplitudes = np.asarray([point.amplitude for point in points], dtype=float)
    frequencies = np.asarray([point.frequency for point in points], dtype=float)

    if sequence is None:
        x = periods
        title = "Period distribution"
        x_title = "P [d]"
        inlier_mask = np.zeros_like(periods, dtype=bool)
    else:
        x = np.mod(periods, sequence.delta_p)
        title = "Period echelle"
        x_title = "P mod Delta_P [d]"
        inlier_set = {round(value, 10) for value in sequence.periods}
        inlier_mask = np.asarray([round(value, 10) in inlier_set for value in periods], dtype=bool)

    colors = np.where(inlier_mask, "#0f766e", "#94a3b8").tolist()
    sizes = (8 + 8 * (amplitudes / max(float(amplitudes.max()), 1e-12))).tolist()
    text = [
        f"f={freq:.6g} d^-1<br>P={period:.6g} d<br>A={amp:.6g}"
        for freq, period, amp in zip(frequencies, periods, amplitudes)
    ]

    return {
        "data": [
            {
                "type": "scatter",
                "mode": "markers",
                "x": x.astype(float).tolist(),
                "y": periods.astype(float).tolist(),
                "text": text,
                "hoverinfo": "text",
                "marker": {"color": colors, "size": sizes, "line": {"color": "#0f172a", "width": 0.5}},
                "name": "peaks",
            }
        ],
        "layout": {
            "title": title,
            "xaxis": {"title": x_title, "zeroline": False},
            "yaxis": {"title": "P [d]", "zeroline": False},
            "margin": {"l": 58, "r": 20, "t": 42, "b": 52},
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
        },
    }


def build_period_spacing_payload(sequence: PeriodSpacingSequence | None) -> dict:
    if sequence is None or len(sequence.periods) < 2:
        return _empty_plot("P-Delta P", "P_mid [d]", "Delta P [d]")

    periods = np.asarray(sequence.periods, dtype=float)
    orders = np.asarray(sequence.radial_orders, dtype=int)
    gaps = np.diff(orders)
    valid = gaps > 0
    period_mid = 0.5 * (periods[:-1][valid] + periods[1:][valid])
    delta_p = np.diff(periods)[valid] / gaps[valid]

    traces = [
        {
            "type": "scatter",
            "mode": "markers+lines",
            "x": period_mid.astype(float).tolist(),
            "y": delta_p.astype(float).tolist(),
            "marker": {"color": "#2563eb", "size": 9},
            "line": {"color": "#93c5fd", "width": 1.5},
            "name": "adjacent spacing",
        }
    ]

    if sequence.slope is not None and len(period_mid) >= 2:
        p_ref = float(np.mean(period_mid))
        x_line = np.linspace(float(period_mid.min()), float(period_mid.max()), 80)
        y_line = sequence.delta_p + sequence.slope * (x_line - p_ref)
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "x": x_line.astype(float).tolist(),
                "y": y_line.astype(float).tolist(),
                "line": {"color": "#dc2626", "width": 2},
                "name": "linear trend",
            }
        )

    return {
        "data": traces,
        "layout": {
            "title": "P-Delta P",
            "xaxis": {"title": "P_mid [d]", "zeroline": False},
            "yaxis": {"title": "Delta P [d]", "zeroline": False},
            "margin": {"l": 58, "r": 20, "t": 42, "b": 52},
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
        },
    }


def build_scan_payload(scan_curve: dict, sequence: PeriodSpacingSequence | None) -> dict:
    traces = [
        {
            "type": "scatter",
            "mode": "lines",
            "x": scan_curve.get("delta_p", []),
            "y": scan_curve.get("score", []),
            "line": {"color": "#475569", "width": 1.6},
            "name": "scan score",
        }
    ]
    if sequence is not None:
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "x": [sequence.delta_p],
                "y": [_score_at(scan_curve, sequence.delta_p)],
                "marker": {"color": "#dc2626", "size": 10},
                "name": "best",
            }
        )

    return {
        "data": traces,
        "layout": {
            "title": "Delta_P scan",
            "xaxis": {"title": "Delta_P [d]", "zeroline": False},
            "yaxis": {"title": "score", "zeroline": False},
            "margin": {"l": 58, "r": 20, "t": 42, "b": 52},
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
        },
    }


def _score_at(scan_curve: dict, delta_p: float) -> float | None:
    xs = np.asarray(scan_curve.get("delta_p", []), dtype=float)
    ys = np.asarray(scan_curve.get("score", []), dtype=float)
    if xs.size == 0:
        return None
    return float(ys[int(np.argmin(np.abs(xs - delta_p)))])


def _empty_plot(title: str, x_title: str, y_title: str) -> dict:
    return {
        "data": [],
        "layout": {
            "title": title,
            "xaxis": {"title": x_title},
            "yaxis": {"title": y_title},
            "margin": {"l": 58, "r": 20, "t": 42, "b": 52},
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
        },
    }
