from tree_sitter import Language
import tree_sitter_python as tspython
from .base import BaseChunker

class PythonChunker(BaseChunker):
    def _get_language(self) -> Language:
        return Language(tspython.language())

    def _get_function_query(self) -> str:
        return "(function_definition) @function"

    def _get_class_query(self) -> str:
        return "(class_definition) @class"
