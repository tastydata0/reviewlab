import pytest
from app.utils.chunking import PythonChunker


@pytest.fixture
def chunker():
    return PythonChunker()


def test_python_chunks_functions(chunker):
    raw_code = """
import math

# asdasd qwerty
def calc_something(x, y):
    # test 123
    return math.sqrt(x**2 + y**2)
    
def dummy():
    pass # zxcvbn
"""
    chunks = chunker.chunk_code(raw_code)
    
    assert len(chunks) == 2
    
    assert chunks[0]["name"] == "calc_something"
    assert chunks[0]["type"] == "function"
    assert chunks[0]["code"] == "def calc_something(x, y):\n    # test 123\n    return math.sqrt(x**2 + y**2)"
    
    assert chunks[1]["name"] == "dummy"
    assert chunks[1]["type"] == "function"
    assert chunks[1]["code"] == "def dummy():\n    pass # zxcvbn"


def test_python_chunks_methods(chunker):
    raw_code = """
class User:
    # qweqwe
    def __init__(self, name):
        self.name = name
        
    def get_name(self):
        # test test test
        return self.name
"""
    chunks = chunker.chunk_code(raw_code)
    
    assert len(chunks) == 2
    
    assert chunks[0]["name"] == "__init__"
    assert chunks[0]["code"] == "def __init__(self, name):\n        self.name = name"
    
    assert chunks[1]["name"] == "get_name"
    assert chunks[1]["code"] == "def get_name(self):\n        # test test test\n        return self.name"
