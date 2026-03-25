import logging
from faststream.rabbit import RabbitBroker
from app.settings import SETTINGS

logger = logging.getLogger(__name__)

broker = RabbitBroker(SETTINGS.RABBITMQ_URL)


class RabbitMQService:
    def __init__(self, broker: RabbitBroker = broker):
        self._broker = broker

    async def publish_submission(self, submission_id: str):
        await self._broker.publish(
            {"submission_id": submission_id}, queue="submission_tasks"
        )
        logger.info(f"Published submission {submission_id} to queue via FastStream")
