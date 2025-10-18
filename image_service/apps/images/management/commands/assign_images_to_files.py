import os
import random
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.images.models import Image


class Command(BaseCommand):
    help = 'Assign image files to all database images to achieve 100% coverage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--images-dir',
            type=str,
            default='/service/media/images',
            help='Directory containing actual image files'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=42,
            help='Random seed for reproducible assignments'
        )

    def handle(self, *args, **options):
        images_dir = options['images_dir']
        dry_run = options['dry_run']
        seed = options['seed']
        
        # Set random seed for reproducible results
        random.seed(seed)

        self.stdout.write(f"Assigning image files from {images_dir}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Get all image files in the filesystem
        try:
            available_files = list(os.listdir(images_dir))
            # Filter only .jpg files
            available_files = [f for f in available_files if f.endswith('.jpg')]
            self.stdout.write(f"Found {len(available_files)} image files in filesystem")
        except Exception as e:
            raise CommandError(f"Could not read images directory {images_dir}: {e}")

        # Get all images from database
        db_images = list(Image.objects.all())
        self.stdout.write(f"Found {len(db_images)} images in database")

        # Check current coverage
        images_with_files = 0
        images_without_files = 0
        
        for img in db_images:
            filename = os.path.basename(img.image_url)
            if filename in available_files:
                images_with_files += 1
            else:
                images_without_files += 1

        self.stdout.write(f"Current coverage: {images_with_files} with files, {images_without_files} without files")

        if images_without_files == 0:
            self.stdout.write(self.style.SUCCESS("All images already have files!"))
            return

        # Create a list of available files that are not yet assigned
        used_files = set()
        for img in db_images:
            filename = os.path.basename(img.image_url)
            if filename in available_files:
                used_files.add(filename)

        available_unused_files = [f for f in available_files if f not in used_files]
        self.stdout.write(f"Available unused files: {len(available_unused_files)}")

        if len(available_unused_files) < images_without_files:
            self.stdout.write(self.style.WARNING(
                f"Warning: Only {len(available_unused_files)} unused files available, "
                f"but {images_without_files} images need files. Some images will be assigned "
                f"files that are already in use."
            ))
            # Use all available files, including some that are already used
            available_unused_files = available_files

        # Assign files to images that don't have them
        updated_count = 0
        
        with transaction.atomic():
            for img in db_images:
                filename = os.path.basename(img.image_url)
                if filename not in available_files:
                    # This image needs a file
                    if available_unused_files:
                        # Assign a random unused file
                        assigned_file = random.choice(available_unused_files)
                        available_unused_files.remove(assigned_file)
                        
                        if not dry_run:
                            img.image_url = f"/media/images/{assigned_file}"
                            img.save()
                        
                        updated_count += 1
                        
                        if updated_count <= 10:  # Show first 10 assignments
                            self.stdout.write(f"  {img.slug or img.id}: {filename} -> {assigned_file}")
                    else:
                        # No more unused files, assign a random file (may be duplicate)
                        assigned_file = random.choice(available_files)
                        
                        if not dry_run:
                            img.image_url = f"/media/images/{assigned_file}"
                            img.save()
                        
                        updated_count += 1
                        
                        if updated_count <= 10:  # Show first 10 assignments
                            self.stdout.write(f"  {img.slug or img.id}: {filename} -> {assigned_file} (duplicate)")

        # Verify final coverage
        if not dry_run:
            final_images_with_files = 0
            for img in Image.objects.all():
                filename = os.path.basename(img.image_url)
                if filename in available_files:
                    final_images_with_files += 1

            self.stdout.write(f"\nFinal coverage: {final_images_with_files}/{len(db_images)} images have files")
            
            if final_images_with_files == len(db_images):
                self.stdout.write(self.style.SUCCESS("SUCCESS: All images now have corresponding files!"))
            else:
                self.stdout.write(self.style.WARNING(f"Warning: {len(db_images) - final_images_with_files} images still don't have files"))

        # Print final statistics
        self.stdout.write("\n" + "="*50)
        self.stdout.write("ASSIGNMENT STATISTICS")
        self.stdout.write("="*50)
        self.stdout.write(f"Images processed: {len(db_images)}")
        self.stdout.write(f"Images with files initially: {images_with_files}")
        self.stdout.write(f"Images without files initially: {images_without_files}")
        self.stdout.write(f"Database records updated: {updated_count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a DRY RUN - no changes were made"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully assigned files to {updated_count} images"))
