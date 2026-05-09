from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PeriodRange:
    period_min: float
    period_max: float
    n_points: int


@dataclass(frozen=True)
class AmplitudePeriodCluster:
    rank: int
    label: str
    n_points: int
    period_min: float
    period_max: float
    amplitude_min: float
    amplitude_max: float
    amplitude_mean: float
    amplitude_median: float
    amplitude_fraction: float
    period_ranges: list[PeriodRange]


@dataclass(frozen=True)
class SpectrumPoint:
    frequency: float
    amplitude: float


@dataclass(frozen=True)
class FrequencyPeak:
    frequency: float
    amplitude: float
    snr: float | None = None
    frequency_error: float | None = None


@dataclass(frozen=True)
class PeriodPoint:
    period: float
    frequency: float
    amplitude: float
    snr: float | None
    sigma_period: float | None
    weight: float


@dataclass(frozen=True)
class PeriodSpacingSequence:
    delta_p: float
    delta_p_start: float
    delta_p_mid: float
    delta_p_end: float
    delta_p_error: float | None
    p0: float
    periods: list[float]
    amplitudes: list[float]
    radial_orders: list[int]
    residuals: list[float]
    slope: float | None
    n_modes: int
    coverage: float
    confidence_score: float
    amplitude_score: float
    amplitude_mean: float
    amplitude_median: float


@dataclass(frozen=True)
class AnalysisResult:
    input_summary: dict
    best_sequence: PeriodSpacingSequence | None
    candidates: list[PeriodSpacingSequence]
    amplitude_period_clusters: list[AmplitudePeriodCluster]
    plots: dict
    warnings: list[str]


@dataclass(frozen=True)
class TrendScanCandidate:
    delta_p_mid: float
    slope: float
    score: float
