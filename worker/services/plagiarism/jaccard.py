from itertools import combinations

from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token

from app.models.plagiarism import CodeSubmission, PlagiarismMatch
from app.services.plagiarism.base import BasePlagiarismStrategy


class JaccardStrategy(BasePlagiarismStrategy):
    """
    Cтратегия 2. Лексическая Token Masking + N-граммы + Jaccard

    код превращается в поток токенов. то есть названия переменных, функций,
    строковые и числовые литералы маскируются. оставшиеся токены
    разбиваются на N-граммы, для которых вычисляется индекс Жаккара
    """

    def __init__(self, n_gram_size: int = 5, language: str | None = None):
        # language - Язык программирования (например, 'python', 'cpp', 'java'). Если None, попытается определить автоматически.
        self.n_gram_size = n_gram_size
        self.language = language

    def _get_lexer(self, code: str):
        if self.language:
            try:
                return get_lexer_by_name(self.language)
            except Exception:
                pass
        return guess_lexer(code)

    def _tokenize_and_mask(self, code: str) -> list[str]:
        lexer = self._get_lexer(code)
        tokens = lexer.get_tokens(code)

        masked_tokens = []
        for token_type, value in tokens:
            # игнорируем пробелы, переносы строк и комментарии
            if token_type in Token.Text or token_type in Token.Comment:
                continue

            # маскируем переменные, функции, имена классов
            if token_type in Token.Name:
                masked_tokens.append("<ID>")
            # маскируем строковые литералы
            elif token_type in Token.Literal.String:
                masked_tokens.append("<STR>")
            # маскируем числовые литералы
            elif token_type in Token.Literal.Number:
                masked_tokens.append("<NUM>")
            else:
                # оставляем ключевые слова if, for, class и операторы +, -, =, {, } как есть
                # приводим к нижнему регистру для единообразия
                masked_tokens.append(value.lower())

        return masked_tokens

    def _get_ngrams(self, tokens: list[str]) -> set[tuple[str, ...]]:
        ngrams = set()
        if len(tokens) < self.n_gram_size:
            # если токенов меньше окна, возвращаем весь массив как одну n-грамму
            return {tuple(tokens)} if tokens else set()

        for i in range(len(tokens) - self.n_gram_size + 1):
            ngrams.add(tuple(tokens[i : i + self.n_gram_size]))
        return ngrams

    async def check(self, submissions: list[CodeSubmission]) -> list[PlagiarismMatch]:
        matches = []

        # предварительная токенизация и извлечение N-грамм
        submission_ngrams = {}
        for sub in submissions:
            tokens = self._tokenize_and_mask(sub.code)
            submission_ngrams[sub.id] = self._get_ngrams(tokens)

        for sub_a, sub_b in combinations(submissions, 2):
            ngrams_a = submission_ngrams[sub_a.id]
            ngrams_b = submission_ngrams[sub_b.id]

            if not ngrams_a and not ngrams_b:
                score = 100.0  # оба кода пустые
            elif not ngrams_a or not ngrams_b:
                score = 0.0  # один код пустой, другой нет
            else:
                intersection = len(ngrams_a.intersection(ngrams_b))
                union = len(ngrams_a.union(ngrams_b))
                score = (intersection / union) * 100.0

            matches.append(
                PlagiarismMatch(
                    source_id=sub_a.id,
                    target_id=sub_b.id,
                    score=score,
                    details={
                        "method": "jaccard_ngrams",
                        "n_gram_size": self.n_gram_size,
                    },
                )
            )

        return matches
