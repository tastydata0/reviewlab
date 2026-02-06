from tree_sitter import Language
import tree_sitter_java as tsjava
from .base import BasePreprocessor

class JavaPreprocessor(BasePreprocessor):
    def _get_language(self) -> Language:
        return Language(tsjava.language())

    def _get_comment_query(self) -> str:
        return """
        (line_comment) @comment
        (block_comment) @comment
        """
