import json
import logging
import os
import django
from kafka import KafkaConsumer
from django.conf import settings
from apps.search.documents import ImageDocument

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

logger = logging.getLogger(__name__)

def run_kafka_consumer():
    logger.info("Starting Kafka consumer for deck_search...")

    # Get topic names from environment variables with fallbacks
    image_created_topic = getattr(settings, 'KAFKA_IMAGE_CREATED_TOPIC', 'image_created')
    image_updated_topic = getattr(settings, 'KAFKA_IMAGE_UPDATED_TOPIC', 'image_updated')
    image_deleted_topic = getattr(settings, 'KAFKA_IMAGE_DELETED_TOPIC', 'image_deleted')

    try:
        consumer = KafkaConsumer(
            image_created_topic,
            image_updated_topic,
            image_deleted_topic,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=getattr(settings, 'KAFKA_CONSUMER_GROUP', 'deck_search_consumer_group'),
            auto_offset_reset='earliest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        logger.info("Kafka consumer connected successfully.")
    except Exception as e:
        logger.error(f"Could not connect Kafka consumer: {e}")
        return

    try:
        ImageDocument.init(index='images')
        logger.info("Elasticsearch index 'images' initialized.")
    except Exception as e:
        logger.error(f"Error initializing Elasticsearch index: {e}")

    for message in consumer:
        logger.info(f"Received message from topic '{message.topic}' with value: {message.value}")
        data = message.value

        try:
            if message.topic in [image_created_topic, image_updated_topic]:
                image_id = data.get('id')
                if not image_id:
                    logger.warning("Received message without an ID. Skipping.")
                    continue

                doc = ImageDocument(
                    meta={'id': image_id},
                    id=data.get('id'),
                    slug=data.get('slug'),
                    title=data.get('title'),
                    description=data.get('description'),
                    image_url=data.get('image_url'),
                    release_year=data.get('release_year'),
                    movie=data.get('movie'),
                    tags=data.get('tags', []),
                    media_type=data.get('media_type'),
                    genre=data.get('genre'),
                    color=data.get('color'),
                    aspect_ratio=data.get('aspect_ratio'),
                    optical_format=data.get('optical_format'),
                    format=data.get('format'),
                    interior_exterior=data.get('interior_exterior'),
                    time_of_day=data.get('time_of_day'),
                    number_of_people=data.get('number_of_people'),
                    gender=data.get('gender'),
                    age=data.get('age'),
                    ethnicity=data.get('ethnicity'),
                    frame_size=data.get('frame_size'),
                    shot_type=data.get('shot_type'),
                    composition=data.get('composition'),
                    lens_size=data.get('lens_size'),
                    lens_type=data.get('lens_type'),
                    lighting=data.get('lighting'),
                    lighting_type=data.get('lighting_type'),
                    camera_type=data.get('camera_type'),
                    resolution=data.get('resolution'),
                    frame_rate=data.get('frame_rate'),
                    exclude_nudity=data.get('exclude_nudity', False),
                    exclude_violence=data.get('exclude_violence', False),
                    # Enhanced color analysis fields
                    dominant_colors=data.get('dominant_colors', []),
                    primary_color_hex=data.get('primary_color_hex'),
                    secondary_color_hex=data.get('secondary_color_hex'),
                    color_palette=data.get('color_palette'),
                    color_samples=data.get('color_samples', []),
                    color_histogram=data.get('color_histogram'),
                    primary_colors=data.get('primary_colors', []),
                    color_search_terms=data.get('color_search_terms', []),
                    created_at=data.get('created_at'),
                    updated_at=data.get('updated_at')
                )
                doc.save(index='images')
                logger.info(f"Document {image_id} indexed successfully.")

            elif message.topic == image_deleted_topic:
                image_id = data.get('id')
                if image_id:
                    try:
                        ImageDocument.get(id=image_id, index='images').delete()
                        logger.info(f"Document {image_id} deleted successfully.")
                    except Exception as e:
                        logger.error(f"Could not delete document {image_id}. Error: {e}")

        except Exception as e:
            logger.error(f"Error processing message from topic {message.topic}: {e}")