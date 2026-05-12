from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PlagiarismSettings(BaseModel):
    max_z: float = Field(default=1.2, description="Порог Z-score для нормализации (чувствительность)")
    use_semantic: bool = Field(default=True, description="Использовать векторные эмбеддинги")
    use_lexical: bool = Field(default=True, description="Использовать лексический анализ (Jaccard/Levenshtein)")
    min_similarity_threshold: float = Field(default=0.3, description="Минимальный порог сырого сходства для учета")


class LinterSettings(BaseModel):
    enabled_linters: list[str] = Field(
        default_factory=lambda: ["flake8", "cppcheck", "checkstyle"],
        description="Список активных линтеров"
    )
    linter_preset_id: int = Field(
        default=1, 
        description="ID пресета аргументов линтера (1: Default, 2: Strict, 3: Google Style, 4: Academic)"
    )
    custom_args: dict[str, str] = Field(
        default_factory=dict,
        description="Кастомные аргументы командной строки для линтеров (linter -> args)"
    )
    timeout_seconds: int = Field(default=30, description="Таймаут выполнения линтера")


class LLMSettings(BaseModel):
    prompt_preset_id: int = Field(default=3, description="ID готового пресета промпта (1-10)")
    strictness_level: int = Field(default=5, description="Уровень строгости ИИ (1-10) для слайдера на фронте")
    custom_instruction_1: Optional[str] = Field(default="", description="Дополнительная инструкция ИИ-ментору (слот 1)")
    custom_instruction_2: Optional[str] = Field(default="", description="Дополнительная инструкция ИИ-ментору (слот 2)")
    custom_instruction_3: Optional[str] = Field(default="", description="Дополнительная инструкция ИИ-ментору (слот 3)")
    review_mode: str = Field(
        default="socratic", 
        description="Стиль общения: 'socratic' (намеки) или 'direct' (объяснение ошибок)"
    )
    verbosity: str = Field(default="medium", description="Уровень подробности (low, medium, high)")
    temperature: float = Field(default=0.3, description="Temperature для генерации")
    max_tokens: int = Field(default=1500, description="Max tokens для ответа")


class CascadingSettings(BaseModel):
    plagiarism: PlagiarismSettings = Field(default_factory=PlagiarismSettings)
    linter: LinterSettings = Field(default_factory=LinterSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    
    submission_limit: int = Field(default=0, description="Максимальное количество попыток (0 - безлимитно)")
    view_results_after: Optional[datetime] = Field(
        default=None, 
        description="Дата и время, после которых результаты станут доступны ученику"
    )
    forbidden_patterns: list[str] = Field(
        default_factory=list,
        description="Список запрещенных regex-паттернов в коде"
    )
    auto_approve_threshold: Optional[float] = Field(
        default=None, 
        description="Порог оценки для автоматического одобрения (0.0 - 1.0)"
    )

    @classmethod
    def merge(cls, base: "CascadingSettings", override: dict) -> "CascadingSettings":
        """
        Выполняет глубокое слияние настроек. 
        base - базовые настройки (например, из курса).
        override - словарь с переопределениями (например, из задачи).
        """
        # Превращаем базовые настройки в словарь
        base_dict = base.model_dump()
        
        def deep_merge(target, source):
            for key, value in source.items():
                if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                    deep_merge(target[key], value)
                elif value is not None:
                    target[key] = value
            return target

        merged_dict = deep_merge(base_dict, override)
        return cls.model_validate(merged_dict)
