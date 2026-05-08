from __future__ import annotations

import io

import numpy as np
import pandas as pd

from rotdetect.core.config import SearchConfig
from rotdetect.core.pipeline import run_pipeline_from_csv_bytes


def make_synthetic_peak_csv(delta_p: float = 0.032) -> bytes:
    rng = np.random.default_rng(7)
    periods = 0.72 + np.arange(16) * delta_p + rng.normal(0, 0.00035, 16)
    frequencies = 1.0 / periods
    amplitudes = np.linspace(1.0, 0.35, len(periods))

    noise_frequency = rng.uniform(0.4, 3.0, 45)
    noise_amplitude = rng.uniform(0.02, 0.18, 45)

    df = pd.DataFrame(
        {
            "frequency": np.concatenate([frequencies, noise_frequency]),
            "amplitude": np.concatenate([amplitudes, noise_amplitude]),
        }
    )
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
    result = run_pipeline_from_csv_bytes(make_synthetic_peak_csv(expected_delta), config)

    assert result.best_sequence is not None
    assert result.best_sequence.n_modes >= 8
    assert abs(result.best_sequence.delta_p - expected_delta) < 0.001


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
    result = run_pipeline_from_csv_bytes(make_single_column_period_csv(expected_delta), config)

    assert result.input_summary["input_quantity"] == "period"
    assert result.best_sequence is not None
    assert abs(result.best_sequence.delta_p - expected_delta) < 0.001


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
    result = run_pipeline_from_csv_bytes(make_single_column_frequency_csv(expected_delta), config)

    assert result.input_summary["input_quantity"] == "frequency"
    assert result.best_sequence is not None
    assert abs(result.best_sequence.delta_p - expected_delta) < 0.001
