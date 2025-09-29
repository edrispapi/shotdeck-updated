from django.core.management.base import BaseCommand
from django.db import transaction
from apps.images.models import Image, ColorOption, MediaTypeOption, GenreOption
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate missing data for images to reduce null values in API responses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of images to process in each batch'
        )
        parser.add_argument(
            '--color-analysis',
            action='store_true',
            help='Perform color analysis on images that lack it'
        )
        parser.add_argument(
            '--default-values',
            action='store_true',
            help='Set default values for common missing fields'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        do_color_analysis = options['color_analysis']
        do_default_values = options['default_values']

        if not do_color_analysis and not do_default_values:
            # If neither specific option is chosen, do both
            do_color_analysis = True
            do_default_values = True

        self.stdout.write('=== POPULATE MISSING DATA ===')
        self.stdout.write(f'Dry run: {dry_run}')
        self.stdout.write(f'Batch size: {batch_size}')
        self.stdout.write(f'Color analysis: {do_color_analysis}')
        self.stdout.write(f'Default values: {do_default_values}')

        # Get images that need processing
        images_needing_work = Image.objects.all()

        if do_color_analysis:
            images_needing_color = images_needing_work.filter(
                dominant_colors__isnull=True
            )
            self.stdout.write(f'Images needing color analysis: {images_needing_color.count()}')

        if do_default_values:
            # Count images with missing common fields
            missing_media_type = images_needing_work.filter(media_type__isnull=True).count()
            missing_color = images_needing_work.filter(color__isnull=True).count()
            missing_description = images_needing_work.filter(description__isnull=True).count()

            self.stdout.write(f'Images with missing media_type: {missing_media_type}')
            self.stdout.write(f'Images with missing color: {missing_color}')
            self.stdout.write(f'Images with missing description: {missing_description}')

        if dry_run:
            self.stdout.write('DRY RUN - No changes will be made')
            return

        updated_count = 0

        if do_default_values:
            updated_count += self._populate_default_values(images_needing_work, batch_size)

        if do_color_analysis:
            updated_count += self._populate_color_analysis(images_needing_work, batch_size)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} images')
        )

    def _populate_default_values(self, queryset, batch_size):
        """Populate default values for common missing fields"""
        self.stdout.write('Populating default values...')

        updated = 0

        # Set default media type if missing
        try:
            default_media_type = MediaTypeOption.objects.get(value='Movie')
            media_type_updated = queryset.filter(media_type__isnull=True).update(media_type=default_media_type)
            updated += media_type_updated
            self.stdout.write(f'Set default media_type for {media_type_updated} images')
        except MediaTypeOption.DoesNotExist:
            self.stdout.write('Warning: Default MediaTypeOption "Movie" not found')

        # Set default color if missing
        try:
            default_color = ColorOption.objects.get(value='Color')
            color_updated = queryset.filter(color__isnull=True).update(color=default_color)
            updated += color_updated
            self.stdout.write(f'Set default color for {color_updated} images')
        except ColorOption.DoesNotExist:
            self.stdout.write('Warning: Default ColorOption "Color" not found')

        # Set empty description for null descriptions
        desc_updated = queryset.filter(description__isnull=True).update(description='')
        updated += desc_updated
        self.stdout.write(f'Set empty description for {desc_updated} images')

        return updated

    def _populate_color_analysis(self, queryset, batch_size):
        """Perform color analysis on images that lack it"""
        self.stdout.write('Performing color analysis...')

        images_needing_color = queryset.filter(dominant_colors__isnull=True)
        updated = 0

        for image in images_needing_color.iterator(chunk_size=batch_size):
            try:
                # Perform color analysis
                if image.analyze_colors():
                    image.save()
                    updated += 1

                    if updated % 50 == 0:
                        self.stdout.write(f'Processed {updated} images for color analysis...')

            except Exception as e:
                logger.warning(f'Failed to analyze colors for image {image.id}: {e}')
                continue

        self.stdout.write(f'Completed color analysis for {updated} images')
        return updated

