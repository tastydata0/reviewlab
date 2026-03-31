def normalize_baseline(score: float, baseline: float) -> float:
    if score <= baseline:
        return 0.0
    if baseline >= 100.0:
        return 0.0
    return min(100.0, (score - baseline) / (100.0 - baseline) * 100.0)
