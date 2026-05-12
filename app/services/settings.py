import uuid
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.task import Task
from app.models.task_group import TaskGroup
from app.models.course import Course
from app.schemas.settings import CascadingSettings


async def get_effective_settings(session: AsyncSession, task_id: uuid.UUID) -> CascadingSettings:
    """
    Вычисляет итоговые настройки для конкретной задачи, 
    учитывая иерархию наследования: Course -> TaskGroup -> Task.
    """
    # Загружаем задачу со всей цепочкой родителей
    statement = (
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.task_group)
            .selectinload(TaskGroup.course)
        )
    )
    result = await session.execute(statement)
    task = result.scalars().first()
    
    if not task:
        # Если задача не найдена, возвращаем дефолтные настройки
        return CascadingSettings()
    
    # 1. Берем настройки из Курса (база)
    course_settings_dict = task.task_group.course.settings or {}
    effective = CascadingSettings.model_validate(course_settings_dict)
    
    # 2. Накладываем переопределения из Группы задач
    group_settings_dict = task.task_group.settings or {}
    effective = CascadingSettings.merge(effective, group_settings_dict)
    
    # 3. Накладываем переопределения из самой Задачи
    task_settings_dict = task.settings or {}
    effective = CascadingSettings.merge(effective, task_settings_dict)
    
    return effective
