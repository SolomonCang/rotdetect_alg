from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SearchConfigPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_min: float = Field(default=0.3, gt=0)
    period_max: float = Field(default=3.0, gt=0)
    delta_p_min: float = Field(default=0.005, gt=0)
    delta_p_max: float = Field(default=0.08, gt=0)
    delta_p_grid: float = Field(default=1e-4, gt=0)
    min_modes: int = Field(default=5, ge=2)
    top_k_candidates: int = Field(default=20, ge=1, le=100)
    tolerance_fraction: float = Field(default=0.10, gt=0, le=0.5)
    max_peaks: int = Field(default=200, ge=5, le=5000)
    peak_threshold_factor: float = Field(default=4.0, gt=0)
    snr_threshold: float = Field(default=4.0, gt=0)
