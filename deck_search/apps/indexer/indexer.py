import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from elasticsearch_dsl import connections
from apps.search.documents import ImageDocument
from .client import image_service_client

logger = logging.getLogger(__name__)


class ImageIndexer:
    """Service for indexing images from image_service into deck_search Elasticsearch"""

    def __init__(self):
        self.client = image_service_client
        self._setup_elasticsearch()

    def _setup_elasticsearch(self):
        """Setup Elasticsearch connection"""
        try:
            from django.conf import settings
            connections.create_connection(
                hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']],
                alias='default'
            )
            # Initialize index
            ImageDocument.init()
            logger.info("Elasticsearch connection established and index initialized")
        except Exception as e:
            logger.error(f"Failed to setup Elasticsearch: {e}")
            raise

    def transform_image_data(self, image_data: Dict) -> Dict:
        """Transform image data from image_service format to deck_search format"""
        try:
            # Base transformation
            transformed = {
                'id': image_data.get('id'),
                'slug': image_data.get('slug'),
                'title': image_data.get('title'),
                'description': image_data.get('description'),
                'image_url': image_data.get('image_url'),
                'release_year': image_data.get('release_year'),
                'exclude_nudity': image_data.get('exclude_nudity', False),
                'exclude_violence': image_data.get('exclude_violence', False),
                'created_at': image_data.get('created_at'),
                'updated_at': image_data.get('updated_at'),
            }

            # Handle option fields - these come as nested objects from API
            option_fields = [
                'media_type', 'color', 'aspect_ratio', 'optical_format', 'format',
                'interior_exterior', 'time_of_day', 'number_of_people', 'gender',
                'age', 'ethnicity', 'frame_size', 'shot_type', 'composition',
                'lens_size', 'lens_type', 'lighting', 'lighting_type', 'camera_type',
                'resolution', 'frame_rate', 'actor', 'camera', 'lens', 'location',
                'setting', 'film_stock', 'shot_time', 'description_filter', 'vfx_backing'
            ]

            for field_name in option_fields:
                field_value = image_data.get(field_name)
                if field_value and isinstance(field_value, dict):
                    transformed[field_name] = field_value.get('value')
                else:
                    transformed[field_name] = field_value

            # Handle genre - comes as list of objects
            genre_data = image_data.get('genre', [])
            if genre_data:
                transformed['genre'] = [g.get('value') if isinstance(g, dict) else g for g in genre_data]
            else:
                transformed['genre'] = []

            # Handle movie - comes as ID or nested object
            movie_data = image_data.get('movie')
            movie_value = image_data.get('movie_value')
            if movie_data:
                if isinstance(movie_data, dict):
                    # Movie comes as nested object
                    transformed['movie'] = {
                        'id': movie_data.get('id'),
                        'slug': movie_data.get('slug'),
                        'title': movie_data.get('title'),
                        'year': movie_data.get('year'),
                    }
                else:
                    # Movie comes as ID, construct object from available data
                    transformed['movie'] = {
                        'id': movie_data,
                        'title': movie_value or '',
                        'slug': '',
                        'year': image_data.get('release_year'),
                    }
            else:
                transformed['movie'] = {}

            # Handle tags - comes as list of objects
            tags_data = image_data.get('tags', [])
            transformed['tags'] = [
                {
                    'id': tag.get('id'),
                    'slug': tag.get('slug'),
                    'name': tag.get('name')
                }
                for tag in tags_data
            ]

            # Handle color analysis fields
            transformed.update({
                'dominant_colors': image_data.get('dominant_colors', []),
                'primary_color_hex': image_data.get('primary_color_hex'),
                'secondary_color_hex': image_data.get('secondary_color_hex'),
                'color_palette': image_data.get('color_palette', {}),
                'color_samples': image_data.get('color_samples', []),
                'color_histogram': image_data.get('color_histogram', {}),
                'primary_colors': image_data.get('primary_colors', []),
                'color_search_terms': image_data.get('color_search_terms', []),
                'color_temperature': image_data.get('color_temperature'),
                'hue_range': image_data.get('hue_range'),
            })

            return transformed

        except Exception as e:
            image_id = image_data.get('id') if isinstance(image_data, dict) else str(image_data)
            logger.error(f"Failed to transform image data for ID {image_id}: {e}")
            return None

    def index_image(self, image_data: Dict) -> bool:
        """Index a single image"""
        try:
            transformed_data = self.transform_image_data(image_data)
            if not transformed_data:
                return False

            # Create and save document
            doc = ImageDocument(
                meta={'id': transformed_data['id']},
                **transformed_data
            )
            doc.save()

            logger.info(f"Successfully indexed image: {transformed_data.get('slug')}")
            return True

        except Exception as e:
            logger.error(f"Failed to index image {image_data.get('id')}: {e}")
            return False

    def index_images_batch(self, images_data: List[Dict], batch_size: int = 50) -> int:
        """Index multiple images in batches"""
        total_indexed = 0

        for i in range(0, len(images_data), batch_size):
            batch = images_data[i:i + batch_size]
            batch_indexed = 0

            for image_data in batch:
                if self.index_image(image_data):
                    batch_indexed += 1
                    total_indexed += 1

            logger.info(f"Indexed batch {i//batch_size + 1}: {batch_indexed}/{len(batch)} images")

        return total_indexed

    def sync_all_images(self, batch_size: int = 100) -> int:
        """Sync all images from image_service"""
        logger.info("Starting full sync of all images")

        # Check if service is healthy
        if not self.client.health_check():
            logger.error("Image service is not healthy, aborting sync")
            return 0

        # Get all images
        images_data = self.client.get_all_images_paginated(batch_size=batch_size)
        logger.info(f"Retrieved {len(images_data)} images from image_service")

        if not images_data:
            logger.warning("No images retrieved from image_service")
            return 0

        # Index all images
        total_indexed = self.index_images_batch(images_data, batch_size=50)
        logger.info(f"Sync completed: {total_indexed}/{len(images_data)} images indexed")

        return total_indexed

    def sync_recent_images(self, hours_back: int = 24, batch_size: int = 100) -> int:
        """Sync images updated in the last N hours"""
        since_time = datetime.now() - timedelta(hours=hours_back)
        since_timestamp = since_time.isoformat()

        logger.info(f"Starting incremental sync for images updated since {since_timestamp}")

        # Get recent images
        images_data = self.client.get_recent_images(since_timestamp=since_timestamp, limit=batch_size)
        logger.info(f"Retrieved {len(images_data)} recently updated images")

        if not images_data:
            logger.info("No recently updated images found")
            return 0

        # Index recent images
        total_indexed = self.index_images_batch(images_data, batch_size=50)
        logger.info(f"Incremental sync completed: {total_indexed}/{len(images_data)} images indexed")

        return total_indexed

    def delete_image(self, image_id: int) -> bool:
        """Delete an image from the index"""
        try:
            doc = ImageDocument.get(id=image_id)
            doc.delete()
            logger.info(f"Successfully deleted image {image_id} from index")
            return True
        except Exception as e:
            logger.error(f"Failed to delete image {image_id}: {e}")
            return False

    def get_index_stats(self) -> Dict:
        """Get indexing statistics"""
        try:
            search = ImageDocument.search()
            total_docs = search.count()

            return {
                'total_documents': total_docs,
                'image_service_health': self.client.health_check(),
                'image_service_count': self.client.get_image_count(),
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}


# Global indexer instance
image_indexer = ImageIndexer()
