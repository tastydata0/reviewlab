from worker.services.static_analysis.base import BaseStaticAnalysisStrategy


class PythonStaticAnalysisStrategy(BaseStaticAnalysisStrategy):
    pass


class Flake8AnalysisStrategy(PythonStaticAnalysisStrategy):
    def __init__(self, extra_args: str = ""):
        super().__init__(f"flake8 {extra_args} {{files}}")
