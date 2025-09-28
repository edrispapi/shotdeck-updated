from django.core.management.base import BaseCommand
from apps.images.models import Image
from messaging.producers import send_event

class Command(BaseCommand):
    help = 'Send all images to Kafka for indexing in search_service'

    def handle(self, *args, **options):
        images = Image.objects.all()
        for image in images:
            data = {
                "id": image.id,
                "slug": image.slug,
                "title": image.title,
                "description": image.description,
                "image_url": image.image_url,
                "release_year": image.release_year,
                "movie": {
                    "slug": image.movie.slug,
                    "title": image.movie.title,
                    "year": image.movie.year
                } if image.movie else None,
                "tags": [{"slug": tag.slug, "name": tag.name} for tag in image.tags.all()],
                "media_type": image.media_type,
                "genre": image.genre,
                "color": image.color,
                "aspect_ratio": image.aspect_ratio,
                "optical_format": image.optical_format,
                "format": image.format,
                "interior_exterior": image.interior_exterior,
                "time_of_day": image.time_of_day,
                "number_of_people": image.number_of_people,
                "gender": image.gender,
                "age": image.age,
                "ethnicity": image.ethnicity,
                "frame_size": image.frame_size,
                "shot_type": image.shot_type,
                "composition": image.composition,
                "lens_size": image.lens_size,
                "lens_type": image.lens_type,
                "lighting": image.lighting,
                "lighting_type": image.lighting_type,
                "camera_type": image.camera_type,
                "resolution": image.resolution,
                "frame_rate": image.frame_rate,
                "exclude_nudity": image.exclude_nudity,
                "exclude_violence": image.exclude_violence,
                "created_at": image.created_at.isoformat(),
                "updated_at": image.updated_at.isoformat()
            }
            send_event('image_created', data)
            self.stdout.write(self.style.SUCCESS(f"Sent image {image.slug} to Kafka"))