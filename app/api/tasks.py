import uuid
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.storage.postgres import get_session
from app.services.task import TaskService
from app.api.deps.auth import get_current_user_id, get_current_user_role
from app.models.task import TaskRead
from app.models.user import UserRole

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskRead])
async def get_my_tasks(
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: UserRole = Depends(get_current_user_role),
    session: AsyncSession = Depends(get_session),
):
    service = TaskService(session)
    return await service.get_available_tasks(user_id, role)
