from django.core.management.base import BaseCommand
from django.conf import settings
from apps.images.models import Image
import os


class Command(BaseCommand):
    help = "Import images from MEDIA_ROOT/images into Image records."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only show what would be imported')
        parser.add_argument('--limit', type=int, default=None, help='Limit number of files processed')
        parser.add_argument('--force', action='store_true', help='Delete and recreate existing Image records for matching files')

    def handle(self, *args, **options):
        media_root = str(getattr(settings, 'MEDIA_ROOT', '/service/media'))
        images_dir = os.path.join(media_root, 'images')

        if not os.path.isdir(images_dir):
            self.stderr.write(self.style.ERROR(f"Images directory not found: {images_dir}"))
            return

        filenames = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
        if options['limit'] is not None:
            filenames = filenames[: options['limit']]

        created_count = 0
        skipped_count = 0

        for name in filenames:
            rel_url = f"/media/images/{name}"
            existing_qs = Image.objects.filter(image_url=rel_url)
            if existing_qs.exists():
                if options['force']:
                    if options['dry_run']:
                        self.stdout.write(f"WOULD DELETE and RECREATE: {rel_url}")
                        continue
                    existing_qs.delete()
                else:
                    skipped_count += 1
                    continue

            if options['dry_run']:
                self.stdout.write(f"WOULD CREATE: {rel_url}")
                continue

            # Create minimal Image record; title is filename without extension
            title = os.path.splitext(name)[0]
            img = Image(title=title, image_url=rel_url)
            img.save()
            created_count += 1

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(f"Dry run complete. Would create {len(filenames) - skipped_count} new, skip {skipped_count}."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Import complete. Created {created_count}, skipped {skipped_count}."))


