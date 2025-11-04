#!/usr/bin/env python3
"""
Fixed Shotdeck Import Command with Limit Support
"""

import os
import json
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from apps.images.models import (
    Image, Movie, Tag, DirectorOption, CinematographerOption,
    MediaTypeOption, ColorOption, GenreOption
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import Shotdeck dataset with limit support"

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-dir',
            type=str,
            default='/host_data/shot_json_data',
            help='Path to JSON files directory'
        )
        parser.add_argument(
            '--image-dir',
            type=str,
            default='/host_data/shot_images',
            help='Path to images directory'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of images to import'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for progress updates'
        )

    def handle(self, *args, **options):
        json_dir = options['json_dir']
        image_dir = options['image_dir']
        limit = options['limit']
        batch_size = options['batch_size']
        
        if not os.path.exists(json_dir):
            raise CommandError(f"JSON directory not found: {json_dir}")
        
        json_files = sorted([f for f in os.listdir(json_dir) if f.endswith('.json')])
        total_files = len(json_files)
        
        self.stdout.write(f"Found {total_files} JSON files")
        
        if limit:
            json_files = json_files[:limit]
            self.stdout.write(f"Limiting import to {limit} files")
        
        processed = 0
        errors = 0
        skipped = 0
        
        for json_file in json_files:
            try:
                json_path = os.path.join(json_dir, json_file)
                
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Process with transaction
                with transaction.atomic():
                    result = self._process_image_data(data, image_dir, json_file)
                    
                    if result == 'processed':
                        processed += 1
                    elif result == 'skipped':
                        skipped += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"✓ Processed {processed} files... (errors: {errors}, skipped: {skipped})")
                    
            except Exception as e:
                self.stderr.write(f"✗ Error processing {json_file}: {str(e)}")
                errors += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Import Complete!\n"
            f"   Processed: {processed}\n"
            f"   Errors: {errors}\n"
            f"   Skipped: {skipped}\n"
            f"   Total: {processed + errors + skipped}"
        ))

    def _process_image_data(self, data, image_dir, json_filename):
        """Process individual JSON file and create Image record"""
        try:
            # Extract image ID from filename
            image_id = os.path.splitext(json_filename)[0]
            
            # Parse JSON structure (adjust based on actual structure)
            # Check if data has nested 'data' key or is flat
            if 'data' in data and 'details' in data['data']:
                details = data['data']['details']
                
                # Extract title
                title = self._extract_value(details, 'title')
                
                # Extract movie info
                movie_title = self._extract_value(details, 'title')
                movie_year = self._extract_value(details, 'year')
                
                # Extract metadata
                media_type_val = self._extract_value(details, 'media_type')
                director_val = self._extract_value(details, 'director')
                cinematographer_val = self._extract_value(details, 'cinematographer')
                color_val = self._extract_value(details, 'color')
                
            else:
                # Fallback to flat structure
                title = data.get('title', '')
                movie_title = data.get('movie_title', data.get('title', ''))
                movie_year = data.get('year')
                media_type_val = data.get('media_type')
                director_val = data.get('director')
                cinematographer_val = data.get('cinematographer')
                color_val = data.get('color')
            
            # Create image URL
            image_filename = f"{image_id}.jpg"
            image_url = f"/media/images/{image_filename}"
            
            # Get or create movie
            movie = None
            if movie_title:
                movie, _ = Movie.objects.get_or_create(
                    title=movie_title,
                    defaults={'year': movie_year}
                )
            
            # Create or update image
            image, created = Image.objects.update_or_create(
                slug=image_id.lower(),
                defaults={
                    'title': title or movie_title or image_id,
                    'image_url': image_url,
                    'movie': movie,
                    'release_year': movie_year,
                }
            )
            
            # Add metadata
            if media_type_val:
                media_type, _ = MediaTypeOption.objects.get_or_create(value=media_type_val)
                image.media_type = media_type
            
            if director_val:
                director, _ = DirectorOption.objects.get_or_create(value=director_val)
                image.director = director
            
            if cinematographer_val:
                cinematographer, _ = CinematographerOption.objects.get_or_create(value=cinematographer_val)
                image.cinematographer = cinematographer
            
            if color_val:
                color, _ = ColorOption.objects.get_or_create(value=color_val)
                image.color = color
            
            image.save()
            
            return 'processed'
            
        except Exception as e:
            raise Exception(f"Failed to process {json_filename}: {str(e)}")

    def _extract_value(self, details, field_name):
        """Extract value from nested JSON structure"""
        try:
            if field_name in details:
                field_data = details[field_name]
                if isinstance(field_data, dict) and 'values' in field_data:
                    values = field_data['values']
                    if values and len(values) > 0:
                        return values[0].get('display_value', '')
            return None
        except:
            return None
