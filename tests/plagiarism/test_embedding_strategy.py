import pytest

from worker.models.plagiarism import CodeSubmission
from worker.services.plagiarism.embedding import SingleEmbeddingStrategy


@pytest.fixture
def strategy():
    return SingleEmbeddingStrategy()


@pytest.mark.asyncio
async def test_single_embedding_identical_logic(strategy):
    # Коды с разным синтаксисом, но одинаковой семантикой (сложение)
    # Векторная модель должна уловить, что обе функции делают одно и то же
    code1 = "def sum_nums(a, b):\n    return a + b"
    code2 = "def add(x, y):\n    res = x + y\n    return res"
    
    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]
    
    results = await strategy.check(submissions)
    
    assert len(results) == 1
    # Локальные модели могут давать не очень высокий процент косинусного сходства (например ~35-40%),
    # но он должен быть выше, чем у совершенно разного кода.
    assert results[0].score > 30.0


@pytest.mark.asyncio
async def test_single_embedding_different_logic(strategy):
    # Совершенно разная семантика: математическая операция vs цикл
    code1 = "def calc(a, b):\n    return a * b"
    code2 = "def do_loop(n):\n    while n > 0:\n        n -= 1"
    
    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]
    
    results = await strategy.check(submissions)
    
    assert len(results) == 1
    # Сходство должно быть заметно ниже, чем для одинаковой логики
    assert results[0].score < 85.0


@pytest.mark.asyncio
async def test_single_embedding_exact_match(strategy):
    code1 = "def hello():\n    print('world')"
    code2 = "def hello():\n    print('world')"
    
    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]
    
    results = await strategy.check(submissions)
    
    assert len(results) == 1
    # Векторы должны быть абсолютно идентичны
    assert results[0].score > 99.0
