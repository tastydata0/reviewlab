import asyncio
import logging
import uuid
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from app.storage.postgres import async_session_maker
from app.models.submission import Submission, SubmissionStatus
from app.settings import SETTINGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vkr_worker")

broker = RabbitBroker(SETTINGS.RABBITMQ_URL)
app = FastStream(broker)


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
        await asyncio.sleep(5)

        submission.status = SubmissionStatus.PROCESSED
        session.add(submission)
        await session.commit()
        logger.info(f"Finished processing submission {submission_id}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
