from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

from rotdetect.core.config import SearchConfig
from rotdetect.core.pipeline import run_pipeline_from_csv_bytes
from rotdetect.core.preprocess import read_frequency_table


def make_synthetic_peak_csv(delta_p: float = 0.032) -> bytes:
    rng = np.random.default_rng(7)
    periods = 0.72 + np.arange(16) * delta_p + rng.normal(0, 0.00035, 16)
    frequencies = 1.0 / periods
    amplitudes = np.linspace(1.0, 0.35, len(periods))

    noise_frequency = rng.uniform(0.4, 3.0, 45)
    noise_amplitude = rng.uniform(0.02, 0.18, 45)

    df = pd.DataFrame({
        "frequency":
        np.concatenate([frequencies, noise_frequency]),
        "amplitude":
        np.concatenate([amplitudes, noise_amplitude]),
    })
    out = io.StringIO()
    df.to_csv(out, index=False)
    return out.getvalue().encode()


def make_single_column_period_csv(delta_p: float = 0.032) -> bytes:
    rng = np.random.default_rng(11)
    periods = 0.72 + np.arange(16) * delta_p + rng.normal(0, 0.00025, 16)
    out = io.StringIO()
    pd.DataFrame({"period": periods}).to_csv(out, index=False)
    return out.getvalue().encode()


def make_single_column_frequency_csv(delta_p: float = 0.032) -> bytes:
    rng = np.random.default_rng(13)
    periods = 0.72 + np.arange(16) * delta_p + rng.normal(0, 0.00025, 16)
    out = io.StringIO()
    pd.DataFrame({"frequency": 1.0 / periods}).to_csv(out, index=False)
    return out.getvalue().encode()


def make_headerless_frequency_amplitude_dat(delta_p: float = 0.032) -> bytes:
    rng = np.random.default_rng(17)
    periods = 0.72 + np.arange(16) * delta_p + rng.normal(0, 0.00025, 16)
    frequencies = 1.0 / periods
    amplitudes = np.linspace(1.0, 0.35, len(periods))
    rows = [
        f"{freq:.10f} {amp:.10f}" for freq, amp in zip(frequencies, amplitudes)
    ]
    return ("\n".join(rows) + "\n").encode()


def make_period04_frequency_list_dat(delta_p: float = 0.032) -> bytes:
    rng = np.random.default_rng(23)
    periods = 0.72 + np.arange(16) * delta_p + rng.normal(0, 0.00025, 16)
    frequencies = 1.0 / periods
    amplitudes = np.linspace(1.0, 0.35, len(periods))
    phases = rng.uniform(0, 2 * np.pi, len(periods))
    snr = np.linspace(20.0, 8.0, len(periods))
    rows = ["# freq, ampl, phase, S/N"]
    rows.extend(f"{freq:.10f} {amp:.10f} {phase:.10f} {snr_value:.10f}"
                for freq, amp, phase, snr_value in zip(frequencies, amplitudes,
                                                       phases, snr))
    return ("\n".join(rows) + "\n").encode()


def make_trend_period_peak_csv(p0: float = 0.51,
                               delta0: float = 0.015,
                               slope_per_mode: float = -0.00032,
                               n_modes: int = 20) -> bytes:
    rng = np.random.default_rng(19)

    periods = [p0]
    current_delta = delta0
    for _ in range(1, n_modes):
        next_period = periods[-1] + current_delta + rng.normal(0.0, 0.00008)
        periods.append(next_period)
        current_delta = max(0.006, current_delta + slope_per_mode)

    periods_arr = np.asarray(periods, dtype=float)
    frequencies = 1.0 / periods_arr
    amplitudes = np.linspace(1.0, 0.45, len(periods_arr))

    noise_frequency = rng.uniform(1.2, 3.0, 35)
    noise_amplitude = rng.uniform(0.02, 0.12, 35)
    df = pd.DataFrame({
        "frequency":
        np.concatenate([frequencies, noise_frequency]),
        "amplitude":
        np.concatenate([amplitudes, noise_amplitude]),
    })

    out = io.StringIO()
    df.to_csv(out, index=False)
    return out.getvalue().encode()


def test_pipeline_recovers_synthetic_delta_p() -> None:
    expected_delta = 0.032
    config = SearchConfig(
        period_min=0.5,
        period_max=1.4,
        delta_p_min=0.02,
        delta_p_max=0.045,
        delta_p_grid=0.0002,
        min_modes=6,
        max_peaks=120,
    )
    result = run_pipeline_from_csv_bytes(
        make_synthetic_peak_csv(expected_delta), config)

    assert result.best_sequence is not None
    assert result.best_sequence.n_modes >= 8
    assert abs(result.best_sequence.delta_p - expected_delta) < 0.001
    assert abs(result.best_sequence.delta_p_mid - expected_delta) < 0.001
    assert "spectrum" in result.plots
    assert len(result.plots["spectrum"]["data"][0]
               ["x"]) == result.input_summary["n_rows"]


