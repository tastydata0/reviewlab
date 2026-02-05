from app.utils.preprocessing.python import PythonPreprocessor


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

    preprocessor = PythonPreprocessor()
    result = preprocessor.preprocess(raw_python_code)
    return result


if __name__ == "__main__":
    chunks = get_chunks()
    print(chunks)
