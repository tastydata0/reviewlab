from worker.services.static_analysis.base import BaseStaticAnalysisStrategy


class JavaStaticAnalysisStrategy(BaseStaticAnalysisStrategy):
    pass


class CheckstyleAnalysisStrategy(JavaStaticAnalysisStrategy):
    def __init__(self, extra_args: str = "-c /google_checks.xml"):
        super().__init__(f"checkstyle {extra_args} {{files}}")
