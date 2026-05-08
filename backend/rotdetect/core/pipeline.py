from __future__ import annotations

from dataclasses import asdict

from .config import SearchConfig
from .data import AnalysisResult
from .plot_payloads import build_plot_payloads
from .preprocess import peaks_to_period_points, read_frequency_table, table_to_peaks
from .ransac import fit_sequence_for_delta_p
from .refine import refine_period_spacing_trend
from .scan import scan_delta_p
from .score import rank_candidates


def run_pipeline_from_csv_bytes(csv_bytes: bytes, config: SearchConfig | None = None) -> AnalysisResult:
    config = config or SearchConfig()
    config.validate()

    df = read_frequency_table(csv_bytes)
    peaks, warnings = table_to_peaks(df, config)
    points = peaks_to_period_points(peaks, config)

    scan_curve = scan_delta_p(points, config)
    candidates = []
    for delta_p in scan_curve["selected_candidates"]:
        sequence = fit_sequence_for_delta_p(points, delta_p, config)
        if sequence is not None:
            candidates.append(refine_period_spacing_trend(sequence))

    candidates = rank_candidates(candidates)
    best = candidates[0] if candidates else None
    if best is None:
        warnings.append("No sequence passed the minimum mode and residual criteria.")

    input_summary = {
        "input_quantity": df.attrs.get("input_quantity", "frequency"),
        "has_amplitude": not bool(df.attrs.get("amplitude_missing", False)),
        "n_rows": int(len(df)),
        "n_peaks": int(len(peaks)),
        "n_period_points": int(len(points)),
        "frequency_min": float(df["frequency"].min()),
        "frequency_max": float(df["frequency"].max()),
        "period_min": float(min(point.period for point in points)),
        "period_max": float(max(point.period for point in points)),
    }

    return AnalysisResult(
        input_summary=input_summary,
        best_sequence=best,
        candidates=candidates[: config.top_k_candidates],
        plots=build_plot_payloads(points, best, scan_curve),
        warnings=warnings,
    )


def result_to_dict(result: AnalysisResult) -> dict:
    return {
        "status": "ok",
        "input_summary": result.input_summary,
        "best_sequence": asdict(result.best_sequence) if result.best_sequence else None,
        "candidates": [asdict(candidate) for candidate in result.candidates],
        "plots": result.plots,
        "warnings": result.warnings,
    }
