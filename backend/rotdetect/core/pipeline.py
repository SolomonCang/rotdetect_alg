from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .amplitude import build_amplitude_period_clusters
from .config import SearchConfig
from .data import AnalysisResult
from .plot_payloads import build_plot_payloads
from .preprocess import peaks_to_period_points, read_frequency_table, table_to_peaks
from .ransac import fit_sequence_for_delta_p
from .refine import refine_period_spacing_trend
from .scan import scan_delta_p
from .score import rank_candidates


def run_pipeline_from_csv_bytes(
        csv_bytes: bytes,
        config: SearchConfig | None = None) -> AnalysisResult:
    config = config or SearchConfig()
    config.validate()

    df = read_frequency_table(csv_bytes, config)
    peaks, warnings = table_to_peaks(df, config)
    points = peaks_to_period_points(peaks, config)
    input_periods = 1.0 / df["frequency"]

    scan_curve = scan_delta_p(points, config)
    amplitude_period_clusters = build_amplitude_period_clusters(points)
    candidates = []
    for scan_candidate in scan_curve["selected_candidates"]:
        sequence = fit_sequence_for_delta_p(points, scan_candidate, config)
        if sequence is not None:
            candidates.append(refine_period_spacing_trend(sequence))

    candidates = rank_candidates(candidates)
    best = candidates[0] if candidates else None
    if best is None:
        warnings.append(
            "No sequence passed the minimum mode and residual criteria.")

    input_summary = {
        "input_quantity": df.attrs.get("input_quantity", "frequency"),
        "has_amplitude": not bool(df.attrs.get("amplitude_missing", False)),
        "n_rows": int(len(df)),
        "n_peaks": int(len(peaks)),
        "n_period_points": int(len(points)),
        "frequency_min": float(df["frequency"].min()),
        "frequency_max": float(df["frequency"].max()),
        "input_period_min": float(input_periods.min()),
        "input_period_max": float(input_periods.max()),
        "period_min": float(min(point.period for point in points)),
        "period_max": float(max(point.period for point in points)),
    }

    spectrum_df, background_warning = _load_spectrum_background_df(config, df)
    if background_warning:
        warnings.append(background_warning)

    return AnalysisResult(
        input_summary=input_summary,
        best_sequence=best,
        candidates=candidates[:config.top_k_candidates],
        amplitude_period_clusters=amplitude_period_clusters,
        plots=build_plot_payloads(points, best, scan_curve, spectrum_df),
        warnings=warnings,
    )


def _load_spectrum_background_df(
    config: SearchConfig,
    fallback_df,
):
    if not config.spectrum_background_path:
        return fallback_df, None

    try:
        background_path = _resolve_workspace_path(config.spectrum_background_path)
        background_df = read_frequency_table(background_path.read_bytes(), config)
        return background_df, None
    except ValueError as exc:
        return fallback_df, f"Could not load spectrum background; using input data instead: {exc}"


def _resolve_workspace_path(path_text: str) -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    raw_path = Path(path_text).expanduser()
    candidate = raw_path if raw_path.is_absolute() else repo_root / raw_path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("Spectrum background path must stay inside the workspace.") from exc
    if not resolved.is_file():
        raise ValueError(f"Spectrum background file not found: {path_text}")
    if resolved.suffix.lower() not in {".csv", ".dat", ".txt"}:
        raise ValueError("Spectrum background file must be .csv, .dat, or .txt.")
    return resolved


def result_to_dict(result: AnalysisResult) -> dict:
    return {
        "status":
        "ok",
        "input_summary":
        result.input_summary,
        "best_sequence":
        asdict(result.best_sequence) if result.best_sequence else None,
        "candidates": [asdict(candidate) for candidate in result.candidates],
        "amplitude_period_clusters":
        [asdict(cluster) for cluster in result.amplitude_period_clusters],
        "plots":
        result.plots,
        "warnings":
        result.warnings,
    }
