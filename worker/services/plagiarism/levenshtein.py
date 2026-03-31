from itertools import combinations

from fuzzywuzzy import fuzz

from app.models.plagiarism import CodeSubmission, PlagiarismMatch
from app.services.plagiarism.base import BasePlagiarismStrategy


class LevenshteinStrategy(BasePlagiarismStrategy):
    """
    cтратегия 1. Нормализованный текст + Расстояние Левенштейна (Baseline).

    cравнивает тексты посылок посимвольно после жесткой нормализации
    (удаление всех пробелов, переносов строк, приведение к нижнему регистру).
    """

    def _normalize(self, text: str) -> str:
        text = (
            text.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
        )
        return text.lower()

    async def check(self, submissions: list[CodeSubmission]) -> list[PlagiarismMatch]:
        """
        считает попарное расстояние Левенштейна для всех переданных кодов.
        """
        matches = []

        # предварительная нормализация
        normalized_codes = {sub.id: self._normalize(sub.code) for sub in submissions}

        # все уникальные пары
        for sub_a, sub_b in combinations(submissions, 2):
            code_a = normalized_codes[sub_a.id]
            code_b = normalized_codes[sub_b.id]

            score = float(fuzz.ratio(code_a, code_b))

            matches.append(
                PlagiarismMatch(
                    source_id=sub_a.id,
                    target_id=sub_b.id,
                    score=score,
                    details={"method": "levenshtein_ratio"},
                )
            )

        return matches
