from app.utils.preprocessing.python import PythonPreprocessor
from app.utils.chunking.python import PythonChunker


def get_chunks():
    raw_python_code = """
import math

# test comment
class Test:
    def __init__(self, name):
        '''docstring 12o 3hoihfo873h8734'''
        self.name = name # Имя пользователя

    def func1(self, x, y):
        # formula 123
        result = math.sqrt(x**2 + y**2)
        
        return result
    """

    chunks = []

    preprocessor = PythonPreprocessor()
    chunker_py = PythonChunker(preprocessor)
    chunks.extend(chunker_py.chunk_code(raw_python_code))

    return chunks


if __name__ == "__main__":
    chunks = get_chunks()
    print(chunks)

[
    {
        "type": "function",
        "name": "__init__",
        "code": "def __init__(self, name):\n        '''docstring 12o 3hoihfo873h8734'''\n        self.name = name",
    },
    {
        "type": "function",
        "name": "func1",
        "code": "def func1(self, x, y):\n        result = math.sqrt(x**2 + y**2)\n        return result",
    },
]
