import math
from itertools import combinations
from sqlalchemy import text

from ...models.plagiarism import CodeSubmission, PlagiarismMatch
from ...services.plagiarism.base import BasePlagiarismStrategy
from ...utils.chunking import CppChunker, JavaChunker, PythonChunker
from ...utils.preprocessing import CppPreprocessor, JavaPreprocessor, PythonPreprocessor
from ...services.embedding import EmbeddingService


class SemanticChunkingStrategy(BasePlagiarismStrategy):
    """
    cтратегия 6 - Semantic Chunking.

    Алгоритм:
    1. Исходный код разбивается на логические блоки (функции/методы/классы.
    2. Каждый блок прогоняется через модель эмбеддингов, формируя "семантический отпечаток" кода.
    3. Для каждой функции из посылки А ищется наиболее семантически похожая функция из посылки Б через pgvector. Считается процент перекрытия.

    позволяет выявлять "Плагиат 4-го типа" (алгоритмический и
    кросс-языковой), против которого бессильны лексические методы вроде Winnowing.
    """

    def __init__(self, language: str = "python", session=None):
        self.language = language
        self.session = session
        self.embedding_service = EmbeddingService(session) if session else None
        
        if language == "python":
            self.chunker = PythonChunker()
            self.preprocessor = PythonPreprocessor()
        elif language == "cpp":
            self.chunker = CppChunker()
            self.preprocessor = CppPreprocessor()
        elif language == "java":
            self.chunker = JavaChunker()
            self.preprocessor = JavaPreprocessor()
        else:
            raise ValueError(f"Unsupported language for semantic chunking: {language}")

    async def compute_coverage(self, sub_a_id: str, sub_b_id: str) -> float:
        if not self.session:
            return 0.0

        query = text("""
            SELECT COALESCE(AVG(max_sim), 0.0) as coverage
            FROM (
                SELECT MAX(1 - (a.embedding <=> b.embedding)) as max_sim
                FROM embedding_1536 a
                CROSS JOIN embedding_1536 b
                WHERE a.submission_id = :a_id AND b.submission_id = :b_id
                GROUP BY a.id
            ) as subq
        """)
        res = await self.session.execute(query, {"a_id": sub_a_id, "b_id": sub_b_id})
        val = res.scalar()
        return float(val) if val is not None else 0.0

    async def check(self, submissions: list[CodeSubmission]) -> list[PlagiarismMatch]:
        matches = []

        if not self.embedding_service:
            # Если нет сессии БД (например, в некоторых старых тестах), пропускаем
            print("Warning: DB session not provided to SemanticChunkingStrategy. Returning empty matches.")
            return []

        # разбиение на чанки и генерация эмбеддингов
        for sub in submissions:
            clean_code = self.preprocessor.preprocess(sub.code)
            chunks = self.chunker.chunk_code(clean_code)
            print(f"Submission {sub.id}: {len(chunks)} chunks")

            # если код представляет собой простой скрипт без функций
            if not chunks:
                chunks = [{"code": clean_code}]

            for chunk in chunks:
                await self.embedding_service.get_or_create_embedding_1536(
                    text=chunk["code"],
                    task_id=sub.task_id,
                    user_id=sub.user_id,
                    submission_id=str(sub.id)
                )

        # попарное сравнение посылок (О квадрат)
        for sub_a, sub_b in combinations(submissions, 2):
            if sub_a.user_id and sub_b.user_id and sub_a.user_id == sub_b.user_id:
                # исключаем случайное сравнение между собой решений одного юзера
                continue

            avg_a_to_b = await self.compute_coverage(str(sub_a.id), str(sub_b.id))
            avg_b_to_a = await self.compute_coverage(str(sub_b.id), str(sub_a.id))

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
