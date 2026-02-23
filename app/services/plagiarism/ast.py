from itertools import combinations

from fuzzywuzzy import fuzz
from tree_sitter import Language, Parser

from app.models.plagiarism import CodeSubmission, PlagiarismMatch
from app.services.plagiarism.base import BasePlagiarismStrategy


class AstStrategy(BasePlagiarismStrategy):
    """
    Стратегия 3. Синтаксическая (AST Node Sequence).

    cравнение абстрактных синтаксических деревьев без учета лексики
    код парсится с помощью tree-sitter, извлекается последовательность типов узлов
    (игнорируя конкретные значения переменных и констант). Затем последовательности
    сравниваются с помощью расстояния Левенштейна.
    """

    def __init__(self, language: str = "python"):
        self.language = language

        if language == "python":
            import tree_sitter_python as ts_lang
        elif language == "cpp":
            import tree_sitter_cpp as ts_lang
        elif language == "java":
            import tree_sitter_java as ts_lang
        else:
            raise ValueError(f"Неподдерживаемый язык: {language}")

        ts_language = Language(ts_lang.language())
        self.parser = Parser(ts_language)

    def _get_ast_sequence(self, code: str) -> str:
        """
        парсит код и возвращает строку, состоящую из типов узлов AST,
        разделенных пробелом (для последующего сравнения Левенштейном).
        """
        tree = self.parser.parse(bytes(code, "utf8"))
        sequence = []

        def traverse(node):
            # is_named позволяет отфильтровать анонимные узлы
            # (например, скобки, запятые, ключевые слова вроде 'def', 'if'),
            # оставляя только значимые синтаксические конструкции.
            if node.is_named:
                sequence.append(node.type)
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return " ".join(sequence)

    async def check(self, submissions: list[CodeSubmission]) -> list[PlagiarismMatch]:
        matches = []

        # предварительный парсинг и обход деревьев O(N)
        submission_asts = {
            sub.id: self._get_ast_sequence(sub.code) for sub in submissions
        }

        # Сравнение всех пар O(N^2)
        for sub_a, sub_b in combinations(submissions, 2):
            ast_seq_a = submission_asts[sub_a.id]
            ast_seq_b = submission_asts[sub_b.id]

            if not ast_seq_a and not ast_seq_b:
                score = 100.0
            elif not ast_seq_a or not ast_seq_b:
                score = 0.0
            else:
                score = float(fuzz.ratio(ast_seq_a, ast_seq_b))

            matches.append(
                PlagiarismMatch(
                    source_id=sub_a.id,
                    target_id=sub_b.id,
                    score=score,
                    details={"method": "ast_sequence", "language": self.language},
                )
            )

        return matches
