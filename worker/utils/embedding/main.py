from enum import Enum
from cashews import cache

if not cache.is_setup():
    cache.setup("mem://")


from .huggingface import _embed_huggingface
from .local import _embed_local
from .openai import _embed_openai


class EmbeddingStrategy768(str, Enum):
    HF = "huggingface"
    LOCAL = "local"


class EmbeddingStrategy1536(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"


@cache(ttl="5m")
async def embed_768(
    text: str, strategy: EmbeddingStrategy768 = EmbeddingStrategy768.HF
) -> list[float]:
    # основная точка входа для получения эмбеддинга размера 768
    if strategy == EmbeddingStrategy768.HF:
        return await _embed_huggingface(text)
    elif strategy == EmbeddingStrategy768.LOCAL:
        return await _embed_local(text)
    else:
        raise ValueError(f"Неизвестная стратегия: {strategy}")


@cache(ttl="5m")
async def embed_1536(
    text: str, strategy: EmbeddingStrategy1536 = EmbeddingStrategy1536.OPENAI
) -> list[float]:
    # основная точка входа для получения эмбеддинга размера 1536
    if strategy == EmbeddingStrategy1536.OPENAI:
        return await _embed_openai(text)
    else:
        raise ValueError(f"Неизвестная стратегия: {strategy}")
