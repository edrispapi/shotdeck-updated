import json
import logging
from kafka import KafkaConsumer
from django.conf import settings
from apps.indexer.indexer import image_indexer

logger = logging.getLogger(__name__)

def run_kafka_consumer():
    logger.info("Starting Kafka consumer for deck_search...")
    consumer = KafkaConsumer(
        settings.KAFKA_IMAGE_CREATED_TOPIC,
        settings.KAFKA_IMAGE_UPDATED_TOPIC,
        settings.KAFKA_IMAGE_DELETED_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    for message in consumer:
        try:
            data = message.value
            if message.topic == settings.KAFKA_IMAGE_CREATED_TOPIC:
                logger.info(f"Received image_created event: {data}")
                image_indexer.index_image(data)
            elif message.topic == settings.KAFKA_IMAGE_UPDATED_TOPIC:
                logger.info(f"Received image_updated event: {data}")
                image_indexer.index_image(data)
            elif message.topic == settings.KAFKA_IMAGE_DELETED_TOPIC:
                logger.info(f"Received image_deleted event: {data}")
                image_id = data.get('id')
                if image_id:
                    image_indexer.delete_image(image_id)
        except Exception as e:
            logger.error(f"Error processing Kafka message: {e}")
