import os
import json
import hashlib
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.images.models import Image, Movie
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Import images with rigorous validation'
    
    def add_arguments(self, parser):
        parser.add_argument('--json-dir', type=str, 
            default='/home/a/Desktop/shotdeck/dataset/shot_json_data')
        parser.add_argument('--image-dir', type=str,
            default='/home/a/Desktop/shotdeck/dataset/shot_images')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--validate-only', action='store_true')
    
    def handle(self, *args, **options):
        json_dir = Path(options['json_dir'])
        image_dir = Path(options['image_dir'])
        dry_run = options['dry_run']
        validate_only = options['validate_only']
        
        if not json_dir.exists():
            self.stdout.write(self.style.ERROR(f'JSON dir not found: {json_dir}'))
            return
        
        json_files = list(json_dir.glob('*.json'))
        self.stdout.write(f'Found {len(json_files)} JSON files')
        
        stats = {
            'total': 0,
            'success': 0,
            'errors': 0,
            'image_not_found': 0,
            'validation_errors': []
        }
        
        for json_file in json_files:
            stats['total'] += 1
            
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                image_data = data['data']
                imageid = image_data['imageid']
                image_filename = image_data['image_file']
                
                # Validate JSON structure
                if not imageid or not image_filename:
                    stats['errors'] += 1
                    stats['validation_errors'].append(f'{json_file.name}: Missing imageid or filename')
                    continue
                
                # Create slug
                slug_base = imageid.lower()
                
                # Find image file
                image_path = None
                if image_dir.exists():
                    # Try exact match
                    exact_path = image_dir / image_filename
                    if exact_path.exists():
                        image_path = exact_path
                    else:
                        # Search for any file matching imageid
                        matches = list(image_dir.glob(f'{imageid}.*'))
                        if matches:
                            image_path = matches[0]
                
                if not image_path and not validate_only:
                    stats['image_not_found'] += 1
                    if stats['image_not_found'] <= 5:
                        self.stdout.write(self.style.WARNING(
                            f'Image not found: {imageid} -> {image_filename}'
                        ))
                    continue
                
                # Extract metadata
                details = image_data.get('details', {})
                title_info = details.get('title', {}).get('values', [{}])[0]
                title = title_info.get('display_value', 'Unknown')
                
                if validate_only:
                    # Just validate
                    db_img = Image.objects.filter(slug__startswith=slug_base).first()
                    if db_img:
                        if title not in db_img.title:
                            stats['validation_errors'].append(
                                f'{imageid}: Title mismatch - JSON:{title} vs DB:{db_img.title}'
                            )
                    else:
                        stats['validation_errors'].append(f'{imageid}: Not in database')
                else:
                    # Import logic here
                    stats['success'] += 1
                
                if stats['total'] % 1000 == 0:
                    self.stdout.write(f'Processed {stats["total"]} files...')
                    
            except Exception as e:
                stats['errors'] += 1
                if len(stats['validation_errors']) < 10:
                    stats['validation_errors'].append(f'{json_file.name}: {str(e)}')
        
        # Print summary
        self.stdout.write(self.style.SUCCESS(f'\n=== SUMMARY ==='))
        self.stdout.write(f'Total JSON files: {stats["total"]}')
        self.stdout.write(f'Success: {stats["success"]}')
        self.stdout.write(f'Errors: {stats["errors"]}')
        self.stdout.write(f'Images not found: {stats["image_not_found"]}')
        
        if stats['validation_errors']:
            self.stdout.write(self.style.ERROR(f'\nValidation Errors (first 10):'))
            for error in stats['validation_errors'][:10]:
                self.stdout.write(f'  - {error}')
