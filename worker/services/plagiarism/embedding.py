import math
from itertools import combinations

from ...models.plagiarism import CodeSubmission, PlagiarismMatch
from ...services.plagiarism.base import BasePlagiarismStrategy
from ...utils.embedding.main import embed_768


class SingleEmbeddingStrategy(BasePlagiarismStrategy):
    """
    Стратегия 5 (Упрощенная). Семантическая (Vector Embeddings) без разбиения на чанки.

    Весь исходный код посылки целиком отправляется в модель для получения
    векторного представления (эмбеддинга). Сходство между посылками
    определяется через косинусное расстояние между их векторами.
    """

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = math.sqrt(sum(a * a for a in v1))
        magnitude2 = math.sqrt(sum(b * b for b in v2))
        if magnitude1 * magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    async def check(self, submissions: list[CodeSubmission]) -> list[PlagiarismMatch]:
        matches = []

        # Получаем эмбеддинги для всех посылок O(N) запросов к API/модели
        submission_embeddings = {}
        for sub in submissions:
            submission_embeddings[sub.id] = await embed_768(sub.code)

        # Сравниваем все пары O(N^2)
        for sub_a, sub_b in combinations(submissions, 2):
            vec_a = submission_embeddings[sub_a.id]
            vec_b = submission_embeddings[sub_b.id]

            similarity = self._cosine_similarity(vec_a, vec_b)
            # Переводим косинусное сходство [-1, 1] в проценты [0, 100]
            score = float(max(0.0, similarity * 100.0))

            matches.append(
                PlagiarismMatch(
                    source_id=sub_a.id,
                    target_id=sub_b.id,
                    score=score,
                    details={"method": "single_embedding"},
                )
            )

        return matches
