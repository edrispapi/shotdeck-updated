from django.core.management.base import BaseCommand
from apps.images.models import Image
from elasticsearch import Elasticsearch
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reindex images from database'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None)
        parser.add_argument('--batch-size', type=int, default=50)

    def handle(self, *args, **options):
        limit = options.get('limit')
        batch_size = options.get('batch_size')

        es = Elasticsearch(hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']])
        
        if not es.ping():
            self.stdout.write(self.style.ERROR('Cannot connect to ES'))
            return

        self.stdout.write(self.style.SUCCESS('Connected to Elasticsearch'))

        images = Image.objects.select_related('movie').prefetch_related('tags', 'genre').all()
        if limit:
            images = images[:limit]

        total = images.count()
        self.stdout.write(f'Found {total} images')

        color_map = {
            1: 'Warm', 2: 'Cool', 3: 'Mixed', 4: 'Saturated', 5: 'Desaturated',
            6: 'Red', 7: 'Orange', 8: 'Yellow', 9: 'Green', 10: 'Cyan',
            11: 'Blue', 12: 'Purple', 13: 'Magenta', 14: 'Pink',
            15: 'White', 16: 'Sepia', 17: 'Black and White', 48: 'Warm'
        }

        def get_val(obj):
            if obj is None:
                return None
            return obj.value if hasattr(obj, 'value') else str(obj)

        indexed = 0
        for i in range(0, total, batch_size):
            for image in images[i:i+batch_size]:
                try:
                    # Get image URL - flexible approach
                    img_url = None
                    if hasattr(image, 'image_url') and image.image_url:
                        img_url = image.image_url
                    elif hasattr(image, 'image') and image.image:
                        img_url = image.image.url
                    else:
                        img_url = f"/media/images/{image.slug}.jpg"

                    color = color_map.get(image.color) if isinstance(image.color, int) else get_val(image.color)
                    
                    doc = {
                        'id': image.id,
                        'slug': image.slug,
                        'title': image.title or '',
                        'image_url': img_url,
                        'color': color,
                        'media_type': get_val(image.media_type),
                        'genre': [get_val(g) for g in image.genre.all()],
                    }
                    
                    es.index(index='images', id=image.id, body=doc)
                    indexed += 1
                except Exception as e:
                    logger.error(f"Error: {e}")
            
            self.stdout.write(f'Indexed {indexed}/{total}')

        self.stdout.write(self.style.SUCCESS(f'Done: {indexed} images'))
