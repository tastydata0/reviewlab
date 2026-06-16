import pytest
from textwrap import dedent
from worker.utils.chunking import PythonChunker


@pytest.fixture
def chunker():
    return PythonChunker()


def test_python_chunks_functions(chunker):
    raw_code = dedent("""
        import math

        def calc_something(x, y):
            return math.sqrt(x**2 + y**2)
        
        def dummy():
            pass
    """).strip()
    chunks = chunker.chunk_code(raw_code)
    
    assert len(chunks) == 2
    
    assert chunks[0]["name"] == "calc_something"
    assert chunks[0]["type"] == "function"
    assert chunks[0]["code"].strip() == "def calc_something(x, y):\n    return math.sqrt(x**2 + y**2)"
    
    assert chunks[1]["name"] == "dummy"
    assert chunks[1]["type"] == "function"
    assert chunks[1]["code"].strip() == "def dummy():\n    pass"


def test_python_chunks_methods(chunker):
    raw_code = dedent("""
        class User:
            def __init__(self, name):
                self.name = name
                
            def get_name(self):
                return self.name
    """).strip()
    chunks = chunker.chunk_code(raw_code)
    
    assert len(chunks) == 2
    
    assert chunks[0]["name"] == "__init__"
    assert chunks[0]["code"].strip() == "def __init__(self, name):\n        self.name = name"
    
    assert chunks[1]["name"] == "get_name"
    assert chunks[1]["code"].strip() == "def get_name(self):\n        return self.name"


def test_python_chunks_classes():
    chunker = PythonChunker(mode="class")
    raw_code = """
class User:
    def __init__(self, name):
        self.name = name

class Admin(User):
    def delete_user(self, user):
        pass
"""
    chunks = chunker.chunk_code(raw_code)
    
    assert len(chunks) == 2
    
    assert chunks[0]["name"] == "User"
    assert chunks[0]["type"] == "class"
    assert "class User:" in chunks[0]["code"]
    
    assert chunks[1]["name"] == "Admin"
    assert chunks[1]["type"] == "class"
    assert "class Admin(User):" in chunks[1]["code"]
