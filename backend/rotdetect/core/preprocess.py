from __future__ import annotations

import io

import numpy as np
import pandas as pd

from .config import SearchConfig
from .data import FrequencyPeak, PeriodPoint
from .peaks import extract_peaks


def read_frequency_table(csv_bytes: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
    except Exception as exc:  # pragma: no cover - pandas message varies
        raise ValueError(f"Could not read CSV file: {exc}") from exc

    df.columns = [str(column).strip().lower() for column in df.columns]
    if "frequency" not in df.columns and "period" not in df.columns:
        raise ValueError("CSV must contain either a frequency column or a period column.")

    df = df.copy()
    input_quantity = "frequency" if "frequency" in df.columns else "period"
    amplitude_missing = "amplitude" not in df.columns

    if "period" in df.columns:
        df["period"] = pd.to_numeric(df["period"], errors="coerce")
    if "frequency" in df.columns:
        df["frequency"] = pd.to_numeric(df["frequency"], errors="coerce")
    else:
        df = df.dropna(subset=["period"])
        df = df[df["period"] > 0]
        df["frequency"] = 1.0 / df["period"]

    if amplitude_missing:
        df["amplitude"] = 1.0
    else:
        df["amplitude"] = pd.to_numeric(df["amplitude"], errors="coerce")

    for optional in ("snr", "frequency_error"):
        if optional in df.columns:
            df[optional] = pd.to_numeric(df[optional], errors="coerce")

    df = df.dropna(subset=["frequency", "amplitude"])
    df = df[(df["frequency"] > 0) & np.isfinite(df["amplitude"])]
    if df.empty:
        raise ValueError("No valid positive frequency or period rows found.")

    result = df.sort_values("frequency").reset_index(drop=True)
    result.attrs["input_quantity"] = input_quantity
    result.attrs["amplitude_missing"] = amplitude_missing
    return result


def table_to_peaks(df: pd.DataFrame, config: SearchConfig) -> tuple[list[FrequencyPeak], list[str]]:
    warnings: list[str] = []
    amplitude_missing = bool(df.attrs.get("amplitude_missing", False))
    looks_like_peak_list = amplitude_missing or "snr" in df.columns or len(df) <= int(config.max_peaks * 1.5)

    if looks_like_peak_list:
        peak_df = df.copy()
        if amplitude_missing:
            warnings.append("No amplitude column found; input was treated as an already extracted peak list.")
        if "snr" in peak_df.columns:
            before = len(peak_df)
            peak_df = peak_df[(peak_df["snr"].isna()) | (peak_df["snr"] >= config.snr_threshold)]
            if len(peak_df) < before:
                warnings.append(f"Removed {before - len(peak_df)} peaks below S/N threshold.")
        peak_df = peak_df.sort_values("amplitude", ascending=False).head(config.max_peaks)
    else:
        peak_df = extract_peaks(df, config)
        warnings.append("Input treated as full spectrum; simple local-maximum peak extraction was used.")

    peaks = [
        FrequencyPeak(
            frequency=float(row.frequency),
            amplitude=float(row.amplitude),
            snr=None if "snr" not in peak_df.columns or pd.isna(getattr(row, "snr")) else float(row.snr),
            frequency_error=(
                None
                if "frequency_error" not in peak_df.columns or pd.isna(getattr(row, "frequency_error"))
                else float(row.frequency_error)
            ),
        )
        for row in peak_df.itertuples(index=False)
    ]
    if len(peaks) < config.min_modes:
        raise ValueError(f"Only {len(peaks)} usable peaks remain; at least {config.min_modes} are required.")
    return peaks, warnings


def peaks_to_period_points(peaks: list[FrequencyPeak], config: SearchConfig) -> list[PeriodPoint]:
    amplitudes = np.asarray([max(peak.amplitude, 0.0) for peak in peaks], dtype=float)
    amp_scale = float(np.nanmedian(amplitudes[amplitudes > 0])) if np.any(amplitudes > 0) else 1.0
    points: list[PeriodPoint] = []

    for peak in peaks:
        period = 1.0 / peak.frequency
        if not (config.period_min <= period <= config.period_max):
            continue

        sigma_period = None
        if peak.frequency_error is not None and peak.frequency_error > 0:
            sigma_period = peak.frequency_error / (peak.frequency * peak.frequency)

        amp_weight = np.sqrt(max(peak.amplitude, 0.0) / amp_scale) if amp_scale > 0 else 1.0
        snr_weight = np.sqrt(peak.snr / config.snr_threshold) if peak.snr and peak.snr > 0 else 1.0
        weight = float(np.clip(amp_weight * snr_weight, 0.2, 5.0))

        points.append(
            PeriodPoint(
                period=float(period),
                frequency=float(peak.frequency),
                amplitude=float(peak.amplitude),
                snr=peak.snr,
                sigma_period=sigma_period,
                weight=weight,
            )
        )

    points.sort(key=lambda point: point.period)
    if len(points) < config.min_modes:
        raise ValueError(
            f"Only {len(points)} peaks fall inside the configured period range; "
            f"at least {config.min_modes} are required."
        )
    return points
