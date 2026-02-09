from tree_sitter import Language
import tree_sitter_java as tsjava
from .base import BaseChunker

class JavaChunker(BaseChunker):
    def _get_language(self) -> Language:
        return Language(tsjava.language())

    def _get_chunk_query(self) -> str:
        return """
        (method_declaration) @method
        (constructor_declaration) @method
        """
