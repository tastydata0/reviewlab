import pytest

from app.models.plagiarism import CodeSubmission
from app.services.plagiarism.levenshtein import LevenshteinStrategy


@pytest.fixture
def strategy():
    return LevenshteinStrategy()


@pytest.mark.asyncio
async def test_levenshtein_exact_match_with_different_whitespaces(strategy):
    code1 = "def   main():\n    print('Hello')"
    code2 = "def main(): print('Hello')"

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score == 100.0


@pytest.mark.asyncio
async def test_levenshtein_different_codes(strategy):
    code1 = "def sum(a, b): return a + b"
    code2 = "def multiply(x, y): return x * y"

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score < 100.0
    assert results[0].score > 0.0


@pytest.mark.asyncio
async def test_levenshtein_multiple_submissions(strategy):
    submissions = [
        CodeSubmission(id="A", code="def A(): pass"),
        CodeSubmission(id="B", code="def B(): pass"),
        CodeSubmission(id="C", code="def C(): pass"),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 3

    # убеждаемся, что все комбинации присутствуют
    pairs = {(r.source_id, r.target_id) for r in results}
    assert pairs == {("A", "B"), ("A", "C"), ("B", "C")}
