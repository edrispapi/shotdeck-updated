import json
import logging
from kafka import KafkaConsumer
from django.conf import settings
from elasticsearch_dsl import Index
from core_apps.images.documents import ImageDocument

logger = logging.getLogger(__name__)

def run_kafka_consumer():
    """
    یک Consumer که به طور دائم به تاپیک‌های Kafka گوش می‌دهد و
    ایندکس Elasticsearch را بر اساس رویدادها به‌روز می‌کند.
    """
    logger.info("Starting Kafka consumer for search_service...")
    consumer = KafkaConsumer(
        'image_created', 'image_updated', 'image_deleted',
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        auto_offset_reset='earliest', # شروع از اولین پیام در صورت نبود offset
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    images_index = Index('images')

    for message in consumer:
        logger.info(f"Received message from topic '{message.topic}'")
        data = message.value

        try:
            if message.topic in ['image_created', 'image_updated']:
                logger.info(f"Indexing document with ID: {data['id']}")
                # ایجاد یا به‌روزرسانی داکیومنت در Elasticsearch
                ImageDocument.init(index='images')
                doc = ImageDocument(meta={'id': data['id']}, **data)
                doc.save()
                logger.info(f"Document {data['id']} indexed successfully.")

            elif message.topic == 'image_deleted':
                image_id = data.get('id')
                if image_id:
                    logger.info(f"Deleting document with ID: {image_id}")
                    # حذف داکیومنت از Elasticsearch
                    ImageDocument.get(id=image_id, index='images').delete()
                    logger.info(f"Document {image_id} deleted successfully.")
        except Exception as e:
            logger.error(f"Error processing message from topic {message.topic}: {e}")