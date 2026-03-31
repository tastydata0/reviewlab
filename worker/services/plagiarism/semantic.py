import math
from itertools import combinations
from typing import List

from ...models.plagiarism import CodeSubmission, PlagiarismMatch
from ...services.plagiarism.base import BasePlagiarismStrategy
from ...utils.chunking import CppChunker, JavaChunker, PythonChunker
from ...utils.embedding.main import embed_1536


class SemanticChunkingStrategy(BasePlagiarismStrategy):
    """
    cтратегия 6 - Semantic Chunking.

    Алгоритм:
    1. Исходный код разбивается на логические блоки (функции/методы/классы.
    2. Каждый блок прогоняется через модель эмбеддингов, формируя "семантический отпечаток" кода.
    3. Для каждой функции из посылки А ищется наиболее семантически похожая функция из посылки Б. Считается процент перекрытия.

    позволяет выявлять "Плагиат 4-го типа" (алгоритмический и
    кросс-языковой), против которого бессильны лексические методы вроде Winnowing.
    """

    def __init__(self, language: str = "python"):
        self.language = language
        if language == "python":
            self.chunker = PythonChunker()
        elif language == "cpp":
            self.chunker = CppChunker()
        elif language == "java":
            self.chunker = JavaChunker()
        else:
            raise ValueError(f"Unsupported language for semantic chunking: {language}")

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = math.sqrt(sum(a * a for a in v1))
        magnitude2 = math.sqrt(sum(b * b for b in v2))
        if magnitude1 * magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    async def check(self, submissions: List[CodeSubmission]) -> List[PlagiarismMatch]:
        matches = []

        # разбиение на чанки и генерация эмбеддингов
        submission_embeddings = {}
        for sub in submissions:
            # получаем AST-чанки
            chunks = self.chunker.chunk_code(sub.code)
            print(f"{len(chunks)} chunks")

            # если код представляет собой простой скрипт без функций
            if not chunks:
                chunks = [{"code": sub.code}]

            embeddings = []
            for chunk in chunks:
                vec = await embed_1536(chunk["code"])
                embeddings.append(vec)

            submission_embeddings[sub.id] = embeddings

        # попарное сравнение посылок (О квадрат)
        for sub_a, sub_b in combinations(submissions, 2):
            emb_a = submission_embeddings[sub_a.id]
            emb_b = submission_embeddings[sub_b.id]

            if not emb_a and not emb_b:
                score = 100.0
            elif not emb_a or not emb_b:
                score = 0.0
            else:
                # coverage: насколько код A покрывается кодом B
                scores_a_to_b = []
                for va in emb_a:
                    best_sim = max(
                        [self._cosine_similarity(va, vb) for vb in emb_b], default=0.0
                    )
                    scores_a_to_b.append(best_sim)

                # И насколько код B покрывается кодом A
                scores_b_to_a = []
                for vb in emb_b:
                    best_sim = max(
                        [self._cosine_similarity(vb, va) for va in emb_a], default=0.0
                    )
                    scores_b_to_a.append(best_sim)

                avg_a_to_b = (
                    sum(scores_a_to_b) / len(scores_a_to_b) if scores_a_to_b else 0.0
                )
                avg_b_to_a = (
                    sum(scores_b_to_a) / len(scores_b_to_a) if scores_b_to_a else 0.0
                )

                # берём максимум (если студент взял 100% чужого кода и добавил 5 своих функций,
                # то покрытие чужой к своему будет маленьким, а свой к чужому = 100%)
                # это гарантирует поимку частичного плагиата
                similarity = max(avg_a_to_b, avg_b_to_a)
                score = float(max(0.0, similarity * 100.0))

            matches.append(
                PlagiarismMatch(
                    source_id=sub_a.id,
                    target_id=sub_b.id,
                    score=score,
                    details={"method": "semantic_chunking"},
                )
            )

        return matches
