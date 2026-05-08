import logging
from typing import List

from app.models.submission import Submission
from worker.models.plagiarism import CodeSubmission
from worker.services.plagiarism.semantic import SemanticChunkingStrategy
from worker.services.plagiarism.copydetect_strategy import CopydetectStrategy

logger = logging.getLogger(__name__)


class PlagiarismService:
    def __init__(self):
        # Стратегии по умолчанию
        pass

    async def analyze(
        self,
        current_submission: Submission,
        other_submissions: List[Submission],
        language: str = "python",
    ):
        """
        Сравнивает текущую посылку со списком других посылок.
        """
        if not other_submissions:
            logger.info("No other submissions to compare with.")
            return 0.0, 0.0, 0.0, {}

        # Конвертируем в формат CodeSubmission
        current_code = self._get_combined_code(current_submission.source_code)
        current_sub = CodeSubmission(id=str(current_submission.id), code=current_code)

        others = [
            CodeSubmission(id=str(s.id), code=self._get_combined_code(s.source_code))
            for s in other_submissions
        ]

        all_subs = [current_sub] + others

        # Fast
        lexical_strategy = CopydetectStrategy(language=language)

        lexical_matches = await lexical_strategy.check(all_subs)
        print(f"Lexical matches: {lexical_matches}")

        # Находим максимальный балл для текущей посылки
        lexical_score = self._get_max_score_for_id(
            str(current_submission.id), lexical_matches
        )

        # Deep
        # используем SemanticChunking как основной "Type-4" детектор
        semantic_strategy = SemanticChunkingStrategy(language=language)
        semantic_matches = await semantic_strategy.check(all_subs)
        print(f"Semantic matches: {semantic_matches}")
        semantic_score = self._get_max_score_for_id(
            str(current_submission.id), semantic_matches
        )

        # Итоговый балл - максимум
        final_score = max(lexical_score, semantic_score)

        # Собираем детали по каждой встреченной посылке
        all_matches = self._get_matches_for_id(
            str(current_submission.id), lexical_matches, semantic_matches
        )

        return final_score, lexical_score, semantic_score, all_matches

    def _get_combined_code(self, source_code: dict[str, str]) -> str:
        return "\n\n".join(source_code.values())

    def _get_max_score_for_id(self, sub_id: str, matches: List) -> float:
        relevant_scores = [
            m.score
            for m in matches
            if str(m.source_id) == sub_id or str(m.target_id) == sub_id
        ]
        return max(relevant_scores) if relevant_scores else 0.0

    def _get_matches_for_id(
        self, sub_id: str, lex_matches: List, sem_matches: List
    ) -> dict[str, float]:
        res = {}

        for m in lex_matches + sem_matches:
            # определяем "другой" ID
            other_id = None
            if str(m.source_id) == sub_id:
                other_id = str(m.target_id)
            elif str(m.target_id) == sub_id:
                other_id = str(m.source_id)

            if other_id:
                res[other_id] = max(res.get(other_id, 0.0), m.score)

        return res
