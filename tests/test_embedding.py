import pytest
from app.utils.embedding import embed_768


@pytest.mark.asyncio
async def test_embed_returns_list_of_floats():
    test_text = "def hello_world(): print('hi')"

    # с дефолтной стратегией (HF)
    result = await embed_768(test_text)

    assert isinstance(result, list)
    assert len(result) == 768
    assert all(isinstance(x, float) for x in result)
