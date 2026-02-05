from tree_sitter import Language
import tree_sitter_cpp as tscpp
from .base import BasePreprocessor

class CppPreprocessor(BasePreprocessor):
    def _get_language(self) -> Language:
        return Language(tscpp.language())
