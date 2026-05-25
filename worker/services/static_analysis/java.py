from typing import Optional
from worker.services.static_analysis.base import BaseStaticAnalysisStrategy


class JavaStaticAnalysisStrategy(BaseStaticAnalysisStrategy):
    pass


class CheckstyleAnalysisStrategy(JavaStaticAnalysisStrategy):
    def __init__(self, extra_args: Optional[list[str]] = None):
        args = extra_args or ["-c", "bin/linters/configs/reviewlab_checks.xml"]
        super().__init__("checkstyle", args)
