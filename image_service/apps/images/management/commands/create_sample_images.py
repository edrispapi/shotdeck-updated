from django.core.management.base import BaseCommand
from apps.images.models import Image, Movie, Tag
import random

class Command(BaseCommand):
    help = 'Create sample images for testing'

    def handle(self, *args, **options):
        # Create sample movie if it doesn't exist
        movie, created = Movie.objects.get_or_create(
            title="Sample Movie",
            defaults={
                'year': 2024,
                'genre': 'Action, Drama',
                'description': 'A sample movie for testing image URLs'
            }
        )

        # Create sample tags
        tags = []
        for tag_name in ['action', 'drama', 'cinematic']:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            tags.append(tag)

        # Create sample images
        sample_images = [
            {
                'title': 'Action Scene 1',
                'description': 'High energy action sequence',
                'image_url': '/media/images/sample_1.jpg'
            },
            {
                'title': 'Dramatic Moment',
                'description': 'Emotional character scene',
                'image_url': '/media/images/sample_2.jpg'
            },
            {
                'title': 'Cinematic Shot',
                'description': 'Beautiful cinematography',
                'image_url': '/media/images/sample_3.jpg'
            }
        ]

        for img_data in sample_images:
            image, created = Image.objects.get_or_create(
                title=img_data['title'],
                defaults={
                    'description': img_data['description'],
                    'image_url': img_data['image_url'],
                    'movie': movie,
                    'release_year': 2024,
                    'media_type': None,
                    'exclude_nudity': False,
                    'exclude_violence': False
                }
            )

            if created:
                # Add tags
                image.tags.set(tags[:2])  # Add first 2 tags
                image.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created image: {image.title} - URL: {image.image_url}')
                )
            else:
                self.stdout.write(f'Image already exists: {image.title}')

        self.stdout.write(
            self.style.SUCCESS(f'Sample images created. Total images: {Image.objects.count()}')
        )
