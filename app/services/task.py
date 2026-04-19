import uuid
from typing import Optional
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

from app.models.task_group import TaskGroup
from app.models.task import Task, TaskRead
from app.models.course import Course
from app.models.links import CourseUserLink
from app.models.user import UserRole


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task_group(
        self, course_id: uuid.UUID, name: str, description: Optional[str] = None
    ) -> TaskGroup:
        group = TaskGroup(course_id=course_id, name=name, description=description)
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def get_course_task_groups(self, course_id: uuid.UUID) -> list[TaskGroup]:
        statement = select(TaskGroup).where(TaskGroup.course_id == course_id)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_task_group(self, group_id: uuid.UUID) -> TaskGroup:
        # Load with tasks
        statement = (
            select(TaskGroup)
            .where(TaskGroup.id == group_id)
            .options(selectinload(TaskGroup.tasks))
        )
        result = await self.session.execute(statement)
        group = result.scalars().first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Laboratory work not found",
            )
        return group

    async def create_task(
        self,
        task_group_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        external_slug: Optional[str] = None,
    ) -> Task:
        task = Task(
            task_group_id=task_group_id,
            name=name,
            description=description,
            external_slug=external_slug,
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_task_by_join_code(self, join_code: str) -> Task:
        statement = select(Task).where(Task.join_code == join_code.upper())
        result = await self.session.execute(statement)
        task = result.scalars().first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        return task

    async def get_task(self, task_id: uuid.UUID) -> Task:
        task = await self.session.get(Task, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        return task

    async def update_task(
        self,
        task_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
    ) -> Task:
        task = await self.get_task(task_id)
        task.name = name
        task.description = description
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_available_tasks(
        self, user_id: uuid.UUID, role: UserRole
    ) -> list[TaskRead]:
        if role in (UserRole.teacher, UserRole.admin):
            # Tasks from courses where user is teacher
            statement = (
                select(Task, TaskGroup.name, Course.name)
                .join(TaskGroup, Task.task_group_id == TaskGroup.id)
                .join(Course, TaskGroup.course_id == Course.id)
                .where(Course.teacher_id == user_id)
            )
        else:
            # Tasks from courses where student is enrolled
            statement = (
                select(Task, TaskGroup.name, Course.name)
                .join(TaskGroup, Task.task_group_id == TaskGroup.id)
                .join(Course, TaskGroup.course_id == Course.id)
                .join(CourseUserLink, Course.id == CourseUserLink.course_id)
                .where(CourseUserLink.user_id == user_id)
            )

        result = await self.session.execute(statement)
        tasks = []
        for task, tg_name, c_name in result.all():
            tasks.append(
                TaskRead(
                    id=task.id,
                    name=task.name,
                    join_code=task.join_code,
                    task_group_name=tg_name,
                    course_name=c_name,
                )
            )
        return tasks
