import requests
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class ImageServiceClient:
    """Client for communicating with image_service API"""

    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = base_url or getattr(settings, 'IMAGE_SERVICE_URL', 'http://image_service:8000')
        self.timeout = timeout
        self.session = requests.Session()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make HTTP request to image_service"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            return None

    def get_image(self, image_id: int) -> Optional[Dict]:
        """Get single image by ID"""
        return self._make_request('GET', f'/api/images/{image_id}/')

    def get_images(self, params: Dict = None) -> Optional[Dict]:
        """Get list of images with optional filtering"""
        params = params or {}
        return self._make_request('GET', '/api/images/', params=params)

    def get_all_images_paginated(self, batch_size: int = 100) -> List[Dict]:
        """Get all images using pagination"""
        all_images = []
        page = 1

        while True:
            response = self.get_images({
                'page': page,
                'page_size': batch_size
            })

            if not response:
                break

            images = response.get('results', [])
            if not images:
                break

            all_images.extend(images)

            # Check if there are more pages
            if not response.get('next'):
                break

            page += 1
            logger.info(f"Fetched page {page-1}, total images so far: {len(all_images)}")

        return all_images

    def get_recent_images(self, since_timestamp: str = None, limit: int = None) -> List[Dict]:
        """Get images updated since a specific timestamp"""
        params = {}
        if since_timestamp:
            params['updated_at__gte'] = since_timestamp
        if limit:
            params['limit'] = limit

        response = self.get_images(params)
        if response:
            return response.get('results', [])
        return []

    def get_image_count(self) -> int:
        """Get total count of images"""
        response = self.get_images({'page_size': 1})
        if response:
            return response.get('count', 0)
        return 0

    def health_check(self) -> bool:
        """Check if image_service is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/api/health/", timeout=10)
            return response.status_code == 200
        except Exception:
            return False


# Global client instance
image_service_client = ImageServiceClient()
