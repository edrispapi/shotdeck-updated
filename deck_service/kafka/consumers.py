# مسیر: deck_service/kafka/consumers.py
import json
import logging
from kafka import KafkaConsumer
from django.conf import settings
# from apps.decks.models import User # اگر مدل User سفارشی داشتید

logger = logging.getLogger(__name__)

def run_kafka_consumer():
    logger.info("Starting Kafka consumer for deck_service...")
    consumer = KafkaConsumer(
        *settings.KAFKA_TOPICS_TO_CONSUME,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        auto_offset_reset='earliest',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    for message in consumer:
        logger.info(f"Received message from topic {message.topic}: {message.value}")
        
        if message.topic == 'user_created':
            # منطق ایجاد کاربر در این سرویس
            # User.objects.create_user(...)
            pass
        
        elif message.topic == 'image_deleted':
            # منطق حذف ID تصویر از تمام Deck ها
            image_id = message.value.get('id')
            if image_id:
                # from apps.decks.models import Deck
                # decks_to_update = Deck.objects.filter(image_ids__contains=[image_id])
                # for deck in decks_to_update:
                #     deck.image_ids.remove(image_id)
                #     deck.save()
                logger.info(f"Removed image ID {image_id} from all relevant decks.")