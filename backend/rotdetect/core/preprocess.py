from __future__ import annotations

import io
from typing import Any

import numpy as np
import pandas as pd

from .config import SearchConfig
from .data import FrequencyPeak, PeriodPoint
from .peaks import extract_peaks


def _read_table(csv_bytes: bytes,
                config: SearchConfig | None = None) -> pd.DataFrame:
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    first_line = _first_nonempty_line(text)
    if first_line is not None and first_line.startswith("#"):
        return _read_headerless_table(text, config)

    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
    except Exception as exc:  # pragma: no cover - pandas message varies
        raise ValueError(f"Could not read input table: {exc}") from exc

    df.columns = [str(column).strip().lower() for column in df.columns]
    df = _apply_column_mapping(df, config)
    normalized_columns = [str(column).strip().lower() for column in df.columns]
    if "frequency" in normalized_columns or "period" in normalized_columns:
        df.columns = normalized_columns
        return df

    return _read_headerless_table(text, config)


def _read_headerless_table(text: str,
                           config: SearchConfig | None = None) -> pd.DataFrame:
    # Fallback for whitespace/tab/comma separated files without headers,
    # e.g. FFT output where col1=frequency [1/day], col2=amplitude.
    try:
        headerless = pd.read_csv(
            io.StringIO(text),
            sep=r"[\s,;]+",
            engine="python",
            header=None,
            comment="#",
        )
    except Exception as exc:  # pragma: no cover - pandas message varies
        raise ValueError(f"Could not read input table: {exc}") from exc

    if headerless.empty or headerless.shape[1] < 1:
        raise ValueError("Input table is empty or malformed.")

    inferred_columns = _infer_headerless_columns(text, headerless.shape[1])
    use_columns = inferred_columns[:headerless.shape[1]]
    headerless = headerless.iloc[:, :len(use_columns)].copy()
    headerless.columns = use_columns
    headerless = _apply_column_mapping(headerless, config)
    return headerless


def _first_nonempty_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _apply_column_mapping(df: pd.DataFrame,
                          config: SearchConfig | None) -> pd.DataFrame:
    if config is None:
        return df

    rename_map: dict[str, str] = {}
    if config.frequency_column:
        rename_map[_resolve_column_name(df,
                                        config.frequency_column)] = "frequency"
    if config.amplitude_column:
        rename_map[_resolve_column_name(df,
                                        config.amplitude_column)] = "amplitude"
    if not rename_map:
        return df

    result = df.copy()
    result = result.rename(columns=rename_map)
    return result


def _resolve_column_name(df: pd.DataFrame, requested: str) -> str:
    normalized_requested = str(requested).strip().lower()
    columns = [str(column).strip().lower() for column in df.columns]
    if normalized_requested in columns:
        return str(df.columns[columns.index(normalized_requested)])

    for prefix in ("col", "column_"):
        if normalized_requested.startswith(prefix):
            suffix = normalized_requested.removeprefix(prefix)
            if suffix.isdigit():
                index = int(suffix) - 1
                if 0 <= index < len(df.columns):
                    return str(df.columns[index])

    if normalized_requested.isdigit():
        index = int(normalized_requested) - 1
        if 0 <= index < len(df.columns):
            return str(df.columns[index])

    available = ", ".join(str(column) for column in df.columns)
    raise ValueError(
        f"Configured column '{requested}' was not found. Available columns: {available}"
    )


def _infer_headerless_columns(text: str, column_count: int) -> list[str]:
    header_tokens: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("#"):
            break
        header_tokens = [
            token.strip().lower()
            for token in stripped.lstrip("#").replace(",", " ").split()
        ]
        if header_tokens:
            break

    if "phase" in header_tokens and any(token in {"s/n", "snr"}
                                        for token in header_tokens):
        return ["frequency", "amplitude", "phase", "snr"][:column_count]

    return ["frequency", "amplitude", "snr", "frequency_error"][:column_count]


