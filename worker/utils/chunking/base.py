from abc import ABC, abstractmethod
from typing import List, Dict
from tree_sitter import Language, Parser, Query, QueryCursor

class BaseChunker(ABC):
    def __init__(self, mode="function"):
        """
        Инициализация чанкера.
        :param mode: "function" (по умолчанию) или "class".
        """
        self.mode = mode
        self.language = self._get_language()
        self.parser = Parser(self.language)

    @abstractmethod
    def _get_language(self) -> Language:
        pass

    @abstractmethod
    def _get_function_query(self) -> str:
        pass

    @abstractmethod
    def _get_class_query(self) -> str:
        pass

    def _get_chunk_query(self) -> str:
        if self.mode == "class":
            return self._get_class_query()
        return self._get_function_query()

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

    def chunk_code(self, source_code: str) -> List[Dict[str, str]]:
        source_bytes = source_code.encode("utf-8")
        tree = self.parser.parse(source_bytes)

        captures = self._execute_query(self._get_chunk_query(), tree.root_node)

        chunks = []
        for node, tag in captures:
            if tag in ["function", "method", "class"]:
                name_node = node.child_by_field_name("name")

                if not name_node and node.type == "function_definition":
                    declarator = node.child_by_field_name("declarator")
                    if declarator:
                        if declarator.type == "function_declarator":
                            name_node = declarator.child_by_field_name("declarator")
                        elif declarator.type in ("reference_declarator", "pointer_declarator"):
                            func_decl = declarator.child_by_field_name("declarator")
                            if func_decl and func_decl.type == "function_declarator":
                                name_node = func_decl.child_by_field_name("declarator")

                chunk_name = (
                    source_bytes[name_node.start_byte : name_node.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                    if name_node
                    else "anonymous"
                )

                # Просто вырезаем байты исходного узла и декодируем
                raw_chunk_bytes = source_bytes[node.start_byte : node.end_byte]
                chunk_code = raw_chunk_bytes.decode("utf-8", errors="ignore")
                
                chunks.append({"type": tag, "name": chunk_name, "code": chunk_code})

        return chunks
