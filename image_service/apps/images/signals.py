from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Image
from elasticsearch import Elasticsearch
import json
import logging

logger = logging.getLogger(__name__)

def get_elasticsearch_client():
    """Get Elasticsearch client"""
    try:
        es = Elasticsearch(['http://elasticsearch:9200'])
        return es if es.ping() else None
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        return None

def index_image(es_client, image):
    """Index a single image in Elasticsearch"""
    try:
        # Convert image to dictionary
        image_data = {
            'id': image.id,
            'slug': image.slug,
            'title': image.title,
            'description': image.description,
            'image_url': image.image_url,
            'release_year': image.release_year,
            'media_type': image.media_type,
            'genre': image.genre,
            'color': image.color,
            'aspect_ratio': image.aspect_ratio,
            'optical_format': image.optical_format,
            'format': image.format,
            'interior_exterior': image.interior_exterior,
            'time_of_day': image.time_of_day,
            'number_of_people': image.number_of_people,
            'gender': image.gender,
            'age': image.age,
            'ethnicity': image.ethnicity,
            'frame_size': image.frame_size,
            'shot_type': image.shot_type,
            'composition': image.composition,
            'lens_size': image.lens_size,
            'lens_type': image.lens_type,
            'lighting': image.lighting,
            'lighting_type': image.lighting_type,
            'camera_type': image.camera_type,
            'resolution': image.resolution,
            'frame_rate': image.frame_rate,
            'exclude_nudity': image.exclude_nudity,
            'exclude_violence': image.exclude_violence,
            'created_at': image.created_at.isoformat(),
            'updated_at': image.updated_at.isoformat(),
        }

        # Add movie data if exists
        if image.movie:
            image_data['movie'] = {
                'id': image.movie.id,
                'slug': image.movie.slug,
                'title': image.movie.title,
                'year': image.movie.year,
            }

        # Add tags data
        image_data['tags'] = [
            {'id': tag.id, 'slug': tag.slug, 'name': tag.name}
            for tag in image.tags.all()
        ]

        # Index the document
        es_client.index(
            index='images',
            id=image.id,
            body=image_data,
            refresh=True  # Make it immediately available for search
        )

        logger.info(f"Successfully indexed image: {image.slug}")

    except Exception as e:
        logger.error(f"Failed to index image {image.slug}: {e}")

def delete_image_from_index(es_client, image_id):
    """Delete an image from Elasticsearch index"""
    try:
        es_client.delete(
            index='images',
            id=image_id,
            refresh=True
        )
        logger.info(f"Successfully deleted image from index: {image_id}")
    except Exception as e:
        logger.error(f"Failed to delete image from index {image_id}: {e}")

@receiver(post_save, sender=Image)
def image_post_save(sender, instance, created, **kwargs):
    """Handle image creation and updates"""
    es_client = get_elasticsearch_client()
    if es_client:
        if created:
            logger.info(f"Indexing new image: {instance.slug}")
        else:
            logger.info(f"Re-indexing updated image: {instance.slug}")
        index_image(es_client, instance)

@receiver(post_delete, sender=Image)
def image_post_delete(sender, instance, **kwargs):
    """Handle image deletion"""
    es_client = get_elasticsearch_client()
    if es_client:
        logger.info(f"Deleting image from index: {instance.slug}")
        delete_image_from_index(es_client, instance.id)