import uuid
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

from app.models.links import CourseUserLink

if TYPE_CHECKING:
    from .user import User
    from .task_group import TaskGroup


class Course(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    emoji: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    teacher_id: uuid.UUID = Field(foreign_key="user.id")

    users: list["User"] = Relationship(
        back_populates="courses", link_model=CourseUserLink
    )
    task_groups: list["TaskGroup"] = Relationship(back_populates="course")

    @property
    def name_with_emoji(self) -> str:
        return f"{self.emoji} {self.name}"
