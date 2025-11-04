# /home/a/shotdeck-main/deck_search/apps/color_ai/image_service_client.py

import requests
import logging
from typing import List, Dict, Optional
from pathlib import Path
from .color_processor import UltimateColorProcessor

logger = logging.getLogger(__name__)


class ImageServiceClient:
    """
    Client for fetching images from the image service and analyzing them.
    """
    
    def __init__(
        self,
        api_base_url: str = "http://localhost:8000/api",
        cache_folder: str = "/home/a/shotdeck-main/deck_search/cache"
    ):
        self.api_base_url = api_base_url
        self.processor = UltimateColorProcessor(cache_folder=cache_folder)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DeckSearch-ColorAI/2.0',
            'Accept': 'application/json'
        })

    def fetch_images(
        self,
        limit: int = 20,
        offset: int = 0,
        **filters
    ) -> List[Dict]:
        """
        Fetch images from the image service.
        
        Args:
            limit: Number of images to fetch
            offset: Pagination offset
            **filters: Additional filters (movie, director, etc.)
            
        Returns:
            List of image data
        """
        try:
            url = f"{self.api_base_url}/images/"
            params = {'limit': limit, 'offset': offset, **filters}
            
            logger.info(f"Fetching images: {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                images = data.get('results', [])
                logger.info(f"Fetched {len(images)} images")
                return images
            else:
                logger.error(f"API error: {data}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Error fetching images: {e}")
            return []

    def analyze_image_from_service(self, image_data: Dict) -> Dict:
        """
        Download and analyze an image from the service.
        
        Args:
            image_data: Image data from API
            
        Returns:
            Complete analysis with original data
        """
        image_url = image_data.get('image_url')
        image_id = str(image_data.get('uuid') or image_data.get('slug', 'unknown'))
        
        if not image_url:
            return {**image_data, 'analysis_error': 'No image URL'}
        
        # Analyze from URL
        analysis = self.processor.analyze_from_url(image_url, image_id)
        
        return {
            **image_data,
            'color_analysis': analysis
        }

    def batch_analyze(
        self,
        limit: int = 20,
        offset: int = 0,
        parallel: bool = False,
        **filters
    ) -> List[Dict]:
        """
        Fetch and analyze multiple images.
        
        Args:
            limit: Number of images
            offset: Pagination offset
            parallel: Use parallel processing (future feature)
            **filters: Additional filters
            
        Returns:
            List of analyzed images
        """
        images = self.fetch_images(limit, offset, **filters)
        
        if not images:
            return []
        
        results = []
        for i, img in enumerate(images, 1):
            logger.info(f"Analyzing {i}/{len(images)}: {img.get('title', 'Unknown')}")
            analyzed = self.analyze_image_from_service(img)
            results.append(analyzed)
        
        return results

    def sync_and_update(self, image_uuid: str) -> Dict:
        """
        Fetch a single image and analyze it, then optionally update the service.
        
        Args:
            image_uuid: UUID of the image
            
        Returns:
            Analysis result
        """
        try:
            url = f"{self.api_base_url}/images/{image_uuid}/"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                image_data = data.get('data')
                return self.analyze_image_from_service(image_data)
            else:
                return {'error': 'Failed to fetch image'}
                
        except Exception as e:
            logger.error(f"Error syncing image {image_uuid}: {e}")
            return {'error': str(e)}


# Convenience functions

def analyze_from_image_service(
    limit: int = 20,
    api_url: str = "http://localhost:8000/api",
    **filters
) -> List[Dict]:
    """
    Quick function to fetch and analyze images from the service.
    
    Args:
        limit: Number of images to analyze
        api_url: API base URL
        **filters: Additional filters
        
    Returns:
        List of analyzed images
    """
    client = ImageServiceClient(api_base_url=api_url)
    return client.batch_analyze(limit=limit, **filters)


def analyze_single_from_service(
    image_uuid: str,
    api_url: str = "http://localhost:8000/api"
) -> Dict:
    """
    Analyze a single image from the service.
    
    Args:
        image_uuid: UUID of the image
        api_url: API base URL
        
    Returns:
        Analysis result
    """
    client = ImageServiceClient(api_base_url=api_url)
    return client.sync_and_update(image_uuid)