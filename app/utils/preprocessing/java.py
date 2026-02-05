from tree_sitter import Language
import tree_sitter_java as tsjava
from .base import BasePreprocessor

class JavaPreprocessor(BasePreprocessor):
    def _get_language(self) -> Language:
        return Language(tsjava.language())
