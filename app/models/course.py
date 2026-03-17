import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

from app.models.links import CourseUserLink

if TYPE_CHECKING:
    from .user import User
    from .task_group import TaskGroup


class Course(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    teacher_id: uuid.UUID = Field(foreign_key="user.id")

    users: List["User"] = Relationship(
        back_populates="courses", link_model=CourseUserLink
    )
    task_groups: List["TaskGroup"] = Relationship(back_populates="course")
