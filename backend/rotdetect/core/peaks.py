from __future__ import annotations

import pandas as pd

from .config import SearchConfig


def extract_peaks(df: pd.DataFrame, config: SearchConfig) -> pd.DataFrame:
    ordered = df.sort_values("frequency").reset_index(drop=True)
    amplitude = ordered["amplitude"]
    local_max = (amplitude > amplitude.shift(1)) & (amplitude > amplitude.shift(-1))

    noise_floor = float(amplitude.median())
    threshold = config.peak_threshold_factor * noise_floor
    peaks = ordered[local_max & (ordered["amplitude"] >= threshold)].copy()

    if peaks.empty:
        # Fall back to strongest samples so the API can return a useful warning/result
        # on synthetic or already sparse spectra without local maxima.
        peaks = ordered.nlargest(config.max_peaks, "amplitude").copy()

    return peaks.nlargest(config.max_peaks, "amplitude").sort_values("frequency").reset_index(drop=True)
