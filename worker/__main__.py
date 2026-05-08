import asyncio
import logging
import uuid
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from sqlmodel import select
import datetime as dt

from app.storage.postgres import async_session_maker
from app.models.submission import Submission, SubmissionStatus, CorrectnessSource
from app.models.task import Task
from app.models.task_stats import TaskPlagiarismStats
from app.settings import SETTINGS

from worker.services.static_analysis.main import StaticAnalysisService
from worker.services.llm_mentor.main import LLMMentorService
from worker.services.plagiarism.main import PlagiarismService
from worker.utils.normalization.zscore import calculate_stats, normalize_zscore_value

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

broker = RabbitBroker(SETTINGS.RABBITMQ_URL)
app = FastStream(broker)

static_analysis_service = StaticAnalysisService()
llm_mentor_service = LLMMentorService()
plagiarism_service = PlagiarismService()


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

        # Static Analysis
        linter_report = await static_analysis_service.analyze(
            source_code=submission.source_code, language=submission.language
        )
        if linter_report:
            submission.linter_report = linter_report

        # Plagiarism Detection
        other_subs_stmt = select(Submission).where(
            Submission.task_id == submission.task_id,
            Submission.status == SubmissionStatus.PROCESSED,
            Submission.user_id != submission.user_id,
        )
        other_subs_result = await session.execute(other_subs_stmt)
        other_submissions = list(other_subs_result.scalars().all())

        plag_score, lex_sim, sem_sim, plag_matches = await plagiarism_service.analyze(
            current_submission=submission,
            other_submissions=other_submissions,
            language=submission.language,
        )
        submission.plagiarism_score = plag_score
        submission.lexical_similarity = lex_sim
        submission.semantic_similarity = sem_sim
        submission.plagiarism_matches = plag_matches
        submission.plagiarism_checked = True

        # Resolve Task early to get real UUID
        task_stmt = select(Task).where(Task.join_code == submission.task_id.upper())
        task_res = await session.execute(task_stmt)
        task = task_res.scalars().first()
        task_id_uuid = task.id if task else None

        # Z-score Normalization: Recalculate for ALL submissions of this task
        all_task_subs_stmt = select(Submission).where(
            Submission.task_id == submission.task_id,
            Submission.status == SubmissionStatus.PROCESSED,
        )
        all_task_subs_result = await session.execute(all_task_subs_stmt)
        all_task_subs = list(all_task_subs_result.scalars().all())

        # Include current submission in the pool for normalization
        pool = all_task_subs + [submission]
        scores = [s.plagiarism_score for s in pool]

        # Calculate global stats for the task
        mean, std_dev = calculate_stats(scores)

        # Update/Create TaskPlagiarismStats using UUID
        if task_id_uuid:
            stats = await session.get(TaskPlagiarismStats, task_id_uuid)
            if not stats:
                stats = TaskPlagiarismStats(task_id=task_id_uuid)

            stats.mean = mean
            stats.std_dev = std_dev
            stats.updated_at = dt.datetime.now()
            session.add(stats)

        # Update Z-scores for all submissions in pool using new stats
        for sub_in_pool in pool:
            sub_in_pool.plagiarism_score_z = normalize_zscore_value(
                sub_in_pool.plagiarism_score, mean, std_dev
            )
            session.add(sub_in_pool)

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
