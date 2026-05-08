import uuid
import datetime as dt
from sqlmodel import SQLModel, Field


class TaskPlagiarismStats(SQLModel, table=True):
    """
    Таблица для хранения коэффициентов нормализации (mean, std_dev) для каждой задачи.
    Позволяет динамически вычислять Z-score для любой посылки без обращения ко всем данным.
    """
    task_id: uuid.UUID = Field(primary_key=True) # Соответствует Task.id (UUID)
    mean: float = Field(default=0.0)
    std_dev: float = Field(default=0.0)
    updated_at: dt.datetime = Field(default_factory=dt.datetime.now)
