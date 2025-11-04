import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ImageIndexer:
    """Service for indexing images from image_service into deck_search Elasticsearch"""

    def __init__(self):
        from apps.indexer.client import image_service_client
        
        self.client = image_service_client
        self._ImageDocument = None
        self._setup_elasticsearch()

    @property
    def ImageDocument(self):
        if self._ImageDocument is None:
            from apps.search.documents import ImageDocument
            self._ImageDocument = ImageDocument
        return self._ImageDocument

    def _setup_elasticsearch(self):
        try:
            from django.conf import settings
            from elasticsearch_dsl import connections
            
            connections.create_connection(
                hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']],
                alias='default'
            )
            
            try:
                self.ImageDocument.init()
                logger.info("Elasticsearch connection established")
            except Exception as e:
                logger.warning(f"Index init skipped: {e}")
                
        except Exception as e:
            logger.error(f"Failed to setup Elasticsearch: {e}")
            raise

    def transform_image_data(self, image_data: Dict) -> Dict:
        try:
            transformed = {
                'id': image_data.get('id'),
                'slug': image_data.get('slug'),
                'title': image_data.get('title'),
                'description': image_data.get('description'),
                'image_url': image_data.get('image_url'),
                'release_year': image_data.get('release_year'),
            }
            
            option_fields = [
                'media_type', 'color', 'aspect_ratio', 'time_of_day',
                'interior_exterior', 'gender', 'lighting', 'lighting_type'
            ]
            
            for field in option_fields:
                value = image_data.get(field)
                transformed[field] = value.get('value') if isinstance(value, dict) else value
            
            return transformed
        except Exception as e:
            logger.error(f"Transform error: {e}")
            return None

    def index_image(self, image_data: Dict) -> bool:
        try:
            transformed = self.transform_image_data(image_data)
            if not transformed:
                return False
            
            doc = self.ImageDocument(meta={'id': transformed['id']}, **transformed)
            doc.save()
            logger.info(f"Indexed: {transformed.get('slug')}")
            return True
        except Exception as e:
            logger.error(f"Index error: {e}")
            return False

    def get_index_stats(self) -> Dict:
        try:
            return {
                'total_documents': self.ImageDocument.search().count(),
                'service_health': self.client.health_check()
            }
        except Exception as e:
            return {}


_indexer = None

def get_image_indexer():
    global _indexer
    if _indexer is None:
        _indexer = ImageIndexer()
    return _indexer
