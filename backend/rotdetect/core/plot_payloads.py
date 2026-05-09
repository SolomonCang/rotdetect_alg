from __future__ import annotations

import numpy as np
import pandas as pd

from .data import PeriodPoint, PeriodSpacingSequence


def build_plot_payloads(
    points: list[PeriodPoint],
    sequence: PeriodSpacingSequence | None,
    scan_curve: dict,
    spectrum_df: pd.DataFrame | None = None,
) -> dict:
    payloads = {
        "echelle": build_echelle_payload(points, sequence),
        "period_spacing": build_period_spacing_payload(sequence),
        "scan": build_scan_payload(scan_curve, sequence),
    }
    if spectrum_df is not None:
        payloads["spectrum"] = build_spectrum_payload(spectrum_df)
    return payloads


def build_spectrum_payload(df: pd.DataFrame) -> dict:
    periods = (1.0 / df["frequency"].to_numpy(dtype=float))
    amplitudes = df["amplitude"].to_numpy(dtype=float)
    frequencies = df["frequency"].to_numpy(dtype=float)
    continuous = is_continuous_spectrum(frequencies)
    order = np.argsort(periods)
    periods = periods[order]
    amplitudes = amplitudes[order]

    return {
        "data": [{
            "type": "scatter",
            "mode": "lines" if continuous else "markers",
            "x": periods.astype(float).tolist(),
            "y": amplitudes.astype(float).tolist(),
            "line": {
                "color": "#191919",
                "width": 0.9,
            },
            "marker": {
                "color": "rgba(82, 82, 82, 0.5)",
                "size": 3,
            },
            "name": "full FFT" if continuous else "input peaks",
            "hovertemplate": "P=%{x:.6g} d<br>A=%{y:.6g}<extra></extra>",
        }],
        "layout": {
            "title": "Full spectrum",
            "meta": {
                "continuous_spectrum": continuous,
            },
            "xaxis": {
                "title": "P [d]",
                "zeroline": False,
            },
            "yaxis": {
                "title": "A",
                "zeroline": False,
            },
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
        },
    }


def is_continuous_spectrum(frequencies: np.ndarray) -> bool:
    if frequencies.size < 2000:
        return False
    sorted_frequencies = np.sort(frequencies)
    diffs = np.diff(sorted_frequencies)
    positive_diffs = diffs[diffs > 0]
    if positive_diffs.size == 0:
        return False
    median_step = float(np.median(positive_diffs))
    max_step = float(np.max(positive_diffs))
    return median_step > 0 and max_step <= median_step * 20


