import pytest
from app.utils.preprocessing import JavaPreprocessor


@pytest.fixture
def preprocessor():
    return JavaPreprocessor()


def test_java_removes_single_line_comments(preprocessor):
    raw_code = """
public int add(int a, int b) {
    // test comment
    return a + b; // eol comm
}
"""
    expected_code = """
public int add(int a, int b) {
    return a + b;
}
"""
    result = preprocessor.preprocess(raw_code)
    assert result.strip() == expected_code.strip()


def test_java_removes_multi_line_comments(preprocessor):
    raw_code = """
/* 
 * 1r1xf243t4x5g45
 */
public int multiply(int a, int b) {
    /* test comm */
    return a * b;
}
"""
    expected_code = """
public int multiply(int a, int b) {
    return a * b;
}
"""
    result = preprocessor.preprocess(raw_code)
    assert result.strip() == expected_code.strip()


def test_java_removes_javadoc_comments(preprocessor):
    raw_code = """
/**
 * javadoc test 123
 * @param a test ad asd
 * @param b hgi3ug3g
 * @return fxin3n34
 */
public int calculate(int a, int b) {
    return a + b; // test
}
"""
    expected_code = """
public int calculate(int a, int b) {
    return a + b;
}
"""
    result = preprocessor.preprocess(raw_code)
    assert result.strip() == expected_code.strip()
