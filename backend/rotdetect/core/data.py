from __future__ import annotations

from dataclasses import dataclass


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
    delta_p_error: float | None
    p0: float
    periods: list[float]
    radial_orders: list[int]
    residuals: list[float]
    slope: float | None
    n_modes: int
    coverage: float
    confidence_score: float


@dataclass(frozen=True)
class AnalysisResult:
    input_summary: dict
    best_sequence: PeriodSpacingSequence | None
    candidates: list[PeriodSpacingSequence]
    plots: dict
    warnings: list[str]
