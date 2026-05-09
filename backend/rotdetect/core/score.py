from __future__ import annotations

from .data import PeriodSpacingSequence


def rank_candidates(
        candidates: list[PeriodSpacingSequence]
) -> list[PeriodSpacingSequence]:

    def ranking_key(
            item: PeriodSpacingSequence) -> tuple[float, float, int, float]:
        slope = item.slope if item.slope is not None else 0.0
        positive_penalty = 0.05 * min(1.0, max(0.0, slope) / 0.003)
        negative_bonus = 0.006 * min(1.0, max(0.0, -slope) / 0.003)
        magnitude_penalty = 0.04 * min(1.0, abs(slope) / 0.003)
        amplitude_bonus = 0.08 * max(0.0, min(1.0, item.amplitude_score))
        adjusted_confidence = (item.confidence_score + amplitude_bonus -
                               positive_penalty - magnitude_penalty +
                               negative_bonus)
        return (adjusted_confidence, item.amplitude_score, item.n_modes,
                item.coverage)

    return sorted(
        candidates,
        key=ranking_key,
        reverse=True,
    )
