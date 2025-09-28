import json
import logging
from kafka import KafkaProducer
from django.conf import settings

logger = logging.getLogger(__name__)

producer = None

def get_kafka_producer():
    """Lazy initialization of Kafka producer to avoid connection issues on startup"""
    global producer

    # Check if Kafka is enabled in settings
    if not getattr(settings, 'KAFKA_ENABLED', False):
        logger.info("Kafka is disabled in settings - skipping producer initialization")
        return None

    if producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers=getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', ['localhost:9092']),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3,
                request_timeout_ms=30000,
                max_block_ms=30000
            )
            logger.info("Kafka Producer for image_service connected successfully.")
        except Exception as e:
            logger.warning(f"Could not connect Kafka Producer (this is OK for development): {e}")
            producer = None
    return producer


def send_event(topic, value):
    producer = get_kafka_producer()
    if not producer:
        logger.debug("Kafka Producer is not available. Message not sent (this is OK).")
        return

    try:
        key = str(value.get("id")).encode() if value.get("id") else None
        future = producer.send(topic, key=key, value=value)

        if getattr(settings, 'DEBUG', False):
            future.get(timeout=30)

        logger.info(f"Event sent to topic '{topic}' with key '{key}': {value}")
    except Exception as e:
        logger.error(f"Failed to send event to Kafka topic '{topic}': {e}")
