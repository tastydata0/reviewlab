from enum import Enum

from .huggingface import _embed_huggingface
from .local import _embed_local


class EmbeddingStrategy(str, Enum):
    HF = "huggingface"
    LOCAL = "local"


async def embed(
    text: str, strategy: EmbeddingStrategy = EmbeddingStrategy.HF
) -> list[float]:
    # основная точка входа для получения эмбеддинга
    if strategy == EmbeddingStrategy.HF:
        return await _embed_huggingface(text)
    elif strategy == EmbeddingStrategy.LOCAL:
        return await _embed_local(text)
    else:
        raise ValueError(f"Неизвестная стратегия: {strategy}")
