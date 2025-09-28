from django.core.management.base import BaseCommand, CommandError
from apps.images.models import Image
from elasticsearch import Elasticsearch
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Index all images in Elasticsearch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of images to index in each batch'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset the index before indexing'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Index only images updated since this datetime (YYYY-MM-DD HH:MM:SS)'
        )

    def handle(self, *args, **options):
        try:
            # Connect to Elasticsearch
            es = Elasticsearch(['http://elasticsearch:9200'])
            if not es.ping():
                raise CommandError('Cannot connect to Elasticsearch')

            self.stdout.write('Connected to Elasticsearch')

            # Reset index if requested
            if options['reset']:
                self.stdout.write('Resetting index...')
                try:
                    es.indices.delete(index='images', ignore=[400, 404])
                    self.stdout.write('Index deleted')
                except Exception as e:
                    self.stdout.write(f'Warning: Could not delete index: {e}')

            # Create index if it doesn't exist
            if not es.indices.exists(index='images'):
                mapping = {
                    'mappings': {
                        'properties': {
                            'id': {'type': 'integer'},
                            'slug': {'type': 'keyword'},
                            'title': {'type': 'text', 'analyzer': 'standard'},
                            'description': {'type': 'text', 'analyzer': 'standard'},
                            'image_url': {'type': 'keyword'},
                            'release_year': {'type': 'integer'},
                            'media_type': {'type': 'keyword'},
                            'genre': {'type': 'keyword'},
                            'color': {'type': 'keyword'},
                            'aspect_ratio': {'type': 'keyword'},
                            'optical_format': {'type': 'keyword'},
                            'format': {'type': 'keyword'},
                            'interior_exterior': {'type': 'keyword'},
                            'time_of_day': {'type': 'keyword'},
                            'number_of_people': {'type': 'keyword'},
                            'gender': {'type': 'keyword'},
                            'age': {'type': 'keyword'},
                            'ethnicity': {'type': 'keyword'},
                            'frame_size': {'type': 'keyword'},
                            'shot_type': {'type': 'keyword'},
                            'composition': {'type': 'keyword'},
                            'lens_size': {'type': 'keyword'},
                            'lens_type': {'type': 'keyword'},
                            'lighting': {'type': 'keyword'},
                            'lighting_type': {'type': 'keyword'},
                            'camera_type': {'type': 'keyword'},
                            'resolution': {'type': 'keyword'},
                            'frame_rate': {'type': 'keyword'},
                            'exclude_nudity': {'type': 'boolean'},
                            'exclude_violence': {'type': 'boolean'},
                            'created_at': {'type': 'date'},
                            'updated_at': {'type': 'date'},
                            'movie': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'slug': {'type': 'keyword'},
                                    'title': {'type': 'text'},
                                    'year': {'type': 'integer'}
                                }
                            },
                            'tags': {
                                'type': 'nested',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'slug': {'type': 'keyword'},
                                    'name': {'type': 'text'}
                                }
                            }
                        }
                    }
                }

                es.indices.create(index='images', body=mapping)
                self.stdout.write('Index created with mapping')

            # Get images to index
            queryset = Image.objects.all()
            if options['since']:
                from django.utils.dateparse import parse_datetime
                since_date = parse_datetime(options['since'])
                if since_date:
                    queryset = queryset.filter(updated_at__gte=since_date)
                    self.stdout.write(f'Indexing images updated since {since_date}')

            total_images = queryset.count()
            self.stdout.write(f'Total images to index: {total_images}')

            # Index images in batches
            batch_size = options['batch_size']
            indexed = 0
            start_time = time.time()

            for i in range(0, total_images, batch_size):
                batch = queryset[i:i + batch_size]
                self.stdout.write(f'Indexing batch {i//batch_size + 1}/{(total_images + batch_size - 1)//batch_size}')

                for image in batch:
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
                        es.index(
                            index='images',
                            id=image.id,
                            body=image_data
                        )

                        indexed += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'Failed to index image {image.slug}: {e}')
                        )

                # Refresh after each batch
                es.indices.refresh(index='images')

            end_time = time.time()
            duration = end_time - start_time

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully indexed {indexed}/{total_images} images in {duration:.2f} seconds'
                )
            )

        except Exception as e:
            raise CommandError(f'Indexing failed: {e}')
