# مسیر: /home/mdk/Documents/shotdeck-main/search_service/messaging/consumers.py
import json
import logging
from kafka import KafkaConsumer
from django.conf import settings
from apps.search.documents import ImageDocument

logger = logging.getLogger(__name__)

def run_kafka_consumer():
    """
    یک Kafka Consumer که به طور دائم به تاپیک‌های مربوط به تصاویر گوش می‌دهد
    و ایندکس Elasticsearch را بر اساس رویدادهای دریافتی به‌روز می‌کند.
    """
    logger.info("Starting Kafka consumer for search_service...")
    
    try:
        consumer = KafkaConsumer(
            'image_created', 
            'image_updated', 
            'image_deleted',
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset='earliest', # از اولین پیام موجود در تاپیک شروع می‌کند
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        logger.info("Kafka consumer connected successfully. Listening for messages...")
    except Exception as e:
        logger.error(f"Could not connect Kafka consumer: {e}")
        return # در صورت عدم اتصال، از حلقه خارج می‌شود

    for message in consumer:
        logger.info(f"Received message from topic '{message.topic}' with value: {message.value}")
        data = message.value

        try:
            if message.topic in ['image_created', 'image_updated']:
                image_id = data.get('id')
                if not image_id:
                    logger.warning("Received message without an ID. Skipping.")
                    continue
                
                logger.info(f"Indexing document with ID: {image_id}")
                # ایجاد یا به‌روزرسانی داکیومنت در Elasticsearch
                # ما از meta={'id': ...} استفاده می‌کنیم تا ID داکیومنت در Elasticsearch
                # با ID آبجکت در دیتابیس اصلی یکی باشد.
                doc = ImageDocument(meta={'id': image_id}, **data)
                doc.save(index='images')
                logger.info(f"Document {image_id} indexed/updated successfully.")

            elif message.topic == 'image_deleted':
                image_id = data.get('id')
                if image_id:
                    logger.info(f"Deleting document with ID: {image_id}")
                    try:
                        doc_to_delete = ImageDocument.get(id=image_id, index='images')
                        doc_to_delete.delete()
                        logger.info(f"Document {image_id} deleted successfully.")
                    except Exception as e:
                        logger.error(f"Could not delete document {image_id}. It might not exist. Error: {e}")

        except Exception as e:
            logger.error(f"Error processing message from topic {message.topic}: {e}")