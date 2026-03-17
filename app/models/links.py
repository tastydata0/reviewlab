import uuid
from sqlmodel import SQLModel, Field

class CourseUserLink(SQLModel, table=True):
    course_id: uuid.UUID = Field(foreign_key="course.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
