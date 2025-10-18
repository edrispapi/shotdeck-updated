import os
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.images.models import Image


class Command(BaseCommand):
    help = 'Map database images to actual image files in the filesystem'

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
            default='/service/media/images',
            help='Directory containing actual image files'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of images to process (for testing)'
        )

    def handle(self, *args, **options):
        json_dir = options['json_dir']
        images_dir = options['images_dir']
        dry_run = options['dry_run']
        limit = options['limit']

        self.stdout.write(f"Mapping images from {json_dir} to {images_dir}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Get all image files in the filesystem
        try:
            available_files = set(os.listdir(images_dir))
            self.stdout.write(f"Found {len(available_files)} files in filesystem")
        except Exception as e:
            raise CommandError(f"Could not read images directory {images_dir}: {e}")

        # Get all JSON files
        try:
            json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
            json_files.sort()  # Process in deterministic order
            self.stdout.write(f"Found {len(json_files)} JSON files")
        except Exception as e:
            raise CommandError(f"Could not read JSON directory {json_dir}: {e}")

        if limit:
            json_files = json_files[:limit]
            self.stdout.write(f"Limited to {limit} files for testing")

        # Track statistics
        stats = {
            'processed': 0,
            'found_exact_match': 0,
            'found_alternative': 0,
            'not_found': 0,
            'updated': 0,
            'errors': 0
        }

        # Process each JSON file
        for json_file in json_files:
            json_path = os.path.join(json_dir, json_file)
            
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                # Extract image information
                if 'data' in data and isinstance(data['data'], dict):
                    image_data = data['data']
                    image_id = image_data.get('imageid')
                    image_file = image_data.get('image_file')
                    
                    if image_id and image_file:
                        stats['processed'] += 1
                        
                        # Find the corresponding image in database
                        try:
                            db_image = Image.objects.get(image_url=f"/media/images/{image_file}")
                            
                            # Check if file exists exactly as specified
                            if image_file in available_files:
                                stats['found_exact_match'] += 1
                                if not dry_run:
                                    # File exists, no need to update
                                    pass
                            else:
                                # Try to find alternative file
                                alternative_file = self.find_alternative_file(image_id, image_file, available_files)
                                
                                if alternative_file:
                                    stats['found_alternative'] += 1
                                    if not dry_run:
                                        # Update database with correct file
                                        db_image.image_url = f"/media/images/{alternative_file}"
                                        db_image.save()
                                        stats['updated'] += 1
                                    
                                    self.stdout.write(f"  {image_id}: {image_file} -> {alternative_file}")
                                else:
                                    stats['not_found'] += 1
                                    self.stdout.write(self.style.ERROR(f"  {image_id}: {image_file} - NO FILE FOUND"))
                        
                        except Image.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f"  {image_id}: Not found in database"))
                            stats['errors'] += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"  {image_id}: Error - {e}"))
                            stats['errors'] += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {json_file}: {e}"))
                stats['errors'] += 1

        # Print final statistics
        self.stdout.write("\n" + "="*50)
        self.stdout.write("MAPPING STATISTICS")
        self.stdout.write("="*50)
        self.stdout.write(f"Processed JSON files: {stats['processed']}")
        self.stdout.write(f"Exact matches found: {stats['found_exact_match']}")
        self.stdout.write(f"Alternative files found: {stats['found_alternative']}")
        self.stdout.write(f"Files not found: {stats['not_found']}")
        self.stdout.write(f"Database records updated: {stats['updated']}")
        self.stdout.write(f"Errors: {stats['errors']}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a DRY RUN - no changes were made"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {stats['updated']} database records"))

    def find_alternative_file(self, image_id, original_file, available_files):
        """
        Try to find an alternative file for the given image_id.
        This method implements various strategies to find the correct file.
        """
        # Strategy 1: Look for exact match first
        if original_file in available_files:
            return original_file
        
        # Strategy 2: Look for files with the image_id pattern
        if image_id:
            for file in available_files:
                if file.startswith(image_id) and file.endswith('.jpg'):
                    return file
        
        # Strategy 3: Look for files starting with the same characters
        base_name = os.path.splitext(original_file)[0]
        for file in available_files:
            if file.startswith(base_name[:4]):  # First 4 characters
                return file
        
        # Strategy 4: Look for files ending with the same characters
        for file in available_files:
            if file.endswith(base_name[-4:] + '.jpg'):  # Last 4 characters
                return file
        
        # Strategy 5: Look for files with similar length and pattern
        for file in available_files:
            if len(file) == len(original_file) and file.endswith('.jpg'):
                # Check if it's alphanumeric like the original
                file_base = os.path.splitext(file)[0]
                if file_base.isalnum() and len(file_base) == len(base_name):
                    return file
        
        # Strategy 6: Look for files with similar character patterns
        # This is a more sophisticated approach for cases where files might be renamed
        original_chars = set(base_name.lower())
        best_match = None
        best_score = 0
        
        for file in available_files:
            if file.endswith('.jpg'):
                file_base = os.path.splitext(file)[0]
                if len(file_base) == len(base_name):
                    file_chars = set(file_base.lower())
                    # Calculate similarity score
                    common_chars = original_chars.intersection(file_chars)
                    score = len(common_chars) / len(original_chars) if original_chars else 0
                    
                    if score > best_score and score > 0.6:  # At least 60% similarity
                        best_score = score
                        best_match = file
        
        if best_match:
            return best_match
        
        return None
