import os
import tempfile
import logging
import shlex
from typing import Optional

from app.schemas.settings import LinterSettings
from worker.config import WORKER_CONFIG
from worker.services.static_analysis.python import Flake8AnalysisStrategy
from worker.services.static_analysis.cpp import CppcheckAnalysisStrategy
from worker.services.static_analysis.java import CheckstyleAnalysisStrategy

logger = logging.getLogger(__name__)


class StaticAnalysisService:
    def __init__(self):
        # Пресеты для линтеров (наборы аргументов CLI)
        self.presets = {
            "python": {
                1: [],  # Default
                2: ["--max-complexity=10", "--ignore=E501"],  # Strict
                3: ["--select=E,W,F"],  # Google-ish
                4: ["--max-line-length=80"],  # Academic
            },
            "cpp": {
                1: ["--enable=all", "--suppress=missingIncludeSystem"],
                2: ["--enable=all", "--inconclusive", "--force"],
                3: ["--enable=style"],
                4: ["--enable=warning,style"],
            },
            "java": {
                1: ["-c", "/google_checks.xml"],
                2: ["-c", "/sun_checks.xml"],
                3: ["-c", "/google_checks.xml"],
                4: ["-c", "/google_checks.xml"],
            },
        }

    def _autdetect_language(self, source_code: dict[str, str]) -> str:
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
        self,
        source_code: dict[str, str],
        language: Optional[str] = None,
        settings: Optional[LinterSettings] = None,
    ) -> Optional[str]:
        if not WORKER_CONFIG.static_analysis.enabled:
            logger.info("Static analysis is disabled in config.")
            return None

        if not language:
            language = self._autdetect_language(source_code)

        language = language.lower()

        # Check if this linter is enabled in cascading settings
        if settings and language not in settings.enabled_linters:
            logger.info(f"Linter for {language} is disabled in cascading settings.")
            return None

        # Resolve preset and custom args
        extra_args = []
        if settings:
            preset_id = settings.linter_preset_id
            if language in self.presets and preset_id in self.presets[language]:
                extra_args.extend(self.presets[language][preset_id])

            if language in settings.custom_args:
                extra_args.extend(shlex.split(settings.custom_args[language]))

        # Instantiate strategy with resolved args
        if language == "python":
            strategy = Flake8AnalysisStrategy(extra_args=extra_args)
        elif language == "cpp":
            strategy = CppcheckAnalysisStrategy(extra_args=extra_args)
        elif language == "java":
            strategy = CheckstyleAnalysisStrategy(extra_args=extra_args)
        else:
            logger.warning(f"No linter strategy found for language: {language}")
            return f"Linter for {language} is not supported."

        timeout = (
            settings.timeout_seconds
            if settings
            else WORKER_CONFIG.static_analysis.timeout_seconds
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            for filename, content in source_code.items():
                file_path = os.path.join(temp_dir, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            logger.info(
                f"Running static analysis for {language} in {temp_dir} with args: {extra_args}"
            )
            report = await strategy.analyze(temp_dir, timeout)
            return report
