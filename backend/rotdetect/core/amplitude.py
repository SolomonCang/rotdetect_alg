from __future__ import annotations

import numpy as np

from .data import AmplitudePeriodCluster, PeriodPoint, PeriodRange


def build_amplitude_period_clusters(
    points: list[PeriodPoint],
    max_clusters: int = 3,
) -> list[AmplitudePeriodCluster]:
    if not points:
        return []

    periods = np.asarray([point.period for point in points], dtype=float)
    amplitudes = np.asarray([max(point.amplitude, 0.0) for point in points],
                            dtype=float)
    finite_mask = np.isfinite(periods) & np.isfinite(amplitudes)
    periods = periods[finite_mask]
    amplitudes = amplitudes[finite_mask]
    if periods.size == 0:
        return []

    if np.unique(amplitudes).size < 2:
        labels = np.zeros(amplitudes.size, dtype=int)
        cluster_count = 1
    else:
        cluster_count = min(max_clusters, periods.size,
                            np.unique(amplitudes).size)
        labels = _kmeans_1d(np.log1p(amplitudes), cluster_count)

    total_amplitude = float(np.sum(amplitudes))
    cluster_summaries = []
    for raw_label in range(cluster_count):
        mask = labels == raw_label
        if not np.any(mask):
            continue
        cluster_amplitudes = amplitudes[mask]
        cluster_periods = periods[mask]
        cluster_summaries.append({
            "periods": cluster_periods,
            "amplitudes": cluster_amplitudes,
            "mean": float(np.mean(cluster_amplitudes)),
        })

    cluster_summaries.sort(key=lambda item: item["mean"], reverse=True)
    names = ["high", "medium", "low"]
    clusters: list[AmplitudePeriodCluster] = []
    for index, summary in enumerate(cluster_summaries):
        cluster_periods = np.asarray(summary["periods"], dtype=float)
        cluster_amplitudes = np.asarray(summary["amplitudes"], dtype=float)
        label = names[index] if index < len(names) else f"level_{index + 1}"
        clusters.append(
            AmplitudePeriodCluster(
                rank=index + 1,
                label=label,
                n_points=int(cluster_periods.size),
                period_min=float(np.min(cluster_periods)),
                period_max=float(np.max(cluster_periods)),
                amplitude_min=float(np.min(cluster_amplitudes)),
                amplitude_max=float(np.max(cluster_amplitudes)),
                amplitude_mean=float(np.mean(cluster_amplitudes)),
                amplitude_median=float(np.median(cluster_amplitudes)),
                amplitude_fraction=(float(np.sum(cluster_amplitudes)) /
                                    total_amplitude
                                    if total_amplitude > 0 else 0.0),
                period_ranges=_split_period_ranges(cluster_periods),
            ))
    return clusters


def _kmeans_1d(values: np.ndarray, cluster_count: int) -> np.ndarray:
    centroids = np.percentile(values,
                              np.linspace(0.0, 100.0, cluster_count + 2)[1:-1])
    labels = np.zeros(values.size, dtype=int)

    for _ in range(40):
        distances = np.abs(values[:, None] - centroids[None, :])
        next_labels = np.argmin(distances, axis=1)
        next_centroids = centroids.copy()
        for index in range(cluster_count):
            member_values = values[next_labels == index]
            if member_values.size:
                next_centroids[index] = float(np.mean(member_values))
        if np.array_equal(labels, next_labels) and np.allclose(
                centroids, next_centroids):
            break
        labels = next_labels
        centroids = next_centroids

    return labels


def _split_period_ranges(periods: np.ndarray) -> list[PeriodRange]:
    sorted_periods = np.sort(periods)
    if sorted_periods.size == 0:
        return []
    if sorted_periods.size == 1:
        value = float(sorted_periods[0])
        return [PeriodRange(period_min=value, period_max=value, n_points=1)]

    gaps = np.diff(sorted_periods)
    positive_gaps = gaps[gaps > 0]
    if positive_gaps.size == 0:
        threshold = 0.0
    else:
        threshold = max(float(np.median(positive_gaps) * 2.5),
                        float(np.percentile(positive_gaps, 75)))

    ranges: list[PeriodRange] = []
    start = 0
    for index, gap in enumerate(gaps, start=1):
        if gap > threshold:
            ranges.append(_make_period_range(sorted_periods[start:index]))
            start = index
    ranges.append(_make_period_range(sorted_periods[start:]))
    return ranges


def _make_period_range(periods: np.ndarray) -> PeriodRange:
    return PeriodRange(
        period_min=float(np.min(periods)),
        period_max=float(np.max(periods)),
        n_points=int(periods.size),
    )
