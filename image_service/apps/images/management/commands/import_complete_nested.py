#!/usr/bin/env python3
"""
Complete Shotdeck Import - Extracts ALL nested metadata
Handles the nested JSON structure: shot_info -> field -> values[0] -> display_value
"""
import os
import json
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from apps.images.models import *

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import 3000 images with COMPLETE nested metadata"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option_cache = {}
        self.stats = {
            'processed': 0, 'updated': 0, 'created': 0, 'errors': 0,
            'fields_filled': {}
        }

    def add_arguments(self, parser):
        parser.add_argument('--json-dir', type=str, default='/host_data/shot_json_data')
        parser.add_argument('--limit', type=int, default=3000)
        parser.add_argument('--batch-size', type=int, default=100)
        parser.add_argument('--update-existing', action='store_true', default=True)
        parser.add_argument('--no-create-images', action='store_true', default=False,
                            help='Only update existing Image rows; skip creation when missing')
        parser.add_argument('--only-db-slugs', action='store_true', default=False,
                            help='Restrict import to JSONs whose base filename matches Image.slug in DB')
        parser.add_argument('--ids-file', type=str, default=None,
                            help='Optional path to a newline-delimited list of image IDs to import (case-insensitive)')
        parser.add_argument(
            '--image-url-template',
            type=str,
            default='/media/images/{id}.jpg',
            help=(
                'Template used to build image_url for each record. '
                'Use {id} as placeholder for the image code, e.g. '
                '"http://192.168.100.11:4008/images/shots/shot/{id}.jpg".'
            ),
        )

    def handle(self, *args, **options):
        json_dir = options['json_dir']
        limit = options['limit']
        batch_size = options['batch_size']
        update_existing = options['update_existing']
        self.image_url_template = options['image_url_template']
        only_db_slugs: bool = options['only_db_slugs']
        no_create_images: bool = options['no_create_images']
        ids_file: str | None = options.get('ids_file')
        
        if not os.path.exists(json_dir):
            raise CommandError(f"JSON directory not found: {json_dir}")
        
        json_files = sorted([f for f in os.listdir(json_dir) if f.endswith('.json')])

        # Build allowed id set if requested
        allowed_ids: set[str] | None = None
        if only_db_slugs:
            from apps.images.models import Image as ImageModel
            db_slugs = set(s.lower() for s in ImageModel.objects.values_list('slug', flat=True))
            allowed_ids = db_slugs if allowed_ids is None else (allowed_ids & db_slugs)
        if ids_file and os.path.exists(ids_file):
            with open(ids_file, 'r', encoding='utf-8') as fh:
                file_ids = {line.strip().lower() for line in fh if line.strip()}
            allowed_ids = file_ids if allowed_ids is None else (allowed_ids & file_ids)

        if allowed_ids is not None:
            before = len(json_files)
            json_files = [f for f in json_files if os.path.splitext(f)[0].lower() in allowed_ids]
            self.stdout.write(f"Filtered JSON files by allowed IDs: {len(json_files)} of {before}")
        
        if limit:
            json_files = json_files[:limit]
        
        self.stdout.write(f"🚀 Processing {len(json_files)} files with FULL metadata extraction...")
        
        for idx, json_file in enumerate(json_files, 1):
            try:
                json_path = os.path.join(json_dir, json_file)
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                with transaction.atomic():
                    self._process_image(data, json_file, update_existing, no_create_images)
                
                if idx % batch_size == 0:
                    self._print_progress(idx, len(json_files))
                    
            except Exception as e:
                self.stderr.write(f"✗ {json_file}: {str(e)}")
                self.stats['errors'] += 1
        
        self._print_final_stats()

    def _process_image(self, data, filename, update_existing, no_create_images=False):
        """Process image with nested metadata extraction"""
        
        # Get image ID from filename
        image_id = os.path.splitext(filename)[0]
        
        # Navigate to details
        if 'data' not in data or 'details' not in data['data']:
            raise ValueError("Invalid JSON structure")
        
        details = data['data']['details']
        
        # Extract basic info
        title = self._extract_nested_value(details, 'title')
        full_title = details.get('full_title', '')
        year_str = self._extract_nested_value(details, 'year')
        media_type_val = self._extract_nested_value(details, 'media_type')
        
        # Parse year
        release_year = None
        if year_str:
            try:
                release_year = int(str(year_str).split('-')[0])
            except:
                pass
        
        # Ensure we have a Movie first (Image.movie is NOT NULL)
        movie_title = title or full_title or image_id
        # Prefer matching on (title, year) when year is available to avoid duplicates
        if release_year is not None:
            movie, _ = Movie.objects.get_or_create(title=movie_title, year=release_year)
        else:
            movie, _ = Movie.objects.get_or_create(title=movie_title)

        # Create/update image (avoid get_or_create due to NOT NULL movie)
        # Build image URL without copying to MEDIA_ROOT
        try:
            image_url = str(self.image_url_template).format(id=image_id)
        except Exception:
            image_url = f"/media/images/{image_id}.jpg"
        image = Image.objects.filter(slug=image_id.lower()).first()
        if image is None:
            if no_create_images:
                # Skip if creation not allowed
                self.stats['processed'] += 1
                return
            image = Image(
                slug=image_id.lower(),
                title=movie_title,
                image_url=image_url,
                release_year=release_year,
                movie=movie,
            )
            image.save()
            created = True
            self.stats['created'] += 1
        else:
            created = False
            self.stats['updated'] += 1
        
        # Update existing fields when requested (including image_url)
        if not created:
            if not update_existing:
                return
            # Always refresh image_url to match the template (no local copy)
            if image.image_url != image_url:
                image.image_url = image_url
        
        # Update title/movie if we have a better title
        if title:
            image.title = title
            if image.movie_id != movie.id:
                image.movie = movie
        
        # Extract shot_info metadata
        shot_info = details.get('shot_info', {})
        self._process_shot_info(image, shot_info)
        
        # Extract title_info metadata (crew)
        title_info = details.get('title_info', {})
        self._process_title_info(image, title_info)
        
        # Process media type
        if media_type_val:
            image.media_type = self._get_or_create_option(MediaTypeOption, media_type_val)
            self._track_field('media_type')
        
        # Process shades (first one as primary color)
        shade_data = details.get('shade', {})
        if isinstance(shade_data, dict) and 'values' in shade_data:
            shades = shade_data['values']
            if shades and len(shades) > 0:
                first_shade = shades[0].get('display_value')
                if first_shade:
                    image.shade = self._get_or_create_option(ShadeOption, first_shade)
                    self._track_field('shade')
        
        # Save all changes
        image.save()
        self.stats['processed'] += 1

    def _process_shot_info(self, image, shot_info):
        """Extract all fields from shot_info"""
        
        # Map shot_info fields to model fields and their option classes
        field_mappings = {
            'camera': ('camera', CameraOption),
            'lens': ('lens', LensOption),
            'lens_type': ('lens_type', LensTypeOption),
            'film_stock': ('film_stock', FilmStockOption),
            'aspect_ratio': ('aspect_ratio', AspectRatioOption),
            'format': ('format', FormatOption),
            'optical_format': ('optical_format', OpticalFormatOption),
            'frame_size': ('frame_size', FrameSizeOption),
            'shot_type': ('shot_type', ShotTypeOption),
            'composition': ('composition', CompositionOption),
            'lighting': ('lighting', LightingOption),
            'lighting_type': ('lighting_type', LightingTypeOption),
            'time_of_day': ('time_of_day', TimeOfDayOption),
            'time_period': ('time_period', TimePeriodOption),
            'int_ext': ('interior_exterior', InteriorExteriorOption),
            'color': ('color', ColorOption),
            'location': ('location', LocationOption),
            'location_type': ('location_type', LocationTypeOption),
            'filming_location': ('filming_location', FilmingLocationOption),
            'setting': ('setting', SettingOption),
            'shot_time': ('shot_time', ShotTimeOption),
        }
        
        for json_field, (model_field, option_class) in field_mappings.items():
            if json_field in shot_info:
                value = self._extract_from_nested_dict(shot_info[json_field])
                if value:
                    option = self._get_or_create_option(option_class, value)
                    if option:
                        setattr(image, model_field, option)
                        self._track_field(model_field)
        
        # Handle tags (many-to-many)
        if 'tags' in shot_info:
            tags_data = shot_info['tags']
            if isinstance(tags_data, dict) and 'values' in tags_data:
                for tag_item in tags_data['values']:
                    tag_name = tag_item.get('display_value')
                    if tag_name:
                        # Do not pass slug; Tag.save() ensures a unique slug
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        image.tags.add(tag)
                        self._track_field('tags')
        
        # Handle actors
        if 'actors' in shot_info:
            actor_val = self._extract_from_nested_dict(shot_info['actors'])
            if actor_val:
                image.actor = self._get_or_create_option(ActorOption, actor_val)
                self._track_field('actor')

    def _process_title_info(self, image, title_info):
        """Extract all crew fields from title_info"""
        
        field_mappings = {
            'director': ('director', DirectorOption),
            'cinematographer': ('cinematographer', CinematographerOption),
            'editor': ('editor', EditorOption),
            'production_designer': ('production_designer', ProductionDesignerOption),
            'costume_designer': ('costume_designer', CostumeDesignerOption),
            'colorist': ('colorist', ColoristOption),
        }
        
        for json_field, (model_field, option_class) in field_mappings.items():
            if json_field in title_info:
                value = self._extract_from_nested_dict(title_info[json_field])
                if value:
                    option = self._get_or_create_option(option_class, value)
                    if option:
                        setattr(image, model_field, option)
                        self._track_field(model_field)
        
        # Handle genre (many-to-many)
        if 'genre' in title_info:
            genre_val = self._extract_from_nested_dict(title_info['genre'])
            if genre_val:
                # Handle comma-separated genres
                genre_names = [g.strip() for g in str(genre_val).split(',') if g.strip()]
                for genre_name in genre_names:
                    genre = self._get_or_create_option(GenreOption, genre_name)
                    if genre:
                        image.genre.add(genre)
                        self._track_field('genre')

    def _extract_nested_value(self, details, field_name):
        """Extract value from top-level nested structure"""
        if field_name not in details:
            return None
        
        field_data = details[field_name]
        return self._extract_from_nested_dict(field_data)

    def _extract_from_nested_dict(self, field_data):
        """Extract display_value from nested dict structure"""
        if not field_data:
            return None
        
        # If it's already a string, return it
        if isinstance(field_data, str):
            return field_data
        
        # If it's a dict with 'values' key
        if isinstance(field_data, dict):
            if 'values' in field_data and field_data['values']:
                first_value = field_data['values'][0]
                if isinstance(first_value, dict):
                    return first_value.get('display_value') or first_value.get('value')
                return str(first_value)
            elif 'display_value' in field_data:
                return field_data['display_value']
            elif 'value' in field_data:
                return field_data['value']
        
        return None

    def _get_or_create_option(self, model_class, value):
        """Get or create option with caching"""
        if not value:
            return None
        
        value = str(value).strip()
        if not value:
            return None
        
        cache_key = f"{model_class.__name__}_{value}"
        if cache_key in self.option_cache:
            return self.option_cache[cache_key]
        
        # Avoid passing slug defaults so model save() can ensure unique slugs
        option, created = model_class.objects.get_or_create(value=value)
        self.option_cache[cache_key] = option

        return option

    def _track_field(self, field_name):
        """Track that a field was populated"""
        self.stats['fields_filled'][field_name] = self.stats['fields_filled'].get(field_name, 0) + 1

    def _print_progress(self, current, total):
        percentage = (current / total) * 100
        self.stdout.write(
            f"  {current}/{total} ({percentage:.1f}%) | "
            f"Created: {self.stats['created']} | Updated: {self.stats['updated']} | "
            f"Errors: {self.stats['errors']}"
        )

    def _print_final_stats(self):
        self.stdout.write("\n" + "="*70)
        self.stdout.write("✅ IMPORT COMPLETE")
        self.stdout.write("="*70)
        self.stdout.write(f"Processed: {self.stats['processed']}")
        self.stdout.write(f"Created: {self.stats['created']}")
        self.stdout.write(f"Updated: {self.stats['updated']}")
        self.stdout.write(f"Errors: {self.stats['errors']}")
        
        if self.stats['fields_filled']:
            self.stdout.write("\n📊 Metadata Fields Populated:")
            sorted_fields = sorted(
                self.stats['fields_filled'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for field, count in sorted_fields:
                percentage = (count / self.stats['processed'] * 100) if self.stats['processed'] > 0 else 0
                bar_length = int(percentage / 2)
                bar = '█' * bar_length + '░' * (50 - bar_length)
                self.stdout.write(f"  {field:25} {bar} {count:4} ({percentage:5.1f}%)")
        
        self.stdout.write("="*70)
