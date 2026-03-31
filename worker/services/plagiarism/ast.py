import math
from abc import ABC, abstractmethod
from itertools import combinations

from fuzzywuzzy import fuzz
from tree_sitter import Language, Parser

from app.models.plagiarism import CodeSubmission, PlagiarismMatch
from app.services.plagiarism.base import BasePlagiarismStrategy
from app.utils.embedding.main import embed_768


class BaseAstStrategy(BasePlagiarismStrategy, ABC):
    """
    Стратегия 3. Синтаксическая (AST Node Sequence).
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
        tree = self.parser.parse(bytes(code, "utf8"))
        sequence = []

        def traverse(node):
            if node.is_named:
                sequence.append(node.type)
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return " ".join(sequence)

    @abstractmethod
    async def _compare_asts(self, ast_seq_a: str, ast_seq_b: str) -> float:
        """
        компаратор - cавнивает две последовательности узлов AST и возвращает процент сходства 0 - 100
        """
        pass

    async def check(self, submissions: list[CodeSubmission]) -> list[PlagiarismMatch]:
        matches = []

        submission_asts = {
            sub.id: self._get_ast_sequence(sub.code) for sub in submissions
        }

        for sub_a, sub_b in combinations(submissions, 2):
            ast_seq_a = submission_asts[sub_a.id]
            ast_seq_b = submission_asts[sub_b.id]

            if not ast_seq_a and not ast_seq_b:
                score = 100.0
            elif not ast_seq_a or not ast_seq_b:
                score = 0.0
            else:
                score = await self._compare_asts(ast_seq_a, ast_seq_b)

            matches.append(
                PlagiarismMatch(
                    source_id=sub_a.id,
                    target_id=sub_b.id,
                    score=score,
                    details={
                        "method": self.__class__.__name__,
                        "language": self.language,
                    },
                )
            )

        return matches


class AstLevenshteinStrategy(BaseAstStrategy):
    """
    компаратор AST - расстояния Левенштейна.
    """

    async def _compare_asts(self, ast_seq_a: str, ast_seq_b: str) -> float:
        return float(fuzz.ratio(ast_seq_a, ast_seq_b))


class AstEmbeddingStrategy(BaseAstStrategy):
    """
    компаратор AST - косинусное сходство эмбеддингов
    """

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = math.sqrt(sum(a * a for a in v1))
        magnitude2 = math.sqrt(sum(b * b for b in v2))
        if magnitude1 * magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    async def _compare_asts(self, ast_seq_a: str, ast_seq_b: str) -> float:
        # print(f"Comparing asts: {ast_seq_a} \nand\n {ast_seq_b}")
        vec_a = await embed_768(ast_seq_a)
        vec_b = await embed_768(ast_seq_b)

        # [-1, 1]
        similarity = self._cosine_similarity(vec_a, vec_b)

        # Переводим в проценты [0, 100]
        # (отрицательное сходство считаем за 0, так как это абсолютно разные структуры)
        score = max(0.0, similarity * 100.0)
        return float(score)


class AstJaccardStrategy(BaseAstStrategy):
    """
    компаратор AST - индекс Жаккара по N-граммам.
    """

    def __init__(self, language: str = "python", n_gram_size: int = 2):
        super().__init__(language=language)
        self.n_gram_size = n_gram_size

    def _get_ngrams(self, sequence: str) -> set[tuple[str, ...]]:
        tokens = sequence.split()
        ngrams = set()
        if len(tokens) < self.n_gram_size:
            return {tuple(tokens)} if tokens else set()
            
        for i in range(len(tokens) - self.n_gram_size + 1):
            ngrams.add(tuple(tokens[i:i + self.n_gram_size]))
        return ngrams

    async def _compare_asts(self, ast_seq_a: str, ast_seq_b: str) -> float:
        ngrams_a = self._get_ngrams(ast_seq_a)
        ngrams_b = self._get_ngrams(ast_seq_b)
        
        if not ngrams_a and not ngrams_b:
            return 100.0
        elif not ngrams_a or not ngrams_b:
            return 0.0
            
        intersection = len(ngrams_a.intersection(ngrams_b))
        union = len(ngrams_a.union(ngrams_b))
        return float((intersection / union) * 100.0)
