#!/usr/bin/env python3
"""Import without genre field (causes errors)"""
import os
import json
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from apps.images.models import *

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import 3000 images - SKIP GENRE field"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option_cache = {}
        self.stats = {'processed': 0, 'updated': 0, 'created': 0, 'errors': 0, 'fields_filled': {}}

    def add_arguments(self, parser):
        parser.add_argument('--json-dir', type=str, default='/host_data/shot_json_data')
        parser.add_argument('--limit', type=int, default=3000)
        parser.add_argument('--batch-size', type=int, default=100)
        parser.add_argument('--update-existing', action='store_true', default=True)

    def handle(self, *args, **options):
        json_dir = options['json_dir']
        limit = options['limit']
        batch_size = options['batch_size']
        update_existing = options['update_existing']
        
        if not os.path.exists(json_dir):
            raise CommandError(f"JSON directory not found: {json_dir}")
        
        json_files = sorted([f for f in os.listdir(json_dir) if f.endswith('.json')])
        
        if limit:
            json_files = json_files[:limit]
        
        self.stdout.write(f"🚀 Processing {len(json_files)} files (SKIPPING GENRE)...")
        
        for idx, json_file in enumerate(json_files, 1):
            try:
                json_path = os.path.join(json_dir, json_file)
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                with transaction.atomic():
                    self._process_image(data, json_file, update_existing)
                
                if idx % batch_size == 0:
                    self._print_progress(idx, len(json_files))
                    
            except Exception as e:
                self.stderr.write(f"✗ {json_file}: {str(e)}")
                self.stats['errors'] += 1
        
        self._print_final_stats()

    def _process_image(self, data, filename, update_existing):
        image_id = os.path.splitext(filename)[0]
        
        if 'data' not in data or 'details' not in data['data']:
            raise ValueError("Invalid JSON structure")
        
        details = data['data']['details']
        
        title = self._extract_nested_value(details, 'title')
        full_title = details.get('full_title', '')
        year_str = self._extract_nested_value(details, 'year')
        media_type_val = self._extract_nested_value(details, 'media_type')
        
        release_year = None
        if year_str:
            try:
                release_year = int(str(year_str).split('-')[0])
            except:
                pass
        
        image_url = f"/media/images/{image_id}.jpg"
        
        image, created = Image.objects.get_or_create(
            slug=image_id.lower(),
            defaults={'title': title or full_title or image_id, 'image_url': image_url, 'release_year': release_year}
        )
        
        if created:
            self.stats['created'] += 1
        else:
            self.stats['updated'] += 1
            if not update_existing:
                return
        
        if title:
            image.title = title
        
        if title:
            movie, _ = Movie.objects.get_or_create(title=title, defaults={'year': release_year})
            image.movie = movie
        
        shot_info = details.get('shot_info', {})
        self._process_shot_info(image, shot_info)
        
        title_info = details.get('title_info', {})
        self._process_title_info(image, title_info)
        
        if media_type_val:
            image.media_type = self._get_or_create_option(MediaTypeOption, media_type_val)
            self._track_field('media_type')
        
        shade_data = details.get('shade', {})
        if isinstance(shade_data, dict) and 'values' in shade_data:
            shades = shade_data['values']
            if shades and len(shades) > 0:
                first_shade = shades[0].get('display_value')
                if first_shade:
                    image.shade = self._get_or_create_option(ShadeOption, first_shade)
                    self._track_field('shade')
        
        image.save()
        self.stats['processed'] += 1

    def _process_shot_info(self, image, shot_info):
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
        
        if 'tags' in shot_info:
            tags_data = shot_info['tags']
            if isinstance(tags_data, dict) and 'values' in tags_data:
                for tag_item in tags_data['values']:
                    tag_name = tag_item.get('display_value')
                    if tag_name:
                        tag, _ = Tag.objects.get_or_create(name=tag_name, defaults={'slug': slugify(tag_name)})
                        image.tags.add(tag)
                        self._track_field('tags')
        
        if 'actors' in shot_info:
            actor_val = self._extract_from_nested_dict(shot_info['actors'])
            if actor_val:
                image.actor = self._get_or_create_option(ActorOption, actor_val)
                self._track_field('actor')

    def _process_title_info(self, image, title_info):
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
        
        # SKIP GENRE - causes table error

    def _extract_nested_value(self, details, field_name):
        if field_name not in details:
            return None
        return self._extract_from_nested_dict(details[field_name])

    def _extract_from_nested_dict(self, field_data):
        if not field_data:
            return None
        if isinstance(field_data, str):
            return field_data
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
        if not value:
            return None
        value = str(value).strip()
        if not value:
            return None
        cache_key = f"{model_class.__name__}_{value}"
        if cache_key in self.option_cache:
            return self.option_cache[cache_key]
        kwargs = {}
        model_fields = [f.name for f in model_class._meta.fields]
        if 'slug' in model_fields:
            kwargs['slug'] = slugify(value)
        option, created = model_class.objects.get_or_create(value=value, defaults=kwargs)
        self.option_cache[cache_key] = option
        return option

    def _track_field(self, field_name):
        self.stats['fields_filled'][field_name] = self.stats['fields_filled'].get(field_name, 0) + 1

    def _print_progress(self, current, total):
        percentage = (current / total) * 100
        self.stdout.write(f"  {current}/{total} ({percentage:.1f}%) | Created: {self.stats['created']} | Updated: {self.stats['updated']} | Errors: {self.stats['errors']}")

    def _print_final_stats(self):
        self.stdout.write("\n" + "="*70)
        self.stdout.write("✅ IMPORT COMPLETE (Genre skipped)")
        self.stdout.write("="*70)
        self.stdout.write(f"Processed: {self.stats['processed']}")
        self.stdout.write(f"Created: {self.stats['created']}")
        self.stdout.write(f"Updated: {self.stats['updated']}")
        self.stdout.write(f"Errors: {self.stats['errors']}")
        if self.stats['fields_filled']:
            self.stdout.write("\n📊 Metadata Fields Populated:")
            sorted_fields = sorted(self.stats['fields_filled'].items(), key=lambda x: x[1], reverse=True)
            for field, count in sorted_fields:
                percentage = (count / self.stats['processed'] * 100) if self.stats['processed'] > 0 else 0
                bar_length = int(percentage / 2)
                bar = '█' * bar_length + '░' * (50 - bar_length)
                self.stdout.write(f"  {field:25} {bar} {count:4} ({percentage:5.1f}%)")
        self.stdout.write("="*70)
