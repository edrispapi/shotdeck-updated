import json
import logging
from kafka import KafkaProducer
from django.conf import settings

logger = logging.getLogger(__name__)

# یک نمونه Producer به صورت Singleton ایجاد می‌کنیم تا از ایجاد مکرر کانکشن جلوگیری شود.
try:
    producer = KafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        # مقادیر را به فرمت JSON و بایت تبدیل می‌کنیم
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    logger.info("Kafka Producer for image_service connected successfully.")
except Exception as e:
    # اگر Kafka در دسترس نباشد، برنامه نباید crash کند.
    logger.error(f"Could not connect Kafka Producer: {e}")
    producer = None

def send_event(topic, value):
    """
    یک تابع کمکی برای ارسال رویداد به یک تاپیک مشخص در Kafka.
    """
    if not producer:
        logger.error("Kafka Producer is not available. Message not sent.")
        return
        
    try:
        # ارسال پیام به تاپیک مورد نظر
        future = producer.send(topic, value=value)
        # منتظر می‌مانیم تا پیام با موفقیت ارسال شود (برای محیط توسعه خوب است)
        future.get(timeout=10)
        logger.info(f"Event sent to topic '{topic}': {value}")
    except Exception as e:
        logger.error(f"Failed to send event to Kafka topic '{topic}': {e}")