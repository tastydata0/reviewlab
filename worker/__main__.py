import asyncio
import logging
import uuid
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from sqlmodel import select

from app.storage.postgres import async_session_maker
from app.models.submission import Submission, SubmissionStatus, CorrectnessSource
from app.models.task import Task
from app.settings import SETTINGS

from worker.services.static_analysis.main import StaticAnalysisService
from worker.services.llm_mentor.main import LLMMentorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vkr_worker")

broker = RabbitBroker(SETTINGS.RABBITMQ_URL)
app = FastStream(broker)

static_analysis_service = StaticAnalysisService()
llm_mentor_service = LLMMentorService()


@broker.subscriber("submission_tasks")
async def handle_submission(msg: dict):
    submission_id = msg["submission_id"]
    logger.info(f"Received submission {submission_id} via FastStream")

    async with async_session_maker() as session:
        submission = await session.get(Submission, uuid.UUID(submission_id))
        if not submission:
            logger.error(f"Submission {submission_id} not found")
            return

        submission.status = SubmissionStatus.PROCESSING
        session.add(submission)
        await session.commit()

        logger.info(f"Running analysis for submission {submission_id}...")

        linter_report = await static_analysis_service.analyze(
            source_code=submission.source_code, language=submission.language
        )
        if linter_report:
            submission.linter_report = linter_report

        statement = select(Task).where(Task.join_code == submission.task_id.upper())
        result = await session.execute(statement)
        task = result.scalars().first()
        task_description = (
            task.description
            if task and task.description
            else "Условие задачи не предоставлено."
        )

        # Fetch previous attempt for context
        prev_stmt = (
            select(Submission)
            .where(
                Submission.user_id == submission.user_id,
                Submission.task_id == submission.task_id,
                Submission.status == SubmissionStatus.PROCESSED,
                Submission.id != submission.id,
            )
            .order_by(Submission.timestamp.desc())
            .limit(1)
        )
        prev_result = await session.execute(prev_stmt)
        prev_submission = prev_result.scalars().first()

        mentor_response = await llm_mentor_service.analyze(
            source_code=submission.source_code,
            task_description=task_description,
            linter_report=linter_report,
            previous_source_code=(
                prev_submission.source_code if prev_submission else None
            ),
            previous_review=prev_submission.ai_review if prev_submission else None,
            previous_linter_report=(
                prev_submission.linter_report if prev_submission else None
            ),
        )

        if mentor_response:
            submission.ai_review = mentor_response.review
            submission.ai_score = mentor_response.score
            if submission.correctness is None:
                submission.correctness = mentor_response.correctness
                submission.correctness_source = CorrectnessSource.AI

        submission.status = SubmissionStatus.PROCESSED

        session.add(submission)
        await session.commit()
        logger.info(f"Finished processing submission {submission_id}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