def build_echelle_payload(points: list[PeriodPoint],
                          sequence: PeriodSpacingSequence | None) -> dict:
    periods = np.asarray([point.period for point in points], dtype=float)
    amplitudes = np.asarray([point.amplitude for point in points], dtype=float)
    frequencies = np.asarray([point.frequency for point in points],
                             dtype=float)

    if sequence is None:
        x = periods
        title = "Period distribution"
        x_title = "P [d]"
        inlier_mask = np.zeros_like(periods, dtype=bool)
    else:
        x = np.mod(periods, sequence.delta_p_mid) * 86400
        title = "Period echelle"
        x_title = "P mod representative Delta_P [s]"
        inlier_set = {round(value, 10) for value in sequence.periods}
        inlier_mask = np.asarray(
            [round(value, 10) in inlier_set for value in periods], dtype=bool)

    # 使用振幅归一化值作为颜色映射
    # 分离 inlier 和 outlier 点：inlier 用绿色，outlier 用蓝色，都按振幅调节透明度
    amp_normalized = amplitudes / max(float(amplitudes.max()), 1e-12)
    sizes = (8 + 8 * amp_normalized).tolist()

    # 为 inlier 和 outlier 分别创建两个 trace，这样可以使用不同的颜色映射
    # Inlier points：绿色系，按振幅调节深度
    inlier_indices = np.where(inlier_mask)[0]
    # Outlier points：蓝色系，按振幅调节深度
    outlier_indices = np.where(~inlier_mask)[0]

    traces = []

    # 绘制 inlier 点
    if len(inlier_indices) > 0:
        inlier_amps = amp_normalized[inlier_indices]
        inlier_text = [
            f"f={frequencies[i]:.6g} d^-1<br>P={periods[i]:.6g} d<br>A={amplitudes[i]:.6g}"
            for i in inlier_indices
        ]
        inlier_colors = [
            f"rgba(15, 118, 110, {0.4 + 0.6 * amp:.1f})"  # 绿色系，透明度 0.4-1.0
            for amp in inlier_amps
        ]
        traces.append({
            "type": "scatter",
            "mode": "markers",
            "x": x[inlier_indices].astype(float).tolist(),
            "y": periods[inlier_indices].astype(float).tolist(),
            "text": inlier_text,
            "hoverinfo": "text",
            "marker": {
                "color": inlier_colors,
                "size": [sizes[i] for i in inlier_indices],
                "line": {
                    "color": "#0f172a",
                    "width": 0.5
                }
            },
            "name": "inliers",
        })

    # 绘制 outlier 点
    if len(outlier_indices) > 0:
        outlier_amps = amp_normalized[outlier_indices]
        outlier_text = [
            f"f={frequencies[i]:.6g} d^-1<br>P={periods[i]:.6g} d<br>A={amplitudes[i]:.6g}"
            for i in outlier_indices
        ]
        outlier_colors = [
            f"rgba(148, 163, 184, {0.4 + 0.6 * amp:.1f})"  # 灰色系，透明度 0.4-1.0
            for amp in outlier_amps
        ]
        traces.append({
            "type": "scatter",
            "mode": "markers",
            "x": x[outlier_indices].astype(float).tolist(),
            "y": periods[outlier_indices].astype(float).tolist(),
            "text": outlier_text,
            "hoverinfo": "text",
            "marker": {
                "color": outlier_colors,
                "size": [sizes[i] for i in outlier_indices],
                "line": {
                    "color": "#0f172a",
                    "width": 0.5
                }
            },
            "name": "outliers",
        })

    return {
        "data": traces,
        "layout": {
            "title":
            title,
            "xaxis": {
                "title": x_title,
                "zeroline": False
            },
            "yaxis": {
                "title": "P [d]",
                "zeroline": False
            },
            "margin": {
                "l": 58,
                "r": 20,
                "t": 42,
                "b": 52
            },
            "paper_bgcolor":
            "white",
            "plot_bgcolor":
            "white",
            "hovermode":
            "closest",
            "annotations": [{
                "text":
                "振幅信息通过：<br>• 标记大小（marker size）<br>• 颜色透明度（opacity）<br>• Hover 文本中的 A 值",
                "xref": "paper",
                "yref": "paper",
                "x": 0.02,
                "y": 0.98,
                "showarrow": False,
                "bgcolor": "rgba(255, 255, 255, 0.8)",
                "bordercolor": "#cbd5e1",
                "borderwidth": 1,
                "font": {
                    "size": 11
                },
                "align": "left",
                "xanchor": "left",
                "yanchor": "top"
            }] if amplitudes.max() > 0 else []
        }
    }


def build_period_spacing_payload(
        sequence: PeriodSpacingSequence | None) -> dict:
    if sequence is None or len(sequence.periods) < 2:
        return _empty_plot("P-Delta P", "P_mid [d]", "Delta P [s]")

    periods = np.asarray(sequence.periods, dtype=float)
    orders = np.asarray(sequence.radial_orders, dtype=int)
    gaps = np.diff(orders)
    valid = gaps > 0
    period_mid = 0.5 * (periods[:-1][valid] + periods[1:][valid])
    delta_p = np.diff(periods)[valid] / gaps[valid]

    traces = [{
        "type": "scatter",
        "mode": "markers+lines",
        "x": period_mid.astype(float).tolist(),
        "y": (delta_p * 86400).astype(float).tolist(),
        "marker": {
            "color": "#2563eb",
            "size": 9
        },
        "line": {
            "color": "#93c5fd",
            "width": 1.5
        },
        "name": "adjacent spacing",
    }]

    if sequence.slope is not None and len(period_mid) >= 2:
        p_ref = float(np.mean(period_mid))
        x_line = np.linspace(float(period_mid.min()), float(period_mid.max()),
                             80)
        y_line = (sequence.delta_p_mid + sequence.slope *
                  (x_line - p_ref)) * 86400
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": x_line.astype(float).tolist(),
            "y": y_line.astype(float).tolist(),
            "line": {
                "color": "#dc2626",
                "width": 2
            },
            "name": "linear trend",
        })

    return {
        "data": traces,
        "layout": {
            "title": "P-Delta P",
            "xaxis": {
                "title": "P_mid [d]",
                "zeroline": False
            },
            "yaxis": {
                "title": "Delta P [s]",
                "zeroline": False
            },
            "margin": {
                "l": 58,
                "r": 20,
                "t": 42,
                "b": 52
            },
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
        },
    }