def test_pipeline_accepts_single_period_column() -> None:
    expected_delta = 0.032
    config = SearchConfig(
        period_min=0.5,
        period_max=1.4,
        delta_p_min=0.02,
        delta_p_max=0.045,
        delta_p_grid=0.0002,
        min_modes=6,
    )
    result = run_pipeline_from_csv_bytes(
        make_single_column_period_csv(expected_delta), config)

    assert result.input_summary["input_quantity"] == "period"
    assert result.input_summary["input_period_min"] <= result.input_summary[
        "period_min"]
    assert result.input_summary["input_period_max"] >= result.input_summary[
        "period_max"]
    assert result.best_sequence is not None
    assert abs(result.best_sequence.delta_p - expected_delta) < 0.001
    assert result.best_sequence.delta_p_start > 0


def test_pipeline_accepts_single_frequency_column() -> None:
    expected_delta = 0.032
    config = SearchConfig(
        period_min=0.5,
        period_max=1.4,
        delta_p_min=0.02,
        delta_p_max=0.045,
        delta_p_grid=0.0002,
        min_modes=6,
    )
    result = run_pipeline_from_csv_bytes(
        make_single_column_frequency_csv(expected_delta), config)

    assert result.input_summary["input_quantity"] == "frequency"
    assert result.input_summary["input_period_min"] <= result.input_summary[
        "period_min"]
    assert result.input_summary["input_period_max"] >= result.input_summary[
        "period_max"]
    assert result.best_sequence is not None
    assert abs(result.best_sequence.delta_p - expected_delta) < 0.001
    assert result.best_sequence.delta_p_end > 0


def test_pipeline_accepts_headerless_frequency_amplitude_dat() -> None:
    expected_delta = 0.032
    config = SearchConfig(
        period_min=0.5,
        period_max=1.4,
        delta_p_min=0.02,
        delta_p_max=0.045,
        delta_p_grid=0.0002,
        min_modes=6,
    )
    result = run_pipeline_from_csv_bytes(
        make_headerless_frequency_amplitude_dat(expected_delta), config)

    assert result.input_summary["input_quantity"] == "frequency"
    assert result.best_sequence is not None
    assert abs(result.best_sequence.delta_p - expected_delta) < 0.001
    assert result.best_sequence.delta_p_mid > 0


def test_pipeline_reports_amplitude_priority_and_clusters() -> None:
    config = SearchConfig(
        period_min=0.5,
        period_max=1.4,
        delta_p_min=0.02,
        delta_p_max=0.045,
        delta_p_grid=0.0002,
        min_modes=6,
        max_peaks=120,
    )
    result = run_pipeline_from_csv_bytes(make_synthetic_peak_csv(), config)

    assert result.best_sequence is not None
    assert result.best_sequence.amplitude_score > 0.0
    assert len(result.best_sequence.amplitudes) == result.best_sequence.n_modes
    assert result.best_sequence.amplitude_median > 0.0
    assert result.amplitude_period_clusters
    assert result.amplitude_period_clusters[0].label == "high"
    assert result.amplitude_period_clusters[0].period_ranges


def test_pipeline_uses_optional_spectrum_background_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    background_path = repo_root / "backend" / "tests" / "_tmp_background_spectrum.dat"
    frequencies = np.linspace(0.8, 2.4, 31)
    amplitudes = np.linspace(0.1, 0.3, 31)
    rows = ["# freq, amplitude"]
    rows.extend(f"{frequency:.8f} {amplitude:.8f}"
                for frequency, amplitude in zip(frequencies, amplitudes))

    try:
        background_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        config = SearchConfig(
            period_min=0.5,
            period_max=1.4,
            delta_p_min=0.02,
            delta_p_max=0.045,
            delta_p_grid=0.0002,
            min_modes=6,
            max_peaks=120,
            spectrum_background_path=
            "backend/tests/_tmp_background_spectrum.dat",
        )

        result = run_pipeline_from_csv_bytes(make_synthetic_peak_csv(), config)
    finally:
        background_path.unlink(missing_ok=True)

    assert result.best_sequence is not None
    assert result.input_summary["n_rows"] != 31
    assert len(result.plots["spectrum"]["data"][0]["x"]) == 31


def test_period04_headerless_columns_map_phase_and_snr() -> None:
    df = read_frequency_table(make_period04_frequency_list_dat())

    assert list(df.columns) == ["frequency", "amplitude", "phase", "snr"]
    assert df["phase"].between(0, 2 * np.pi).all()
    assert df["snr"].min() >= 8.0


def test_comment_header_dat_accepts_explicit_column_mapping() -> None:
    config = SearchConfig(frequency_column="col1", amplitude_column="col2")
    df = read_frequency_table(make_period04_frequency_list_dat(), config)

    assert df["frequency"].min() > 0
    assert df["amplitude"].min() > 0
    assert len(df) == 16


def test_pipeline_handles_trend_spacing_without_duplicate_orders() -> None:
    config = SearchConfig(
        period_min=0.49,
        period_max=0.75,
        delta_p_min=0.006,
        delta_p_max=0.018,
        delta_p_grid=0.0001,
        min_modes=8,
        max_peaks=160,
    )
    result = run_pipeline_from_csv_bytes(make_trend_period_peak_csv(), config)

    assert result.best_sequence is not None
    assert result.best_sequence.n_modes >= 10
    assert len(set(result.best_sequence.radial_orders)) == len(
        result.best_sequence.radial_orders)
    assert result.best_sequence.delta_p_start > result.best_sequence.delta_p_end
