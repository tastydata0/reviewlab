import uuid
from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

from app.models.course import Course
from app.models.user import User
from app.models.links import CourseUserLink
from app.utils.emojis import get_random_course_emoji


class CourseService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_course(
        self,
        name: str,
        teacher_id: uuid.UUID,
        description: Optional[str] = None,
        emoji: Optional[str] = None,
    ) -> Course:
        if not emoji:
            emoji = get_random_course_emoji()
        course = Course(
            name=name, teacher_id=teacher_id, description=description, emoji=emoji
        )
        self.session.add(course)
        await self.session.commit()
        await self.session.refresh(course)
        return course

    async def get_course(self, course_id: uuid.UUID) -> Course:
        course = await self.session.get(Course, course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )
        return course

    async def update_course(
        self,
        course_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Course:
        course = await self.get_course(course_id)
        if name:
            course.name = name
        if description:
            course.description = description
        self.session.add(course)
        await self.session.commit()
        await self.session.refresh(course)
        return course

    async def get_teacher_courses(self, teacher_id: uuid.UUID) -> list[Course]:
        statement = select(Course).where(Course.teacher_id == teacher_id)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def add_user_to_course(self, course_id: uuid.UUID, user_id: uuid.UUID):
        statement = select(CourseUserLink).where(
            CourseUserLink.course_id == course_id, CourseUserLink.user_id == user_id
        )
        result = await self.session.execute(statement)
        if not result.scalars().first():
            link = CourseUserLink(course_id=course_id, user_id=user_id)
            self.session.add(link)
            await self.session.commit()

    async def remove_user_from_course(self, course_id: uuid.UUID, user_id: uuid.UUID):
        statement = select(CourseUserLink).where(
            CourseUserLink.course_id == course_id, CourseUserLink.user_id == user_id
        )
        result = await self.session.execute(statement)
        link = result.scalars().first()
        if link:
            await self.session.delete(link)
            await self.session.commit()

    async def add_group_to_course(self, course_id: uuid.UUID, group_id: uuid.UUID):
        # Get all users in group
        statement = select(User).where(User.group_id == group_id)
        result = await self.session.execute(statement)
        users = result.scalars().all()

        for user in users:
            link_statement = select(CourseUserLink).where(
                CourseUserLink.course_id == course_id, CourseUserLink.user_id == user.id
            )
            link_result = await self.session.execute(link_statement)
            if not link_result.scalars().first():
                self.session.add(CourseUserLink(course_id=course_id, user_id=user.id))

        await self.session.commit()

    async def get_course_users(self, course_id: uuid.UUID) -> list[User]:
        subquery = select(CourseUserLink.user_id).where(
            CourseUserLink.course_id == course_id
        )
        statement = select(User).where(User.id.in_(subquery))
        result = await self.session.execute(statement)
        users = result.scalars().all()
        print(
            f"DEBUG: get_course_users returned {len(users)} users. First item type: {type(users[0]) if users else 'N/A'}"
        )
        return users
