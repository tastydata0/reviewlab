import pytest

from app.models.plagiarism import CodeSubmission
from app.services.plagiarism.copydetect_strategy import CopydetectStrategy


@pytest.fixture
def strategy():
    return CopydetectStrategy(
        language="python", noise_threshold=10, guarantee_threshold=10
    )


@pytest.mark.asyncio
async def test_copydetect_identical_logic(strategy):
    code1 = "def sum_nums(a, b):\n    return a + b"
    code2 = "def add(x, y):\n    return x + y"

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score > 80.0


@pytest.mark.asyncio
async def test_copydetect_different_logic(strategy):
    code1 = "def calc(a, b):\n    return a * b"
    code2 = "def do_loop(n):\n    while n > 0:\n        n -= 1"

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score < 50.0


@pytest.mark.asyncio
async def test_copydetect_multiple_submissions(strategy):
    submissions = [
        CodeSubmission(id="A", code="def A():\n    print('test')\n    return 1"),
        CodeSubmission(id="B", code="def B():\n    print('test')\n    return 1"),
        CodeSubmission(id="C", code="def C():\n    print('different')\n    return 2"),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 3

    # A и B должны быть очень похожи
    ab_match = next(r for r in results if set([r.source_id, r.target_id]) == {"A", "B"})
    assert ab_match.score > 80.0

    # A и C должны быть менее похожи
    ac_match = next(r for r in results if set([r.source_id, r.target_id]) == {"A", "C"})
    assert ac_match.score < ab_match.score
