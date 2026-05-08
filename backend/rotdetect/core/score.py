from __future__ import annotations

from .data import PeriodSpacingSequence


def rank_candidates(candidates: list[PeriodSpacingSequence]) -> list[PeriodSpacingSequence]:
    return sorted(
        candidates,
        key=lambda item: (item.confidence_score, item.n_modes, item.coverage),
        reverse=True,
    )
