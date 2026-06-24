"""
Kafka Producer service for ShieldAI.
"""
import json
from aiokafka import AIOKafkaProducer
from config import settings
from logging_config import get_logger

logger = get_logger("shield_ai.kafka_producer")

class KafkaProducerService:
    def __init__(self):
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        logger.info("kafka_producer_started", servers=settings.KAFKA_BOOTSTRAP_SERVERS)

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("kafka_producer_stopped")

    async def publish(self, topic: str, message: dict):
        if not self.producer:
            await self.start()
        try:
            await self.producer.send_and_wait(topic, message)
            logger.info("message_published", topic=topic, keys=list(message.keys()))
        except Exception as e:
            logger.error("kafka_publish_failed", error=str(e), topic=topic)

# Singleton
producer_service = KafkaProducerService()
