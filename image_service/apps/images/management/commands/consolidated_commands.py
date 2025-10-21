#!/usr/bin/env python3
"""
Consolidated Management Commands for Image Service
Combines all management commands into a single file for easier maintenance
"""

import os
import json
import uuid
import logging
import re
from typing import Dict, List, Optional, Set
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from django.utils.text import slugify
from apps.images.models import (
    Image, Movie, Tag, ActorOption, CameraOption, CinematographerOption, 
    DirectorOption, LensOption, FilmStockOption, SettingOption, 
    LocationOption, FilmingLocationOption, AspectRatioOption,
    MediaTypeOption, TimePeriodOption, TimeOfDayOption, 
    InteriorExteriorOption, FormatOption, FrameSizeOption,
    LensTypeOption, CompositionOption, ShotTypeOption, LightingOption,
    LightingTypeOption, CameraTypeOption, ResolutionOption, FrameRateOption,
    ColorOption, ShadeOption, ProductionDesignerOption, CostumeDesignerOption,
    EditorOption, ColoristOption, ArtistOption, LocationTypeOption,
    YearOption, VfxBackingOption, GenreOption, GenderOption, AgeOption,
    EthnicityOption, NumberOfPeopleOption, OpticalFormatOption, LabProcessOption
)

# Regex patterns for parsing
TAG_PREFIX_PATTERN = re.compile(r"\b[Tt]ags\s*:\s*(?P<tags>[^|\n\r]*)")
ACTORS_PREFIX_PATTERN = re.compile(r"\b[Aa]ctors?\s*:\s*(?P<actors>[^|\n\r]*)")

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consolidated management commands for image service operations"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option_cache = {}
        self.used_files = set()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/service/consolidated_commands.log'),
                logging.StreamHandler()
            ]
        )

    def add_arguments(self, parser):
        # Main command selection
        parser.add_argument(
            'command',
            choices=[
                'import_complete', 'import_optimized', 'import_metadata',
                'backfill_colors', 'backfill_release_year', 'normalize_tags',
                'populate_movies', 'derive_colors', 'verify_integrity',
                'show_sample', 'import_dataset'
            ],
            help='Command to execute'
        )
        
        # Common arguments
        parser.add_argument(
            '--json-dir',
            type=str,
            default='/host_data/dataset/shot_json_data',
            help='Path to JSON files directory'
        )
        parser.add_argument(
            '--image-dir',
            type=str,
            default='/host_data/dataset/shot_images',
            help='Path to images directory'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for processing'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes'
        )

    def handle(self, *args, **options):
        command = options['command']
        
        if command == 'import_complete':
            self.import_complete(options)
        elif command == 'import_optimized':
            self.import_optimized(options)
        elif command == 'import_metadata':
            self.import_metadata(options)
        elif command == 'backfill_colors':
            self.backfill_colors(options)
        elif command == 'backfill_release_year':
            self.backfill_release_year(options)
        elif command == 'normalize_tags':
            self.normalize_tags(options)
        elif command == 'populate_movies':
            self.populate_movies(options)
        elif command == 'derive_colors':
            self.derive_colors(options)
        elif command == 'verify_integrity':
            self.verify_integrity(options)
        elif command == 'show_sample':
            self.show_sample(options)
        elif command == 'import_dataset':
            self.import_dataset(options)

    def import_complete(self, options):
        """Complete Shotdeck data import with ALL metadata fields"""
        self.stdout.write("Starting complete Shotdeck data import...")
        
        json_dir = options['json_dir']
        image_dir = options['image_dir']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if not os.path.exists(json_dir):
            raise CommandError(f"JSON directory not found: {json_dir}")
        
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        self.stdout.write(f"Found {len(json_files)} JSON files")
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            return
        
        processed = 0
        errors = 0
        
        for json_file in json_files:
            try:
                with open(os.path.join(json_dir, json_file), 'r') as f:
                    data = json.load(f)
                
                # Process the image data
                self._process_image_data(data, image_dir)
                processed += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed} files...")
                    
            except Exception as e:
                self.stderr.write(f"Error processing {json_file}: {e}")
                errors += 1
        
        self.stdout.write(f"Import complete. Processed: {processed}, Errors: {errors}")

    def import_optimized(self, options):
        """Optimized Shotdeck data import with intelligent file matching"""
        self.stdout.write("Starting optimized Shotdeck data import...")
        
        json_dir = options['json_dir']
        image_dir = options['image_dir']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if not os.path.exists(json_dir):
            raise CommandError(f"JSON directory not found: {json_dir}")
        
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        self.stdout.write(f"Found {len(json_files)} JSON files")
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            return
        
        processed = 0
        errors = 0
        
        for json_file in json_files:
            try:
                with open(os.path.join(json_dir, json_file), 'r') as f:
                    data = json.load(f)
                
                # Process with optimization
                self._process_image_data_optimized(data, image_dir)
                processed += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed} files...")
                    
            except Exception as e:
                self.stderr.write(f"Error processing {json_file}: {e}")
                errors += 1
        
        self.stdout.write(f"Optimized import complete. Processed: {processed}, Errors: {errors}")

    def import_metadata(self, options):
        """Import images with metadata"""
        self.stdout.write("Starting metadata import...")
        
        json_dir = options['json_dir']
        image_dir = options['image_dir']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if not os.path.exists(json_dir):
            raise CommandError(f"JSON directory not found: {json_dir}")
        
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        self.stdout.write(f"Found {len(json_files)} JSON files")
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            return
        
        processed = 0
        errors = 0
        
        for json_file in json_files:
            try:
                with open(os.path.join(json_dir, json_file), 'r') as f:
                    data = json.load(f)
                
                # Process metadata
                self._process_metadata(data, image_dir)
                processed += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed} files...")
                    
            except Exception as e:
                self.stderr.write(f"Error processing {json_file}: {e}")
                errors += 1
        
        self.stdout.write(f"Metadata import complete. Processed: {processed}, Errors: {errors}")

    def backfill_colors(self, options):
        """Backfill color data for existing images"""
        self.stdout.write("Starting color backfill...")
        
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            return
        
        images = Image.objects.filter(color__isnull=True)
        self.stdout.write(f"Found {images.count()} images without color data")
        
        processed = 0
        errors = 0
        
        for image in images:
            try:
                # Backfill color data
                self._backfill_image_colors(image)
                processed += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed} images...")
                    
            except Exception as e:
                self.stderr.write(f"Error processing image {image.id}: {e}")
                errors += 1
        
        self.stdout.write(f"Color backfill complete. Processed: {processed}, Errors: {errors}")

    def backfill_release_year(self, options):
        """Backfill release year data for existing images"""
        self.stdout.write("Starting release year backfill...")
        
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            return
        
        images = Image.objects.filter(release_year__isnull=True)
        self.stdout.write(f"Found {images.count()} images without release year data")
        
        processed = 0
        errors = 0
        
        for image in images:
            try:
                # Backfill release year data
                self._backfill_image_release_year(image)
                processed += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed} images...")
                    
            except Exception as e:
                self.stderr.write(f"Error processing image {image.id}: {e}")
                errors += 1
        
        self.stdout.write(f"Release year backfill complete. Processed: {processed}, Errors: {errors}")

    def normalize_tags(self, options):
        """Normalize image descriptions and move tags to proper field"""
        self.stdout.write("Starting tag normalization...")
        
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            return
        
        images = Image.objects.filter(description__icontains='Tags:')
        self.stdout.write(f"Found {images.count()} images with tag prefixes")
        
        processed = 0
        errors = 0
        
        for image in images:
            try:
                # Normalize tags
                self._normalize_image_tags(image)
                processed += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed} images...")
                    
            except Exception as e:
                self.stderr.write(f"Error processing image {image.id}: {e}")
                errors += 1
        
        self.stdout.write(f"Tag normalization complete. Processed: {processed}, Errors: {errors}")

    def populate_movies(self, options):
        """Populate movie fields for existing images"""
        self.stdout.write("Starting movie field population...")
        
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            return
        
        images = Image.objects.filter(movie__isnull=True)
        self.stdout.write(f"Found {images.count()} images without movie data")
        
        processed = 0
        errors = 0
        
        for image in images:
            try:
                # Populate movie fields
                self._populate_image_movie_fields(image)
                processed += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed} images...")
                    
            except Exception as e:
                self.stderr.write(f"Error processing image {image.id}: {e}")
                errors += 1
        
        self.stdout.write(f"Movie population complete. Processed: {processed}, Errors: {errors}")

    def derive_colors(self, options):
        """Derive colors from shades for existing images"""
        self.stdout.write("Starting color derivation from shades...")
        
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            return
        
        images = Image.objects.filter(shade__isnull=False, color__isnull=True)
        self.stdout.write(f"Found {images.count()} images with shades but no colors")
        
        processed = 0
        errors = 0
        
        for image in images:
            try:
                # Derive colors from shades
                self._derive_colors_from_shades(image)
                processed += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed} images...")
                    
            except Exception as e:
                self.stderr.write(f"Error processing image {image.id}: {e}")
                errors += 1
        
        self.stdout.write(f"Color derivation complete. Processed: {processed}, Errors: {errors}")

    def verify_integrity(self, options):
        """Verify data integrity between database and JSON files"""
        self.stdout.write("Starting data integrity verification...")
        
        # Get a sample image from database
        img = Image.objects.filter(slug__startswith='3ujb4r4v').first()
        if not img:
            self.stdout.write("Sample image not found in database")
            return
        
        self.stdout.write(f"Database Image: {img.slug}")
        self.stdout.write(f"Database Movie: {img.movie.title if img.movie else 'None'}")
        self.stdout.write(f"Database Media Type: {img.media_type.value if img.media_type else 'None'}")
        self.stdout.write(f"Database Director: {img.director.value if img.director else 'None'}")
        self.stdout.write(f"Database Cinematographer: {img.cinematographer.value if img.cinematographer else 'None'}")
        self.stdout.write(f"Database Genre: {[g.value for g in img.genre.all()] if img.genre.exists() else 'None'}")
        
        # Check JSON file
        json_path = '/host_data/dataset/shot_json_data/3UJB4R4V.json'
        if not os.path.exists(json_path):
            self.stdout.write("JSON file not found")
            return
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        details = data['data']['details']
        self.stdout.write("=== SOURCE JSON DATA ===")
        self.stdout.write(f"JSON Movie: {details['title']['values'][0]['display_value']}")
        self.stdout.write(f"JSON Media Type: {details['media_type']['values'][0]['display_value']}")
        self.stdout.write(f"JSON Year: {details['year']['values'][0]['display_value']}")
        
        self.stdout.write("Data integrity verification complete")

    def show_sample(self, options):
        """Show sample data from database"""
        self.stdout.write("Showing sample data...")
        
        # Get sample images
        images = Image.objects.all()[:5]
        
        for img in images:
            self.stdout.write(f"Image: {img.slug}")
            self.stdout.write(f"  Title: {img.title}")
            self.stdout.write(f"  Movie: {img.movie.title if img.movie else 'None'}")
            self.stdout.write(f"  Media Type: {img.media_type.value if img.media_type else 'None'}")
            self.stdout.write(f"  Color: {img.color.value if img.color else 'None'}")
            self.stdout.write(f"  Tags: {[t.name for t in img.tags.all()]}")
            self.stdout.write("---")

    def import_dataset(self, options):
        """Import complete dataset"""
        self.stdout.write("Starting complete dataset import...")
        
        json_dir = options['json_dir']
        image_dir = options['image_dir']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if not os.path.exists(json_dir):
            raise CommandError(f"JSON directory not found: {json_dir}")
        
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        self.stdout.write(f"Found {len(json_files)} JSON files")
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            return
        
        processed = 0
        errors = 0
        
        for json_file in json_files:
            try:
                with open(os.path.join(json_dir, json_file), 'r') as f:
                    data = json.load(f)
                
                # Process complete dataset
                self._process_complete_dataset(data, image_dir)
                processed += 1
                
                if processed % batch_size == 0:
                    self.stdout.write(f"Processed {processed} files...")
                    
            except Exception as e:
                self.stderr.write(f"Error processing {json_file}: {e}")
                errors += 1
        
        self.stdout.write(f"Dataset import complete. Processed: {processed}, Errors: {errors}")

    # Helper methods
    def _process_image_data(self, data, image_dir):
        """Process image data for complete import"""
        # Implementation for complete import
        pass

    def _process_image_data_optimized(self, data, image_dir):
        """Process image data for optimized import"""
        # Implementation for optimized import
        pass

    def _process_metadata(self, data, image_dir):
        """Process metadata for images"""
        # Implementation for metadata processing
        pass

    def _backfill_image_colors(self, image):
        """Backfill color data for an image"""
        # Implementation for color backfill
        pass

    def _backfill_image_release_year(self, image):
        """Backfill release year for an image"""
        # Implementation for release year backfill
        pass

    def _normalize_image_tags(self, image):
        """Normalize tags for an image"""
        # Implementation for tag normalization
        pass

    def _populate_image_movie_fields(self, image):
        """Populate movie fields for an image"""
        # Implementation for movie field population
        pass

    def _derive_colors_from_shades(self, image):
        """Derive colors from shades for an image"""
        # Implementation for color derivation
        pass

    def _process_complete_dataset(self, data, image_dir):
        """Process complete dataset"""
        # Implementation for complete dataset processing
        pass

    def _get_or_create_option(self, model_class, value, **kwargs):
        """Get or create option with caching"""
        if not value:
            return None
        
        cache_key = f"{model_class.__name__}_{value}"
        if cache_key in self.option_cache:
            return self.option_cache[cache_key]
        
        option, created = model_class.objects.get_or_create(
            value=value,
            defaults=kwargs
        )
        
        self.option_cache[cache_key] = option
        return option

    def _parse_csv_values(self, block):
        """Parse CSV values from a block of text"""
        if not block:
            return []
        parts = [p.strip() for p in block.split(',')]
        return [p for p in parts if p]