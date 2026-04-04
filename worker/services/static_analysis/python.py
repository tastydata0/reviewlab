from typing import Optional
from worker.services.static_analysis.base import BaseStaticAnalysisStrategy


class PythonStaticAnalysisStrategy(BaseStaticAnalysisStrategy):
    pass


class Flake8AnalysisStrategy(PythonStaticAnalysisStrategy):
    def __init__(self, extra_args: Optional[list[str]] = None):
        args = extra_args or []
        super().__init__("flake8", args)
