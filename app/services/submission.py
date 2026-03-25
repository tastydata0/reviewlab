import uuid
import logging
from typing import List, Optional
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

from app.models.submission import Submission, SubmissionStatus
from app.models.task import Task
from app.services.mq import RabbitMQService

logger = logging.getLogger(__name__)


class SubmissionService:
    def __init__(
        self, session: AsyncSession, mq_service: Optional[RabbitMQService] = None
    ):
        self.session = session
        self.mq_service = mq_service

    async def create_submission(
        self,
        user_id: uuid.UUID,
        task_id: str,
        source_code: dict[str, str],
        language: str = "python",
    ) -> Submission:
        statement = select(Task).where(Task.join_code == task_id.upper())
        result = await self.session.execute(statement)
        task = result.scalars().first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with join code {task_id} not found",
            )

        submission = Submission(
            user_id=user_id,
            task_id=task.join_code,
            source_code=source_code,
            language=language,
            status=SubmissionStatus.CREATED,
        )
        self.session.add(submission)
        await self.session.commit()
        await self.session.refresh(submission)

        if self.mq_service:
            await self.mq_service.publish_submission(str(submission.id))
        else:
            logger.warning(
                f"Submission {submission.id} created but no MQ service provided"
            )

        return submission

    async def get_user_submissions(self, user_id: uuid.UUID) -> List[Submission]:
        statement = (
            select(Submission)
            .where(Submission.user_id == user_id)
            .order_by(desc(Submission.timestamp))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_task_submissions(self, task_id: str) -> List[Submission]:
        statement = (
            select(Submission)
            .where(Submission.task_id == task_id.upper())
            .order_by(desc(Submission.timestamp))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_submission(self, submission_id: uuid.UUID) -> Submission:
        submission = await self.session.get(Submission, submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
            )
        return submission
