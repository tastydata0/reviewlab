from tree_sitter import Language
import tree_sitter_cpp as tscpp
from .base import BaseChunker

class CppChunker(BaseChunker):
    def _get_language(self) -> Language:
        return Language(tscpp.language())

    def _get_chunk_query(self) -> str:
        return "(function_definition) @function"
