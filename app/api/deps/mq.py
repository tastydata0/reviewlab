from app.services.mq import broker, RabbitMQService


async def get_mq_service() -> RabbitMQService:
    return RabbitMQService(broker)
