import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.embedding import Embedding768, Embedding1536
from app.services.embedding import EmbeddingService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_embedding_service_create_and_read_768(mock_session):
    service = EmbeddingService(mock_session)
    test_text = "def calculate_sum(a, b):\n    return a + b"

    with MagicMock() as mock_embed:
        mock_embed.return_value = [0.1] * 768

        from unittest.mock import patch

        with patch(
            "app.services.embedding.embed_768", AsyncMock(return_value=[0.1] * 768)
        ):
            saved_embedding = await service.create_embedding_768(test_text)

            assert isinstance(saved_embedding, Embedding768)
            assert len(saved_embedding.embedding) == 768
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_embedding_service_create_and_read_1536(mock_session):
    service = EmbeddingService(mock_session)
    test_text = "class Test: pass"

    from unittest.mock import patch

    with patch(
        "app.services.embedding.embed_1536", AsyncMock(return_value=[0.2] * 1536)
    ):
        saved_embedding = await service.create_embedding_1536(test_text)

        assert isinstance(saved_embedding, Embedding1536)
        assert len(saved_embedding.embedding) == 1536
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
