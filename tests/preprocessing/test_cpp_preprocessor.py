import pytest
from worker.utils.preprocessing import CppPreprocessor


@pytest.fixture
def preprocessor():
    return CppPreprocessor()


def test_cpp_removes_single_line_comments(preprocessor):
    raw_code = """
int add(int a, int b) {
    // test 123
    return a + b; // eol comm
}
"""
    expected_code = """
int add(int a, int b) {
    return a + b;
}
"""
    result = preprocessor.preprocess(raw_code)
    assert result.strip() == expected_code.strip()


def test_cpp_removes_multi_line_comments(preprocessor):
    raw_code = """
/* 
 * comm test 2
 */
int multiply(int a, int b) {
    /* test 123 */
    return a * b;
}
"""
    expected_code = """
int multiply(int a, int b) {
    return a * b;
}
"""
    result = preprocessor.preprocess(raw_code)
    assert result.strip() == expected_code.strip()


def test_cpp_removes_mixed_comments(preprocessor):
    raw_code = """
// test 123
void init() {
    /* 
    asduhk23g32yu
    */
    int x = 5; // x is 5
}
"""
    expected_code = """
void init() {
    int x = 5;
}
"""
    result = preprocessor.preprocess(raw_code)
    assert result.strip() == expected_code.strip()
