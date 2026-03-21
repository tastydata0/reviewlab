import uuid
from typing import List, Optional
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

from app.models.task_group import TaskGroup
from app.models.task import Task


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

    async def get_course_task_groups(self, course_id: uuid.UUID) -> List[TaskGroup]:
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
