from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchConfig:
    period_min: float = 0.3
    period_max: float = 3.0
    delta_p_min: float = 0.005
    delta_p_max: float = 0.08
    delta_p_grid: float = 1e-4
    min_modes: int = 5
    top_k_candidates: int = 20
    tolerance_fraction: float = 0.10
    max_peaks: int = 200
    peak_threshold_factor: float = 4.0
    snr_threshold: float = 4.0
    random_seed: int = 42

    def validate(self) -> None:
        if self.period_min <= 0 or self.period_max <= self.period_min:
            raise ValueError("period range must satisfy 0 < period_min < period_max")
        if self.delta_p_min <= 0 or self.delta_p_max <= self.delta_p_min:
            raise ValueError("delta_p range must satisfy 0 < delta_p_min < delta_p_max")
        if self.delta_p_grid <= 0:
            raise ValueError("delta_p_grid must be positive")
        if self.min_modes < 2:
            raise ValueError("min_modes must be at least 2")
        if self.max_peaks < self.min_modes:
            raise ValueError("max_peaks must be greater than or equal to min_modes")
