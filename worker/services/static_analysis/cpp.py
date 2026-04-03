from typing import List, Optional
from worker.services.static_analysis.base import BaseStaticAnalysisStrategy


class CppStaticAnalysisStrategy(BaseStaticAnalysisStrategy):
    pass


class CppcheckAnalysisStrategy(CppStaticAnalysisStrategy):
    def __init__(self, extra_args: Optional[List[str]] = None):
        args = extra_args or ["--enable=all"]
        super().__init__("cppcheck", args)
