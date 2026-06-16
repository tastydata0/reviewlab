import pytest
from worker.utils.chunking import CppChunker


@pytest.fixture
def chunker():
    return CppChunker()


def test_cpp_chunks_functions(chunker):
    raw_code = """
#include <iostream>

int calc_sum(int a, int b) {
    return a + b;
}

void do_nothing() {
    return;
}
"""
    chunks = chunker.chunk_code(raw_code)

    assert len(chunks) == 2

    assert chunks[0]["name"] == "calc_sum"
    assert chunks[0]["type"] == "function"
    assert (
        chunks[0]["code"]
        == "int calc_sum(int a, int b) {\n    return a + b;\n}"
    )

    assert chunks[1]["name"] == "do_nothing"
    assert chunks[1]["type"] == "function"
    assert (
        chunks[1]["code"]
        == "void do_nothing() {\n    return;\n}"
    )


def test_cpp_chunks_methods(chunker):
    raw_code = """
class MyClass {
public:
    MyClass() {
    }
    
    void do_stuff() {
        int x = 1;
    }
};
"""
    chunks = chunker.chunk_code(raw_code)

    assert len(chunks) == 2

    # В C++ конструктор может парситься специфично, поэтому проверим только наличие и код
    assert chunks[0]["name"] in [
        "MyClass",
        "anonymous",
    ]  # зависит от версии tree-sitter
    assert "MyClass() {" in chunks[0]["code"]

    assert chunks[1]["name"] == "do_stuff"
    assert (
        chunks[1]["code"]
        == "void do_stuff() {\n        int x = 1;\n    }"
    )


def test_cpp_chunks_classes_and_structs():
    chunker = CppChunker(mode="class")
    raw_code = """
class MyClass {
    void method() {}
};

struct MyStruct {
    int value;
};
"""
    chunks = chunker.chunk_code(raw_code)

    assert len(chunks) == 2

    assert chunks[0]["name"] == "MyClass"
    assert chunks[0]["type"] == "class"
    assert "class MyClass" in chunks[0]["code"]

    assert chunks[1]["name"] == "MyStruct"
    assert chunks[1]["type"] == "class"
    assert "struct MyStruct" in chunks[1]["code"]
