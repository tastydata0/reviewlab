import uuid
import random
import string
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON

if TYPE_CHECKING:
    from .task_group import TaskGroup


def generate_join_code():
    # Генерируем короткий код вида A7X9Q
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


class Task(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_group_id: uuid.UUID = Field(foreign_key="taskgroup.id", index=True)
    name: str
    description: Optional[str] = None

    join_code: str = Field(default_factory=generate_join_code, unique=True, index=True)
    external_slug: Optional[str] = Field(default=None, index=True)

    settings: dict = Field(default_factory=dict, sa_column=Column(JSON))

    task_group: "TaskGroup" = Relationship(back_populates="tasks")


class TaskRead(SQLModel):
    id: uuid.UUID
    name: str
    join_code: str
    task_group_name: str
    course_name: str
