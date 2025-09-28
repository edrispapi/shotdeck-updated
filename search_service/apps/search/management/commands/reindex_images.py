from django.core.management.base import BaseCommand
from django.conf import settings
from elasticsearch_dsl import connections
from apps.search.documents import ImageDocument
from apps.images.models import Image
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Re-index all images in Elasticsearch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Batch size for indexing'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of images to index'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        limit = options['limit']

        # Setup Elasticsearch connection
        connections.create_connection(
            hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']],
            alias='default'
        )

        # Create index if it doesn't exist
        ImageDocument.init()

        # Get images to index
        images = Image.objects.all()
        if limit:
            images = images[:limit]

        total_images = images.count()
        self.stdout.write(f'Starting re-indexing of {total_images} images...')

        indexed_count = 0
        for i in range(0, total_images, batch_size):
            batch = images[i:i + batch_size]

            for image in batch:
                try:
                    # Create document data
                    doc_data = {
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
                        'created_at': image.created_at,
                        'updated_at': image.updated_at,
                        # Color fields
                        'dominant_colors': image.dominant_colors or [],
                        'primary_color_hex': image.primary_color_hex,
                        'secondary_color_hex': image.secondary_color_hex,
                        'color_palette': image.color_palette,
                        'color_samples': image.color_samples or [],
                        'color_histogram': image.color_histogram,
                        'primary_colors': image.primary_colors or [],
                        'color_search_terms': image.color_search_terms or [],
                        # Relations
                        'movie': {
                            'id': image.movie.id if image.movie else None,
                            'slug': image.movie.slug if image.movie else None,
                            'title': image.movie.title if image.movie else None,
                            'year': image.movie.year if image.movie else None,
                        } if image.movie else {},
                        'tags': [
                            {
                                'id': tag.id,
                                'slug': tag.slug,
                                'name': tag.name
                            } for tag in image.tags.all()
                        ]
                    }

                    # Index the document
                    doc = ImageDocument(meta={'id': image.id}, **doc_data)
                    doc.save()

                    indexed_count += 1

                    if indexed_count % 10 == 0:
                        self.stdout.write(f'Indexed {indexed_count}/{total_images} images...')

                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Failed to index image {image.id}: {e}')
                    )

            self.stdout.write(f'Completed batch {i//batch_size + 1}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully re-indexed {indexed_count} images!')
        )
