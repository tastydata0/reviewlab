import math


def calculate_stats(scores: list[float]) -> tuple[float, float]:
    """
    Вычисляет среднее значение и стандартное отклонение для списка баллов.
    """
    if not scores:
        return 0.0, 0.0

    n = len(scores)
    if n < 2:
        return sum(scores) / n, 0.0

    mean = sum(scores) / n
    variance = sum((x - mean) ** 2 for x in scores) / n
    std_dev = math.sqrt(variance)
    
    return mean, std_dev


def normalize_zscore_value(
    score: float, mean: float, std_dev: float, max_z: float = 1.2
) -> float:
    """
    Нормализует одно значение на основе переданных коэффициентов.
    """
    if std_dev == 0:
        return 0.0

    z = (score - mean) / std_dev
    # Масштабируем: Z=0 -> 0%, Z=max_z -> 100%
    perc = max(0.0, min(100.0, z * (100.0 / max_z)))
    return perc


def normalize_zscore(scores: list[float], max_z: float = 1.2) -> list[float]:
    """
    Legacy функция для нормализации списка (использует calculate_stats внутри).
    """
    mean, std_dev = calculate_stats(scores)
    return [normalize_zscore_value(x, mean, std_dev, max_z) for x in scores]
