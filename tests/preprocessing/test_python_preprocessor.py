import pytest
from app.utils.preprocessing import PythonPreprocessor


@pytest.fixture
def preprocessor():
    return PythonPreprocessor()


def test_python_removes_single_line_comments(preprocessor):
    raw_code = """
def add(a, b):
    # comm 123 123
    return a + b # eol comm
"""
    expected_code = """
def add(a, b):
    return a + b
"""
    result = preprocessor.preprocess(raw_code)
    assert result.strip() == expected_code.strip()


def test_python_multiple_comments_and_blank_lines(preprocessor):
    raw_code = """
# realkjsdljasd

def foo():
    # comm 1
    
    # comm 2
    pass
"""
    expected_code = """
def foo():
    pass
"""
    result = preprocessor.preprocess(raw_code)
    assert result.strip() == expected_code.strip()
