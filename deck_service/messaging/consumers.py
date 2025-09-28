# مسیر: deck_service/messaging/consumers.py
import json
import logging
from kafka import KafkaConsumer
from django.conf import settings
from apps.decks.models import Deck

logger = logging.getLogger(__name__)

def run_kafka_consumer():
    logger.info("Starting Kafka consumer for deck_service...")
    consumer = KafkaConsumer(
        'image_deleted',
        'user_created',
        'user_vip_activated',
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    for message in consumer:
        try:
            if message.topic == 'image_deleted':
                data = message.value
                image_slug = data.get('slug')
                if image_slug:
                    logger.info(f"Received event to delete image slug '{image_slug}' from all decks.")

                    # پیدا کردن تمام Deck هایی که این slug را دارند
                    decks_to_update = Deck.objects.filter(image_slugs__contains=image_slug)

                    # حذف slug از لیست هر Deck
                    for deck in decks_to_update:
                        if image_slug in deck.image_slugs:
                            deck.image_slugs.remove(image_slug)
                            deck.save()

                    logger.info(f"Finished cleaning up image slug '{image_slug}'.")

            elif message.topic == 'user_access_check':
                data = message.value
                user_uuid = data.get('user_uuid')
                page = data.get('page')
                timestamp = data.get('timestamp')
                logger.info(f"User access check: {user_uuid} - Page: {page} - Time: {timestamp}")

                # Here you can perform access control based on subscription
                # This will be handled by the subscription service

            elif message.topic == 'user_created':
                data = message.value
                user_id = data.get('user_id')
                phone_number = data.get('phone_number')
                logger.info(f"New user created: {user_id} - {phone_number}")

                # Here you can perform any deck-related actions for new users
                # For example, create a default deck for new users

            elif message.topic == 'user_vip_activated':
                data = message.value
                user_id = data.get('user_id')
                vip_token = data.get('vip_token')
                logger.info(f"User VIP activated: {user_id} - Token: {vip_token}")

                # Here you can perform actions when a user becomes VIP
                # For example, unlock premium decks or content

        except Exception as e:
            logger.error(f"Error processing Kafka message: {e}")