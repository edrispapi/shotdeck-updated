from django.db import ProgrammingError
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

def prepare_image_data(image):
    """Prepare image data for indexing"""
    try:
        # Convert image to dictionary with all fields
        image_data = {
            'id': image.id,
            'slug': image.slug,
            'title': image.title,
            'description': image.description,
            'image_url': image.image_url,
            'release_year': image.release_year,
            'exclude_nudity': image.exclude_nudity,
            'exclude_violence': image.exclude_violence,
            'created_at': image.created_at.isoformat() if image.created_at else None,
            'updated_at': image.updated_at.isoformat() if image.updated_at else None,
        }

        # Handle option fields (ForeignKey to option models)
        option_fields = [
            'media_type', 'color', 'aspect_ratio', 'optical_format', 'format',
            'interior_exterior', 'time_of_day', 'number_of_people', 'gender',
            'age', 'ethnicity', 'frame_size', 'shot_type', 'composition',
            'lens_size', 'lens_type', 'lighting', 'lighting_type', 'camera_type',
            'resolution', 'frame_rate', 'actor', 'camera', 'lens', 'location',
            'setting', 'film_stock', 'shot_time', 'description_filter', 'vfx_backing'
        ]

        for field_name in option_fields:
            field_value = getattr(image, field_name, None)
            if field_value:
                image_data[field_name] = field_value.value if hasattr(field_value, 'value') else str(field_value)
            else:
                image_data[field_name] = None

        # Handle genre (ManyToManyField)
        genres = []
        if hasattr(image, 'genre'):
            try:
                if image.genre.exists():
                    genres = [genre.value for genre in image.genre.all()]
            except ProgrammingError:
                logger.warning("Genre relation unavailable; skipping genre data during indexing.")
        image_data['genre'] = genres

        # Add movie data if exists
        if image.movie:
            image_data['movie'] = {
                'id': image.movie.id,
                'slug': image.movie.slug,
                'title': image.movie.title,
                'year': image.movie.year,
            }
        else:
            image_data['movie'] = {}

        # Add tags data
        try:
            image_data['tags'] = [
                {'id': tag.id, 'slug': tag.slug, 'name': tag.name}
                for tag in image.tags.all()
            ]
        except ProgrammingError:
            logger.warning("Tag relation unavailable; skipping tag data during indexing.")
            image_data['tags'] = []

        # Add color analysis fields
        image_data.update({
            'dominant_colors': image.dominant_colors or [],
            'primary_color_hex': image.primary_color_hex,
            'secondary_color_hex': image.secondary_color_hex,
            'color_palette': image.color_palette or {},
            'color_samples': image.color_samples or [],
            'color_histogram': image.color_histogram or {},
            'primary_colors': image.primary_colors or [],
            'color_search_terms': image.color_search_terms or [],
            'color_temperature': getattr(image, 'color_temperature', None),
            'hue_range': getattr(image, 'hue_range', None),
        })

        return image_data

    except Exception as e:
        logger.error(f"Failed to prepare image data for {image.slug}: {e}")
        return None

def index_image(es_client, image):
    """Index a single image in Elasticsearch"""
    try:
        image_data = prepare_image_data(image)
        if not image_data:
            return False

        # Index the document
        es_client.index(
            index='images',
            id=image.id,
            body=image_data,
            refresh=True  # Make it immediately available for search
        )

        logger.info(f"Successfully indexed image: {image.slug}")
        return True

    except Exception as e:
        logger.error(f"Failed to index image {image.slug}: {e}")
        return False

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
