import os
import tempfile
import logging
from typing import Optional

from worker.config import WORKER_CONFIG
from worker.services.static_analysis.python import Flake8AnalysisStrategy
from worker.services.static_analysis.cpp import CppcheckAnalysisStrategy
from worker.services.static_analysis.java import CheckstyleAnalysisStrategy

logger = logging.getLogger(__name__)


class StaticAnalysisService:
    def __init__(self):
        self.strategies = {
            "python": Flake8AnalysisStrategy(),
            "cpp": CppcheckAnalysisStrategy(),
            "java": CheckstyleAnalysisStrategy(),
        }

    def _autodetect_language(self, source_code: dict[str, str]) -> str:
        extensions = {
            ".py": "python",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c": "cpp",
            ".hpp": "cpp",
            ".h": "cpp",
            ".java": "java",
        }

        counts = {"python": 0, "cpp": 0, "java": 0}

        for filename in source_code.keys():
            ext = os.path.splitext(filename)[1].lower()
            if ext in extensions:
                counts[extensions[ext]] += 1

        detected = max(counts.items(), key=lambda x: x[1])[0]
        if counts[detected] == 0:
            return "python"
        return detected

    async def analyze(
        self, source_code: dict[str, str], language: Optional[str] = None
    ) -> Optional[str]:
        if not WORKER_CONFIG.static_analysis.enabled:
            logger.info("Static analysis is disabled in config.")
            return None

        if not language:
            language = self._autodetect_language(source_code)

        language = language.lower()
        strategy = self.strategies.get(language)

        if not strategy:
            logger.warning(f"No linter strategy found for language: {language}")
            return f"Linter for {language} is not supported."

        with tempfile.TemporaryDirectory() as temp_dir:
            for filename, content in source_code.items():
                file_path = os.path.join(temp_dir, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            logger.info(f"Running static analysis for {language} in {temp_dir}")
            report = await strategy.analyze(
                temp_dir, WORKER_CONFIG.static_analysis.timeout_seconds
            )
            return report
