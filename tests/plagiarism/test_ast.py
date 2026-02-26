import pytest

from app.models.plagiarism import CodeSubmission
from app.services.plagiarism.ast import AstLevenshteinStrategy


@pytest.fixture
def strategy():
    return AstLevenshteinStrategy(language="python")


@pytest.mark.asyncio
async def test_ast_identical_structure_different_names(strategy):
    code1 = """
def calculate(a, b):
    if a > 0:
        return a + b
    return 0
"""
    code2 = """
def get_result(x, y):
    if x > 0:
        return x + y
    return 0
"""

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score == 100.0


@pytest.mark.asyncio
async def test_ast_different_structure(strategy):
    code1 = """
def process(n):
    if n > 0:
        return n
    return -1
"""
    code2 = """
def process(n):
    while n > 0:
        n -= 1
    return n
"""

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert results[0].score < 100.0


@pytest.mark.asyncio
async def test_ast_slightly_modified_structure(strategy):
    code1 = """
def sum(a, b):
    return a + b
"""
    code2 = """
def sum(a, b):
    c = 0
    return a + b + c
"""

    submissions = [
        CodeSubmission(id=1, code=code1),
        CodeSubmission(id=2, code=code2),
    ]

    results = await strategy.check(submissions)

    assert len(results) == 1
    assert 50.0 < results[0].score < 100.0
