import json
import logging

logger = logging.getLogger(__name__)


def run_kafka_consumer():
    from django.conf import settings
    from kafka import KafkaConsumer
    from apps.indexer.indexer import get_image_indexer
    
    logger.info("Starting Kafka consumer...")
    indexer = get_image_indexer()
    
    consumer = KafkaConsumer(
        settings.KAFKA_IMAGE_CREATED_TOPIC,
        settings.KAFKA_IMAGE_UPDATED_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    for message in consumer:
        try:
            data = message.value
            indexer.index_image(data)
        except Exception as e:
            logger.error(f"Kafka error: {e}")
