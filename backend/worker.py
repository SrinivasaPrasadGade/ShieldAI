"""
Kafka Consumer worker for ShieldAI.
Runs as a standalone process to consume background tasks from Kafka.
"""
import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer

from config import settings
from logging_config import setup_logging, get_logger
from services.currency_analyzer import get_currency_analyzer
from services.graph_service import get_graph_service

logger = get_logger("shield_ai.worker")

async def process_currency_task(message):
    task_data = message.value
    task_id = task_data.get("task_id")
    file_url = task_data.get("file_url")
    denomination = task_data.get("denomination")
    location = task_data.get("location")
    
    logger.info("processing_currency_task", task_id=task_id)
    analyzer = get_currency_analyzer()
    # Modify analyzer.run_verification to accept file_url instead of reading from memory
    await analyzer.run_verification(task_id, file_url=file_url, denomination=denomination, location=location)

async def process_evidence_task(message):
    task_data = message.value
    task_id = task_data.get("task_id")
    cluster_id = task_data.get("cluster_id")
    
    logger.info("processing_evidence_task", task_id=task_id, cluster_id=cluster_id)
    from services.evidence_service import get_evidence_service
    evidence_svc = get_evidence_service()
    await evidence_svc.generate_evidence_package(cluster_id, task_id)

async def consume():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_CURRENCY,
        settings.KAFKA_TOPIC_EVIDENCE,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="shieldai_worker_group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    await consumer.start()
    logger.info("worker_started", topics=[settings.KAFKA_TOPIC_CURRENCY, settings.KAFKA_TOPIC_EVIDENCE])
    
    try:
        async for message in consumer:
            logger.info("message_received", topic=message.topic, partition=message.partition)
            if message.topic == settings.KAFKA_TOPIC_CURRENCY:
                asyncio.create_task(process_currency_task(message))
            elif message.topic == settings.KAFKA_TOPIC_EVIDENCE:
                asyncio.create_task(process_evidence_task(message))
    finally:
        await consumer.stop()

if __name__ == "__main__":
    setup_logging()
    asyncio.run(consume())
