import math
from typing import List


def normalize_zscore(scores: List[float], max_z: float = 3.0) -> List[float]:
    if not scores:
        return []

    n = len(scores)
    if n < 2:
        return [0.0] * n

    mean = sum(scores) / n
    variance = sum((x - mean) ** 2 for x in scores) / n
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return [0.0] * n

    normalized = []
    for x in scores:
        z = (x - mean) / std_dev
        perc = max(0.0, min(100.0, z * (100.0 / max_z)))
        normalized.append(perc)

    return normalized
