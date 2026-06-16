import pytest
import respx
from httpx import Response
from worker.utils.embedding import embed_768, embed_1536, EmbeddingStrategy1536
from worker.utils.embedding.huggingface import API_URL
from app.settings import SETTINGS


@pytest.mark.asyncio
@respx.mock
async def test_embed_returns_list_of_floats():
    test_text = "def hello_world(): print('hi')"
    mock_embedding = [0.1] * 768
    
    respx.post(API_URL).mock(
        return_value=Response(200, json=mock_embedding)
    )

    # с дефолтной стратегией (HF)
    result = await embed_768(test_text)

    assert isinstance(result, list)
    assert len(result) == 768
    assert all(isinstance(x, float) for x in result)
    assert result == mock_embedding


@pytest.mark.asyncio
@respx.mock
async def test_embed_1536_openai():
    test_text = "def hello_world(): print('hi')"
    mock_embedding = [0.1] * 1536
    
    # OpenAI client appends /embeddings to base_url
    openai_url = f"{SETTINGS.OPENAI_API_BASE_URL}/embeddings"
    
    # Мокаем ответ OpenAI
    respx.post(openai_url).mock(
        return_value=Response(
            200, 
            json={
                "data": [
                    {"embedding": mock_embedding}
                ]
            }
        )
    )

    result = await embed_1536(test_text, strategy=EmbeddingStrategy1536.OPENAI)

    assert isinstance(result, list)
    assert len(result) == 1536
    assert result == mock_embedding
