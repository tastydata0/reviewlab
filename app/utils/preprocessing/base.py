import re
from abc import ABC, abstractmethod
from typing import List
from tree_sitter import Language, Parser, Query, QueryCursor

class BasePreprocessor(ABC):
    def __init__(self):
        self.language = self._get_language()
        self.parser = Parser(self.language)

    @abstractmethod
    def _get_language(self) -> Language:
        pass

    def _execute_query(self, query_str: str, node) -> List[tuple]:
        query = Query(self.language, query_str)
        cursor = QueryCursor(query)
        captures_dict = cursor.captures(node)

        result = []
        for tag, nodes in captures_dict.items():
            for n in nodes:
                result.append((n, tag))

        result.sort(key=lambda x: x[0].start_byte)
        return result

    def preprocess(self, source_code: str) -> str:
        """Принимает код строкой и возвращает очищенный код."""
        source_bytes = source_code.encode("utf-8")
        tree = self.parser.parse(source_bytes)
        return self.clean_code(source_bytes, tree.root_node)

    def clean_code(self, source_bytes: bytes, node) -> str:
        """Внутренний метод: удаляет комментарии и нормализует пробелы в конкретном узле."""
        captures = self._execute_query("(comment) @comment", node)

        ranges_to_remove = []
        for captured_node, _ in captures:
            ranges_to_remove.append((captured_node.start_byte, captured_node.end_byte))

        ranges_to_remove.sort(key=lambda x: x[0], reverse=True)

        clean_bytes = bytearray(source_bytes[node.start_byte : node.end_byte])
        node_start = node.start_byte

        for start, end in ranges_to_remove:
            rel_start = start - node_start
            rel_end = end - node_start
            if rel_start >= 0 and rel_end <= len(clean_bytes):
                del clean_bytes[rel_start:rel_end]

        clean_str = clean_bytes.decode("utf-8", errors="ignore")
        clean_str = re.sub(r"\n\s*\n", "\n", clean_str).strip()
        return clean_str
