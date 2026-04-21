import uuid
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON

if TYPE_CHECKING:
    from .course import Course
    from .task import Task


class TaskGroup(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    course_id: uuid.UUID = Field(foreign_key="course.id", index=True)
    name: str
    emoji: Optional[str] = Field(default=None)
    description: Optional[str] = None
    settings: dict = Field(default_factory=dict, sa_column=Column(JSON))

    course: "Course" = Relationship(back_populates="task_groups")
    tasks: list["Task"] = Relationship(back_populates="task_group")
