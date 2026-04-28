from pydantic import BaseModel, Field


class StaticAnalysisConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable or disable static analysis")
    timeout_seconds: int = Field(
        default=30, description="Timeout for linter execution in seconds"
    )


class LLMMentorConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable or disable LLM Mentor")
    model_name: str = Field(
        default="gpt-4o-mini", description="OpenAI model name to use"
    )
    system_prompt: str = Field(
        default="Ты опытный ИИ-ментор по программированию. Проанализируй код студента, результаты статического анализа и условие задачи. "
        "Укажи на ошибки, логические недочеты и дай советы по улучшению. "
        "Оцени общее качество кода (чистота, структура) и отдельно функциональную правильность (насколько код решает задачу). "
        "ОТВЕЧАЙ КРАТКО, ВЕДИ СЕБЯ КАК В СПЕШКЕ, пиши всё со строчной буквы. Не пиши код за студента, только задавай наводящие вопросы и подсказывай направления.",
        description="System prompt defining the mentor's persona and rules",
    )
    temperature: float = Field(
        default=0.3, description="Temperature for LLM generation"
    )
    max_tokens: int = Field(default=1500, description="Max tokens for LLM response")


class WorkerConfig(BaseModel):
    static_analysis: StaticAnalysisConfig = Field(default_factory=StaticAnalysisConfig)
    llm_mentor: LLMMentorConfig = Field(default_factory=LLMMentorConfig)


WORKER_CONFIG = WorkerConfig()
