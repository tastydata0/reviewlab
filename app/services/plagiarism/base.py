from abc import ABC, abstractmethod

from app.models.plagiarism import CodeSubmission, PlagiarismMatch


class BasePlagiarismStrategy(ABC):
    """
    базовая абстракция для всех стратегий проверки на плагиат
    """

    @abstractmethod
    async def check(self, submissions: list[CodeSubmission]) -> list[PlagiarismMatch]:
        """
        - принимает набор исходных кодов студентов для одной задачи
        - возвращает граф сходства в виде списка ребер (попарные оценки)
        """
        pass
