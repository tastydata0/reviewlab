from typing import Any
from pydantic import BaseModel, Field


class CodeSubmission(BaseModel):
    """
    модель, описывающая единицу исходного кода, переданную на проверку
    """

    id: int | str = Field(description="Уникальный идентификатор посылки")
    code: str
    user_id: str | None = None
    task_id: str | None = None


class PlagiarismMatch(BaseModel):
    """
    модель, описывающая ребро в графе заимствований. насколько коды схожи между собой
    """

    source_id: int | str
    target_id: int | str
    score: float = Field(description="Процент заимствования")
    details: dict[str, Any] | None = Field(
        default=None,
    )
