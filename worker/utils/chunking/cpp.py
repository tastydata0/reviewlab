from tree_sitter import Language
import tree_sitter_cpp as tscpp
from .base import BaseChunker

class CppChunker(BaseChunker):
    def _get_language(self) -> Language:
        return Language(tscpp.language())

    def _get_function_query(self) -> str:
        return "(function_definition) @function"

    def _get_class_query(self) -> str:
        return """
        (class_specifier) @class
        (struct_specifier) @class
        """
