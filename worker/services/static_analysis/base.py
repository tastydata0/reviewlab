import asyncio
import logging
from abc import ABC
import os

logger = logging.getLogger(__name__)


class BaseStaticAnalysisStrategy(ABC):
    def __init__(self, program: str, args: list[str]):
        self.program = program
        self.args = args

    async def analyze(self, files_dir: str, timeout: int) -> str:
        current_args = self.args + [files_dir]
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                self.program,
                *current_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            report = (stdout.decode() + "\n" + stderr.decode()).strip()

            # Clean up the output: remove the absolute path to temp_dir
            # We add a trailing slash to make it look like relative paths
            abs_path = os.path.abspath(files_dir)
            if not abs_path.endswith(os.sep):
                abs_path += os.sep

            report = report.replace(abs_path, "")
            return report
        except asyncio.TimeoutError:
            if process:
                process.kill()
            return "Linter execution timed out."
        except Exception as e:
            logger.error(f"Error running linter '{self.program}': {e}")
            return f"Error: {e}"
