from worker.services.static_analysis.base import BaseStaticAnalysisStrategy


class CppStaticAnalysisStrategy(BaseStaticAnalysisStrategy):
    pass


class CppcheckAnalysisStrategy(CppStaticAnalysisStrategy):
    def __init__(self, extra_args: str = "--enable=all"):
        super().__init__(f"cppcheck {extra_args} {{files}}")
