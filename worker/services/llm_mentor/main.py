import logging
from typing import Optional
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from worker.config import WORKER_CONFIG
from app.settings import SETTINGS

logger = logging.getLogger(__name__)


class LLMMentorResponse(BaseModel):
    review: str = Field(description="The textual review and feedback for the student.")
    score: int = Field(
        description="A score from 0 to 100 representing the quality of the submission."
    )


class LLMMentorService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=SETTINGS.OPENAI_API_KEY.get_secret_value(),
            base_url=SETTINGS.OPENAI_API_BASE_URL,
        )

    def _format_source_code(self, source_code: dict[str, str]) -> str:
        formatted = []
        for filename, content in source_code.items():
            formatted.append(f"--- File: {filename} ---\n{content}\n")
        return "\n".join(formatted)

    async def analyze(
        self,
        source_code: dict[str, str],
        task_description: str,
        linter_report: Optional[str] = None,
        previous_source_code: Optional[dict[str, str]] = None,
        previous_review: Optional[str] = None,
        previous_linter_report: Optional[str] = None,
    ) -> Optional[LLMMentorResponse]:
        if not WORKER_CONFIG.llm_mentor.enabled:
            logger.info("LLM Mentor is disabled in config.")
            return None

        code_text = self._format_source_code(source_code)

        prompt = f"Задание:\n{task_description}\n\nТекущий исходный код студента:\n{code_text}\n\n"

        if linter_report:
            prompt += f"Текущие результаты статического анализа (линтер):\n{linter_report}\n\n"

        if previous_source_code or previous_review:
            prompt += "--- Контекст предыдущей попытки ---\n"
            if previous_source_code:
                prev_code_text = self._format_source_code(previous_source_code)
                prompt += f"Предыдущий код:\n{prev_code_text}\n"
            if previous_review:
                prompt += f"Предыдущая рецензия ИИ:\n{previous_review}\n"
            if previous_linter_report:
                prompt += f"Предыдущие ошибки линтера:\n{previous_linter_report}\n"
            prompt += "--- Конец контекста ---\n\n"

        prompt += (
            "Твоя задача: сравни решение с предыдущим (если оно есть), оцени прогресс, "
            "оцени текущее решение от 0 до 100 и дай конструктивный фидбек."
        )

        try:
            logger.info("Requesting review from LLM Mentor...")
            completion = await self.client.beta.chat.completions.parse(
                model=WORKER_CONFIG.llm_mentor.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": WORKER_CONFIG.llm_mentor.system_prompt,
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=LLMMentorResponse,
                temperature=WORKER_CONFIG.llm_mentor.temperature,
                max_tokens=WORKER_CONFIG.llm_mentor.max_tokens,
            )

            result = completion.choices[0].message.parsed
            logger.info(
                f"LLM Mentor review complete. Score: {result.score if result else 'N/A'}"
            )
            return result
        except Exception as e:
            logger.error(f"Error during LLM Mentor analysis: {e}")
            return None
