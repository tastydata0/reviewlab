import pytest
from app.utils.chunking import CppChunker


@pytest.fixture
def chunker():
    return CppChunker()


def test_cpp_chunks_functions(chunker):
    raw_code = """
#include <iostream>

// asdasdasd
int calc_sum(int a, int b) {
    // test 123
    return a + b;
}

void do_nothing() {
    /* qwe qwe
       zxcvbn */
    return;
}
"""
    chunks = chunker.chunk_code(raw_code)
    
    assert len(chunks) == 2
    
    assert chunks[0]["name"] == "calc_sum"
    assert chunks[0]["type"] == "function"
    assert chunks[0]["code"] == "int calc_sum(int a, int b) {\n    // test 123\n    return a + b;\n}"
    
    assert chunks[1]["name"] == "do_nothing"
    assert chunks[1]["type"] == "function"
    assert chunks[1]["code"] == "void do_nothing() {\n    /* qwe qwe\n       zxcvbn */\n    return;\n}"


def test_cpp_chunks_methods(chunker):
    raw_code = """
class MyClass {
public:
    MyClass() {
        // asdfg
    }
    
    void do_stuff() {
        // test 12345
        int x = 1;
    }
};
"""
    chunks = chunker.chunk_code(raw_code)
    
    assert len(chunks) == 2
    
    # В C++ конструктор может парситься специфично, поэтому проверим только наличие и код
    assert chunks[0]["name"] in ["MyClass", "anonymous"] # зависит от версии tree-sitter
    assert "MyClass() {" in chunks[0]["code"]
    
    assert chunks[1]["name"] == "do_stuff"
    assert chunks[1]["code"] == "void do_stuff() {\n        // test 12345\n        int x = 1;\n    }"
