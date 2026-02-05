from tree_sitter import Language
import tree_sitter_python as tspython
from .base import BasePreprocessor


class PythonPreprocessor(BasePreprocessor):
    def _get_language(self) -> Language:
        return Language(tspython.language())


# TODO: добавить удаление докстрингов
