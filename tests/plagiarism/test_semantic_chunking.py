import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from worker.models.plagiarism import CodeSubmission
from worker.services.plagiarism.semantic import SemanticChunkingStrategy


@pytest.fixture
def mock_session():
    session = AsyncMock()
    
    # Мокаем execute так, чтобы он возвращал нужное значение coverage
    async def mock_execute(query, params=None):
        mock_result = MagicMock()
        # Имитируем поведение БД: возвращаем какое-то значение покрытия
        # Чтобы тесты проходили, нам нужно просто задать значения в зависимости от id 
        # или просто возвращать константы для разных тестов
        
        # Для простоты, в фикстуре возвращаем 0.0, а в самих тестах будем переопределять
        mock_result.scalar.return_value = 0.0
        return mock_result
        
    session.execute = AsyncMock(side_effect=mock_execute)
    return session


@pytest.fixture
def strategy(mock_session):
    return SemanticChunkingStrategy(language="python", session=mock_session)


@pytest.mark.asyncio
async def test_semantic_chunking_identical_logic(strategy, mock_session):
    # разные названия, но идентичная структура и смысл (Сложение и умножение)
    #  2 чанка (функции)
    code1 = """
def sum_nums(a, b):
    return a + b

def mult_nums(a, b):
    return a * b
"""
    code2 = """
def add(x, y):
    return x + y

def multiply(x, y):
    return x * y
"""

    submissions = [
        CodeSubmission(id=1, code=code1, user_id="u1"),
        CodeSubmission(id=2, code=code2, user_id="u2"),
    ]

    # Настраиваем mock для execute, чтобы он возвращал высокое сходство
    async def mock_execute(query, params=None):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0.95  # 95% покрытие
        return mock_result
    mock_session.execute.side_effect = mock_execute

    with patch('worker.services.plagiarism.semantic.EmbeddingService.get_or_create_embedding_1536', new_callable=AsyncMock):
        results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score > 30.0


@pytest.mark.asyncio
async def test_semantic_chunking_different_logic(strategy, mock_session):
    code1 = """
def do_something(a, b):
    return a - b
"""
    code2 = """
def process(n):
    while n > 0:
        print(n)
        n -= 1
"""

    submissions = [
        CodeSubmission(id=1, code=code1, user_id="u1"),
        CodeSubmission(id=2, code=code2, user_id="u2"),
    ]

    # Настраиваем mock для execute, чтобы он возвращал низкое сходство
    async def mock_execute(query, params=None):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0.10  # 10% покрытие
        return mock_result
    mock_session.execute.side_effect = mock_execute

    with patch('worker.services.plagiarism.semantic.EmbeddingService.get_or_create_embedding_1536', new_callable=AsyncMock):
        results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score < 35.0


@pytest.mark.asyncio
async def test_semantic_chunking_partial_plagiarism(strategy, mock_session):
    code1 = """
def f1(a): return a + 1
def f2(a): return a + 2
def f3(a): return a + 3
"""
    code2 = """
def f2_stolen(x): return x + 2
"""

    submissions = [
        CodeSubmission(id=1, code=code1, user_id="u1"),
        CodeSubmission(id=2, code=code2, user_id="u2"),
    ]

    # Для частичного плагиата:
    # avg(1->2) = низкое
    # avg(2->1) = почти 1.0
    async def mock_execute(query, params=None):
        mock_result = MagicMock()
        if params["a_id"] == "1" and params["b_id"] == "2":
            mock_result.scalar.return_value = 0.33
        elif params["a_id"] == "2" and params["b_id"] == "1":
            mock_result.scalar.return_value = 0.99
        else:
            mock_result.scalar.return_value = 0.0
        return mock_result
    mock_session.execute.side_effect = mock_execute

    with patch('worker.services.plagiarism.semantic.EmbeddingService.get_or_create_embedding_1536', new_callable=AsyncMock):
        results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score > 60.0
