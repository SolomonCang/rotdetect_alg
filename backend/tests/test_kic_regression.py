from __future__ import annotations

from pathlib import Path

from rotdetect.core.config import SearchConfig
from rotdetect.core.pipeline import run_pipeline_from_csv_bytes


def test_kic_fft_results_recover_trend_sequence() -> None:
    sample_path = Path(__file__).resolve(
    ).parents[2] / "examples" / "KIC004253413_FFT_results.dat"
    config = SearchConfig(
        period_min=0.49,
        period_max=0.72,
        delta_p_min=0.008,
        delta_p_max=0.016,
        delta_p_grid=0.00005,
        max_peaks=1200,
        peak_threshold_factor=3.0,
    )

    result = run_pipeline_from_csv_bytes(sample_path.read_bytes(), config)

    assert result.best_sequence is not None
    best = result.best_sequence
    assert best.n_modes == 19
    assert best.slope is not None and best.slope < 0
    assert 1200 <= best.delta_p_start * 86400 <= 1350
    assert 880 <= best.delta_p_mid * 86400 <= 1000
    assert 620 <= best.delta_p_end * 86400 <= 740
    assert best.delta_p_start > best.delta_p_mid > best.delta_p_end
    assert best.coverage > 0.85
    assert result.plots["scan"]["data"]
    assert result.plots["scan"]["data"][1]["name"] == "best candidate"