def read_frequency_table(csv_bytes: bytes,
                         config: SearchConfig | None = None) -> pd.DataFrame:
    df = _read_table(csv_bytes, config)
    df.columns = [str(column).strip().lower() for column in df.columns]
    if "frequency" not in df.columns and "period" not in df.columns:
        raise ValueError(
            "Input table must contain either a frequency column or a period column."
        )

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

    for optional in ("phase", "snr", "frequency_error"):
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


def table_to_peaks(
        df: pd.DataFrame,
        config: SearchConfig) -> tuple[list[FrequencyPeak], list[str]]:
    warnings: list[str] = []
    amplitude_missing = bool(df.attrs.get("amplitude_missing", False))
    looks_like_peak_list = amplitude_missing or "snr" in df.columns or len(
        df) <= int(config.max_peaks * 1.5)

    if looks_like_peak_list:
        peak_df = df.copy()
        if amplitude_missing:
            warnings.append(
                "No amplitude column found; input was treated as an already extracted peak list."
            )
        if "snr" in peak_df.columns:
            before = len(peak_df)
            peak_df = peak_df[(peak_df["snr"].isna()) |
                              (peak_df["snr"] >= config.snr_threshold)]
            if len(peak_df) < before:
                warnings.append(
                    f"Removed {before - len(peak_df)} peaks below S/N threshold."
                )
        peak_df = peak_df.sort_values("amplitude",
                                      ascending=False).head(config.max_peaks)
    else:
        peak_df = extract_peaks(df, config)
        warnings.append(
            "Input treated as full spectrum; simple local-maximum peak extraction was used."
        )

    peaks = []
    for row in peak_df.to_dict(orient="records"):
        snr = _optional_float(row, "snr")
        frequency_error = _optional_float(row, "frequency_error")
        peaks.append(
            FrequencyPeak(
                frequency=float(row["frequency"]),
                amplitude=float(row["amplitude"]),
                snr=snr,
                frequency_error=frequency_error,
            ))
    if len(peaks) < config.min_modes:
        raise ValueError(
            f"Only {len(peaks)} usable peaks remain; at least {config.min_modes} are required."
        )
    return peaks, warnings


def _optional_float(row: Any, key: str) -> float | None:
    value = row.get(key)
    if value is None or pd.isna(value):
        return None
    return float(value)


def peaks_to_period_points(peaks: list[FrequencyPeak],
                           config: SearchConfig) -> list[PeriodPoint]:
    amplitudes = np.asarray([max(peak.amplitude, 0.0) for peak in peaks],
                            dtype=float)
    amp_scale = float(np.nanmedian(amplitudes[amplitudes > 0])) if np.any(
        amplitudes > 0) else 1.0
    points: list[PeriodPoint] = []

    for peak in peaks:
        period = 1.0 / peak.frequency
        if not (config.period_min <= period <= config.period_max):
            continue

        sigma_period = None
        if peak.frequency_error is not None and peak.frequency_error > 0:
            sigma_period = peak.frequency_error / (peak.frequency *
                                                   peak.frequency)

        amp_weight = np.sqrt(max(peak.amplitude, 0.0) /
                             amp_scale) if amp_scale > 0 else 1.0
        snr_weight = np.sqrt(
            peak.snr /
            config.snr_threshold) if peak.snr and peak.snr > 0 else 1.0
        weight = float(np.clip(amp_weight * snr_weight, 0.2, 5.0))

        points.append(
            PeriodPoint(
                period=float(period),
                frequency=float(peak.frequency),
                amplitude=float(peak.amplitude),
                snr=peak.snr,
                sigma_period=sigma_period,
                weight=weight,
            ))

    points.sort(key=lambda point: point.period)
    if len(points) < config.min_modes:
        raise ValueError(
            f"Only {len(points)} peaks fall inside the configured period range; "
            f"at least {config.min_modes} are required.")
    return points
