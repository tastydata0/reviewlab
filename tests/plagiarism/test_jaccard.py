import pytest

from app.models.plagiarism import CodeSubmission
from app.services.plagiarism.jaccard import JaccardStrategy


@pytest.fixture
def strategy():
    return JaccardStrategy(n_gram_size=3, language="python")


@pytest.mark.asyncio
async def test_jaccard_identical_with_renamed_variables(strategy):
    # Коды отличаются только именами переменных и функций, структура одинакова
    code1 = "def calculate_sum(a, b):\n    return a + b"
    code2 = "def get_total(x, y):\n    return x + y"

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    # токены маскируются, структуры должны быть  идентичными
    assert results[0].score == 100.0


@pytest.mark.asyncio
async def test_jaccard_different_logic(strategy):
    code1 = "def sum(a, b): return a + b"
    code2 = "def loop(n):\n    while n > 0:\n        n -= 1"

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score < 100.0


@pytest.mark.asyncio
async def test_jaccard_reordered_functions(strategy):
    # пересечение множеств N-грамм будет очень высоким при перестановке функий
    code1 = "def a(): pass\ndef b(): pass"
    code2 = "def b(): pass\ndef a(): pass"

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score > 80.0
