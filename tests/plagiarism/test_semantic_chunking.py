import pytest

from app.models.plagiarism import CodeSubmission
from app.services.plagiarism.semantic import SemanticChunkingStrategy


@pytest.fixture
def strategy():
    return SemanticChunkingStrategy(language="python")


@pytest.mark.asyncio
async def test_semantic_chunking_identical_logic(strategy):
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
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score > 30.0


@pytest.mark.asyncio
async def test_semantic_chunking_different_logic(strategy):
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
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score < 35.0


@pytest.mark.asyncio
async def test_semantic_chunking_partial_plagiarism(strategy):
    code1 = """
def f1(a): return a + 1
def f2(a): return a + 2
def f3(a): return a + 3
"""
    code2 = """
def f2_stolen(x): return x + 2
"""

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    # благодаря тому, что мы берем max(avg(A->B), avg(B->A)),
    # avg(B->A) будет равен почти 100% (весь код B содержится в коде A).
    # таким образом мы успешно ловим частичный плагиат.
    assert results[0].score > 60.0