def build_scan_payload(scan_curve: dict,
                       sequence: PeriodSpacingSequence | None) -> dict:
    delta_p_mid_values = np.asarray(scan_curve.get("delta_p_mid", []),
                                    dtype=float) * 86400
    slope_values = np.asarray(scan_curve.get("slope", []), dtype=float) * 86400
    score_grid = np.asarray(scan_curve.get("score_grid", []), dtype=float)
    traces = [{
        "type": "heatmap",
        "x": delta_p_mid_values.astype(float).tolist(),
        "y": slope_values.astype(float).tolist(),
        "z": score_grid.astype(float).tolist(),
        "colorscale": "Viridis",
        "colorbar": {
            "title": "score"
        },
        "name": "trend scan",
    }]
    if sequence is not None:
        best_x = sequence.delta_p_mid * 86400
        best_y = sequence.slope * 86400 if sequence.slope is not None else 0.0
        x_min = float(
            delta_p_mid_values.min()) if delta_p_mid_values.size else best_x
        x_max = float(
            delta_p_mid_values.max()) if delta_p_mid_values.size else best_x
        y_min = float(slope_values.min()) if slope_values.size else best_y
        y_max = float(slope_values.max()) if slope_values.size else best_y
        traces.append({
            "type": "scatter",
            "mode": "markers",
            "x": [best_x],
            "y": [best_y],
            "marker": {
                "color": "#ffffff",
                "size": 18,
                "symbol": "star",
                "line": {
                    "color": "#dc2626",
                    "width": 3,
                },
            },
            "name": "best candidate",
            "hovertemplate": "best candidate<extra></extra>",
        })
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": [best_x, best_x],
            "y": [y_min, y_max],
            "line": {
                "color": "#dc2626",
                "width": 2,
                "dash": "dot",
            },
            "name": "best slope",
            "hoverinfo": "skip",
            "showlegend": False,
        })
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": [x_min, x_max],
            "y": [best_y, best_y],
            "line": {
                "color": "#dc2626",
                "width": 2,
                "dash": "dot",
            },
            "name": "best delta_p",
            "hoverinfo": "skip",
            "showlegend": False,
        })

    return {
        "data": traces,
        "layout": {
            "title":
            "Linear trend scan",
            "xaxis": {
                "title": "Delta_P mid [s]",
                "zeroline": False
            },
            "yaxis": {
                "title": "slope [s/d]",
                "zeroline": False
            },
            "annotations": [{
                "x": best_x,
                "y": best_y,
                "text": "best",
                "showarrow": True,
                "arrowhead": 2,
                "ax": 24,
                "ay": -24,
                "font": {
                    "color": "#dc2626",
                    "size": 12,
                },
                "arrowcolor": "#dc2626",
            }] if sequence is not None else [],
            "margin": {
                "l": 58,
                "r": 20,
                "t": 42,
                "b": 52
            },
            "paper_bgcolor":
            "white",
            "plot_bgcolor":
            "white",
        },
    }


def _empty_plot(title: str, x_title: str, y_title: str) -> dict:
    return {
        "data": [],
        "layout": {
            "title": title,
            "xaxis": {
                "title": x_title
            },
            "yaxis": {
                "title": y_title
            },
            "margin": {
                "l": 58,
                "r": 20,
                "t": 42,
                "b": 52
            },
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
        },
    }
