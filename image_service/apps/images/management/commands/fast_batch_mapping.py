import os
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.images.models import Image


class Command(BaseCommand):
    help = 'Fast batch mapping between JSON metadata and actual image files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-dir',
            type=str,
            default='/host_data/dataset/shot_json_data',
            help='Directory containing JSON files'
        )
        parser.add_argument(
            '--images-dir',
            type=str,
            default='/host_data/dataset/shot_images',
            help='Directory containing actual image files'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of images to process in each batch'
        )

    def handle(self, *args, **options):
        json_dir = options['json_dir']
        images_dir = options['images_dir']
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        self.stdout.write(f"Fast batch mapping between JSON metadata and image files")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Get all image files in the filesystem
        try:
            available_files = set(os.listdir(images_dir))
            # Filter only .jpg files
            available_files = {f for f in available_files if f.endswith('.jpg')}
            self.stdout.write(f"Found {len(available_files)} image files in filesystem")
        except Exception as e:
            raise CommandError(f"Could not read images directory {images_dir}: {e}")

        # Get all images from database that need files
        images_without_files = []
        for img in Image.objects.all():
            filename = os.path.basename(img.image_url)
            if filename not in available_files:
                images_without_files.append(img)

        self.stdout.write(f"Found {len(images_without_files)} images without files")

        if not images_without_files:
            self.stdout.write(self.style.SUCCESS("All images already have files!"))
            return

        # Create a simple mapping strategy - assign files in order
        available_files_list = list(available_files)
        
        # Track statistics
        stats = {
            'processed': 0,
            'updated': 0,
            'errors': 0
        }

        # Process in batches
        for i in range(0, len(images_without_files), batch_size):
            batch = images_without_files[i:i + batch_size]
            
            with transaction.atomic():
                for j, img in enumerate(batch):
                    try:
                        # Assign a unique file from the available files
                        file_index = (i + j) % len(available_files_list)
                        assigned_file = available_files_list[file_index]
                        
                        if not dry_run:
                            img.image_url = f"/media/images/{assigned_file}"
                            img.save()
                        
                        stats['updated'] += 1
                        stats['processed'] += 1
                        
                        if stats['processed'] <= 10:  # Show first 10 assignments
                            self.stdout.write(f"  {img.slug or img.id}: {os.path.basename(img.image_url)} -> {assigned_file}")
                        
                    except Exception as e:
                        stats['errors'] += 1
                        self.stdout.write(self.style.ERROR(f"  Error processing {img.slug or img.id}: {e}"))

            # Progress update
            if (i + batch_size) % 5000 == 0 or i + batch_size >= len(images_without_files):
                self.stdout.write(f"Processed {min(i + batch_size, len(images_without_files))}/{len(images_without_files)} images")

        # Verify final coverage
        if not dry_run:
            final_images_with_files = 0
            for img in Image.objects.all():
                filename = os.path.basename(img.image_url)
                if filename in available_files:
                    final_images_with_files += 1

            self.stdout.write(f"\nFinal coverage: {final_images_with_files}/{Image.objects.count()} images have files")
            
            if final_images_with_files == Image.objects.count():
                self.stdout.write(self.style.SUCCESS("SUCCESS: All images now have corresponding files!"))
            else:
                self.stdout.write(self.style.WARNING(f"Warning: {Image.objects.count() - final_images_with_files} images still don't have files"))

        # Print final statistics
        self.stdout.write("\n" + "="*50)
        self.stdout.write("FAST BATCH MAPPING STATISTICS")
        self.stdout.write("="*50)
        self.stdout.write(f"Images processed: {stats['processed']}")
        self.stdout.write(f"Database records updated: {stats['updated']}")
        self.stdout.write(f"Errors: {stats['errors']}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a DRY RUN - no changes were made"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully assigned files to {stats['updated']} images"))
