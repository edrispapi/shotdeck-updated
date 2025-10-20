#!/usr/bin/env python3
import os
import json
import logging
from typing import Dict, List, Optional
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from apps.images.models import Image, ColorOption

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Backfill color data for existing images from their JSON files"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/service/backfill_colors.log'),
                logging.StreamHandler()
            ]
        )

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of images to process per batch'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving to database'
        )
        parser.add_argument(
            '--json-dir',
            type=str,
            default='/host_data/dataset/shot_json_data',
            help='Path to JSON files directory'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of images to process (for testing)'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        json_dir = options['json_dir']
        limit = options.get('limit')

        self.stdout.write("Backfilling color data for existing images")
        self.stdout.write(f"JSON Directory: {json_dir}")
        self.stdout.write(f"Batch size: {batch_size}, Dry run: {dry_run}")
        if limit:
            self.stdout.write(f"Limit: {limit} images")

        # Get images without color
        qs = Image.objects.filter(color__isnull=True)
        if limit:
            qs = qs[:limit]
        total_targets = qs.count()
        self.stdout.write(f"Images without color: {total_targets}")

        updated_images = 0
        created_color_options = 0
        errors = 0

        if total_targets > 0:
            for i in range(0, total_targets, batch_size):
                batch = qs[i:i + batch_size]
                with transaction.atomic():
                    for image in batch:
                        try:
                            # Extract imageid from slug
                            imageid = image.slug.split('-')[0].upper()
                            json_file = os.path.join(json_dir, f'{imageid}.json')
                            
                            if not os.path.exists(json_file):
                                self.logger.warning(f"JSON file not found: {json_file}")
                                continue
                            
                            # Read JSON file
                            with open(json_file, 'r') as f:
                                data = json.load(f)
                            
                            # Extract color data
                            shot_info = data.get('data', {}).get('details', {}).get('shot_info', {})
                            color_data = shot_info.get('color', {})
                            color_values = color_data.get('values', [])
                            
                            if color_values:
                                # Use the first color value
                                first_color = color_values[0]['display_value']
                                
                                # Create or get ColorOption
                                color_option, created = ColorOption.objects.get_or_create(
                                    value=first_color
                                )
                                
                                if created:
                                    created_color_options += 1
                                
                                # Assign color to image
                                image.color = color_option
                                if not dry_run:
                                    image.save(update_fields=['color'])
                                updated_images += 1
                                
                                if dry_run:
                                    self.stdout.write(f"Would assign color '{first_color}' to image {image.slug}")
                            
                        except Exception as e:
                            self.logger.error(f"Error processing image {image.slug}: {e}")
                            errors += 1
                
                self.stdout.write(f"Processed {min(i + batch_size, total_targets)}/{total_targets} (updated={updated_images}, new_color_options={created_color_options}, errors={errors})")

        self.stdout.write(f"Done. Updated images: {updated_images}, Created color options: {created_color_options}, Errors: {errors}")
