import asyncio
import logging
from abc import ABC

logger = logging.getLogger(__name__)


class BaseStaticAnalysisStrategy(ABC):
    def __init__(self, cmd_template: str):
        self.cmd_template = cmd_template

    async def analyze(self, files_dir: str, timeout: int) -> str:
        cmd = self.cmd_template.format(files=files_dir)
        process = None
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return (stdout.decode() + "\n" + stderr.decode()).strip()
        except asyncio.TimeoutError:
            if process:
                process.kill()
            return "Linter execution timed out."
        except Exception as e:
            logger.error(f"Error running linter '{cmd}': {e}")
            return f"Error: {e}"
