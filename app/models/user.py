import enum
import uuid
from typing import Optional, TYPE_CHECKING
from pydantic import EmailStr
from sqlmodel import SQLModel, Field, Relationship
from app.models.links import CourseUserLink

if TYPE_CHECKING:
    from .group import StudyGroup
    from .course import Course


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr = Field(unique=True, index=True)
    hashed_password: str
    full_name: str
    role: UserRole = Field(default=UserRole.student)

    group_id: Optional[uuid.UUID] = Field(default=None, foreign_key="studygroup.id")
    group: Optional["StudyGroup"] = Relationship(back_populates="users")

    courses: list["Course"] = Relationship(
        back_populates="users", link_model=CourseUserLink
    )
