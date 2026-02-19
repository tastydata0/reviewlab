import numpy as np
import pytest
import pytest_asyncio

from app.models.embedding import Embedding768
from app.services.embedding import EmbeddingService
from app.storage.postgres import async_session_maker, create_db_and_tables


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    await create_db_and_tables()


@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


@pytest.mark.asyncio
async def test_embedding_service_create_and_read_768(db_session):
    service = EmbeddingService(db_session)
    test_text = "def calculate_sum(a, b):\n    return a + b"

    saved_embedding = await service.create_embedding_768(test_text)

    assert saved_embedding.id is not None
    assert isinstance(saved_embedding.embedding, (list, np.ndarray))
    assert len(saved_embedding.embedding) == 768

    # очищаем локальный кэш сессии, чтобы гарантировать, что мы читаем из базы
    db_session.expunge_all()

    fetched_embedding = await db_session.get(Embedding768, saved_embedding.id)

    assert fetched_embedding is not None
    assert fetched_embedding.id == saved_embedding.id
    # pgvector возвращает ndarray или список, проверим размерность
    assert len(fetched_embedding.embedding) == 768

    assert np.allclose(
        fetched_embedding.embedding, saved_embedding.embedding, atol=1e-6
    )
