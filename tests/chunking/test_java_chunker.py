import pytest
from app.utils.chunking import JavaChunker


@pytest.fixture
def chunker():
    return JavaChunker()


def test_java_chunks_methods_and_constructors(chunker):
    raw_code = """
public class Worker {
    // 123123123 params
    private String name;

    public Worker(String n) {
        // asd
        this.name = n;
    }
    
    public void work() {
        /* qwe
           test test */
        System.out.println("Working...");
    }
}
"""
    chunks = chunker.chunk_code(raw_code)
    
    assert len(chunks) == 2
    
    assert chunks[0]["name"] == "Worker"
    assert chunks[0]["type"] == "method"
    assert chunks[0]["code"] == "public Worker(String n) {\n        // asd\n        this.name = n;\n    }"
    
    assert chunks[1]["name"] == "work"
    assert chunks[1]["type"] == "method"
    assert chunks[1]["code"] == "public void work() {\n        /* qwe\n           test test */\n        System.out.println(\"Working...\");\n    }"
