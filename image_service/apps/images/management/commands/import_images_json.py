from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from apps.images.models import (
    Image,
    Movie,
    MediaTypeOption,
    GenreOption,
    ColorOption,
    AspectRatioOption,
    OpticalFormatOption,
    FormatOption,
    LabProcessOption,
    TimePeriodOption,
    InteriorExteriorOption,
    TimeOfDayOption,
    NumberOfPeopleOption,
    GenderOption,
    AgeOption,
    EthnicityOption,
    FrameSizeOption,
    ShotTypeOption,
    CompositionOption,
    LensSizeOption,
    LensTypeOption,
    LightingOption,
    LightingTypeOption,
    CameraTypeOption,
    ResolutionOption,
    FrameRateOption,
    ActorOption,
    CameraOption,
    LensOption,
    LocationOption,
    SettingOption,
    FilmStockOption,
    ShotTimeOption,
    DescriptionOption,
    VfxBackingOption,
    DirectorOption,
    CinematographerOption,
    EditorOption,
    ColoristOption,
    CostumeDesignerOption,
    ProductionDesignerOption,
    ShadeOption,
    ArtistOption,
    FilmingLocationOption,
    LocationTypeOption,
    YearOption,
)
import os
import json


def get_or_none(model, value):
    if value in (None, "", []):
        return None
    obj, _ = model.objects.get_or_create(value=str(value))
    return obj


def extract_filter_value(data, filter_key):
    """Extract value from nested JSON filter structure"""
    if not isinstance(data, dict):
        return None
    
    # Check if it's the nested structure with details
    if 'details' in data and isinstance(data['details'], dict):
        details = data['details']
        if filter_key in details and isinstance(details[filter_key], dict):
            filter_data = details[filter_key]
            if 'values' in filter_data and isinstance(filter_data['values'], list) and len(filter_data['values']) > 0:
                return filter_data['values'][0].get('display_value')
    
    # Check direct key access
    if filter_key in data:
        value = data[filter_key]
        if isinstance(value, dict) and 'values' in value and isinstance(value['values'], list) and len(value['values']) > 0:
            return value['values'][0].get('display_value')
        elif isinstance(value, str):
            return value
    
    return None


class Command(BaseCommand):
    help = "Import images from JSON files into the database in deterministic order (per-file transaction)."

    def add_arguments(self, parser):
        parser.add_argument('--json-dir', type=str, default='/home/a/Desktop/shotdeck/dataset/shot_json_data', help='Directory containing JSON files')
        parser.add_argument('--dry-run', action='store_true', help='Only show what would be imported')
        parser.add_argument('--limit', type=int, default=None, help='Limit number of JSON files processed')
        parser.add_argument('--force', action='store_true', help='If image slug/url exists, replace it')

    def handle(self, *args, **options):
        json_dir = options['json_dir']
        dry_run = options['dry_run']
        limit = options['limit']
        force = options['force']

        if not os.path.isdir(json_dir):
            self.stderr.write(self.style.ERROR(f"JSON directory not found: {json_dir}"))
            return

        # Deterministic order: sort by filename
        filenames = [f for f in os.listdir(json_dir) if f.lower().endswith('.json') and os.path.isfile(os.path.join(json_dir, f))]
        filenames.sort()
        if limit is not None:
            filenames = filenames[:limit]

        total_created = 0
        total_updated = 0
        total_skipped = 0

        for fname in filenames:
            file_path = os.path.join(json_dir, fname)
            self.stdout.write(f"Processing file: {file_path}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to read {file_path}: {e}"))
                continue

            # Each file in its own atomic transaction to avoid mixing data across files
            try:
                with transaction.atomic():
                    created, updated, skipped = self._import_one_file(data, dry_run=dry_run, force=force)
                    total_created += created
                    total_updated += updated
                    total_skipped += skipped
                    if dry_run:
                        raise transaction.TransactionManagementError("Dry run rollback")
            except transaction.TransactionManagementError as tm:
                if str(tm) != "Dry run rollback":
                    self.stderr.write(self.style.ERROR(f"Transaction error in {file_path}: {tm}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Dry run: rolled back changes for {file_path}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error importing {file_path}: {e}"))
                continue

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run complete. Would create {total_created}, update {total_updated}, skip {total_skipped}."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Import complete. Created {total_created}, updated {total_updated}, skipped {total_skipped}."))

    def _import_one_file(self, data, dry_run=False, force=False):
        # Support both list of records or object with a key
        if isinstance(data, dict):
            # Try common keys
            if 'data' in data and isinstance(data['data'], dict):
                # Single record format with nested data
                records = [data['data']]
            elif 'images' in data and isinstance(data['images'], list):
                records = data['images']
            else:
                # assume values
                records = list(data.values())
        elif isinstance(data, list):
            records = data
        else:
            records = []

        created = 0
        updated = 0
        skipped = 0

        for rec in records:
            if not isinstance(rec, dict):
                skipped += 1
                continue

            # Basic fields from JSON (with common aliases)
            image_id = rec.get('imageid') or rec.get('image_id') or rec.get('id')
            image_file = rec.get('image_file') or rec.get('image_url') or rec.get('file')
            
            # Extract title from nested structure
            title = extract_filter_value(rec, 'title') or rec.get('title') or (str(image_id) if image_id is not None else os.path.basename(str(image_file)) if image_file else None) or 'Untitled'
            description = rec.get('description')

            # Build a stable URL or path. Prefer provided URL else make relative under MEDIA_ROOT/images
            if image_file and (str(image_file).startswith('http://') or str(image_file).startswith('https://') or str(image_file).startswith('/')):
                image_url = str(image_file)
            elif image_file:
                image_url = f"/media/images/{image_file}"
            else:
                image_url = None

            # Determine uniqueness: prefer slug based on movie+shot if present else image_url
            movie_title = extract_filter_value(rec, 'title') or rec.get('movie') or rec.get('movie_title')
            movie_year = extract_filter_value(rec, 'year') or rec.get('year') or rec.get('release_year')
            movie = None
            if movie_title:
                movie, _ = Movie.objects.get_or_create(title=str(movie_title), defaults={'year': movie_year if isinstance(movie_year, int) else None})

            # Find existing image by url or by slug strategy
            existing_qs = Image.objects
            if image_url:
                existing_qs = existing_qs.filter(image_url=image_url)
            if movie and image_url:
                # slug is generated from movie slug + filename; but not available before save.
                pass

            if existing_qs.exists():
                img = existing_qs.first()
                if not force:
                    skipped += 1
                    continue
            else:
                img = Image()

            img.title = title
            img.description = description
            if image_url:
                img.image_url = image_url
            if movie:
                img.movie = movie

            # Map option fields using the extraction function
            img.media_type = get_or_none(MediaTypeOption, extract_filter_value(rec, 'media_type'))
            img.color = get_or_none(ColorOption, extract_filter_value(rec, 'color'))
            img.aspect_ratio = get_or_none(AspectRatioOption, extract_filter_value(rec, 'aspect_ratio'))
            img.optical_format = get_or_none(OpticalFormatOption, extract_filter_value(rec, 'optical_format'))
            img.format = get_or_none(FormatOption, extract_filter_value(rec, 'format'))
            img.lab_process = get_or_none(LabProcessOption, extract_filter_value(rec, 'lab_process'))
            img.time_period = get_or_none(TimePeriodOption, extract_filter_value(rec, 'time_period'))
            img.interior_exterior = get_or_none(InteriorExteriorOption, extract_filter_value(rec, 'interior_exterior'))
            img.time_of_day = get_or_none(TimeOfDayOption, extract_filter_value(rec, 'time_of_day'))
            img.number_of_people = get_or_none(NumberOfPeopleOption, extract_filter_value(rec, 'number_of_people'))
            img.gender = get_or_none(GenderOption, extract_filter_value(rec, 'gender'))
            img.age = get_or_none(AgeOption, extract_filter_value(rec, 'age'))
            img.ethnicity = get_or_none(EthnicityOption, extract_filter_value(rec, 'ethnicity'))
            img.frame_size = get_or_none(FrameSizeOption, extract_filter_value(rec, 'frame_size'))
            img.shot_type = get_or_none(ShotTypeOption, extract_filter_value(rec, 'shot_type'))
            img.composition = get_or_none(CompositionOption, extract_filter_value(rec, 'composition'))
            img.lens_size = get_or_none(LensSizeOption, extract_filter_value(rec, 'lens_size'))
            img.lens_type = get_or_none(LensTypeOption, extract_filter_value(rec, 'lens_type'))
            img.lighting = get_or_none(LightingOption, extract_filter_value(rec, 'lighting'))
            img.lighting_type = get_or_none(LightingTypeOption, extract_filter_value(rec, 'lighting_type'))
            img.camera_type = get_or_none(CameraTypeOption, extract_filter_value(rec, 'camera_type'))
            img.resolution = get_or_none(ResolutionOption, extract_filter_value(rec, 'resolution'))
            img.frame_rate = get_or_none(FrameRateOption, extract_filter_value(rec, 'frame_rate'))

            # Newer filter fields
            img.actor = get_or_none(ActorOption, extract_filter_value(rec, 'actor'))
            img.camera = get_or_none(CameraOption, extract_filter_value(rec, 'camera'))
            img.lens = get_or_none(LensOption, extract_filter_value(rec, 'lens'))
            img.location = get_or_none(LocationOption, extract_filter_value(rec, 'location'))
            img.setting = get_or_none(SettingOption, extract_filter_value(rec, 'setting'))
            img.film_stock = get_or_none(FilmStockOption, extract_filter_value(rec, 'film_stock'))
            img.shot_time = get_or_none(ShotTimeOption, extract_filter_value(rec, 'shot_time'))
            img.description_filter = get_or_none(DescriptionOption, extract_filter_value(rec, 'description'))
            img.vfx_backing = get_or_none(VfxBackingOption, extract_filter_value(rec, 'vfx_backing'))

            # Crew fields
            img.director = get_or_none(DirectorOption, extract_filter_value(rec, 'director'))
            img.cinematographer = get_or_none(CinematographerOption, extract_filter_value(rec, 'cinematographer'))
            img.editor = get_or_none(EditorOption, extract_filter_value(rec, 'editor'))
            img.colorist = get_or_none(ColoristOption, extract_filter_value(rec, 'colorist'))
            img.costume_designer = get_or_none(CostumeDesignerOption, extract_filter_value(rec, 'costume_designer'))
            img.production_designer = get_or_none(ProductionDesignerOption, extract_filter_value(rec, 'production_designer'))

            # Additional options
            img.shade = get_or_none(ShadeOption, extract_filter_value(rec, 'shade'))
            img.artist = get_or_none(ArtistOption, extract_filter_value(rec, 'artist'))
            img.filming_location = get_or_none(FilmingLocationOption, extract_filter_value(rec, 'filming_location'))
            img.location_type = get_or_none(LocationTypeOption, extract_filter_value(rec, 'location_type'))
            img.year = get_or_none(YearOption, extract_filter_value(rec, 'year'))

            # Booleans
            if 'exclude_nudity' in rec:
                img.exclude_nudity = bool(rec.get('exclude_nudity'))
            if 'exclude_violence' in rec:
                img.exclude_violence = bool(rec.get('exclude_violence'))

            # Save image before M2M
            img.save()

            # ManyToMany: genre and tags
            genre_val = extract_filter_value(rec, 'genre')
            if genre_val:
                # Normalize to list
                if isinstance(genre_val, str):
                    genres = [genre_val]
                elif isinstance(genre_val, list):
                    genres = genre_val
                else:
                    genres = []
                img.genre.clear()
                for g in genres:
                    g_obj, _ = GenreOption.objects.get_or_create(value=str(g))
                    img.genre.add(g_obj)

            tags_val = rec.get('tags')
            if tags_val:
                from apps.images.models import Tag
                if isinstance(tags_val, str):
                    tags = [t.strip() for t in tags_val.split(',') if t.strip()]
                elif isinstance(tags_val, list):
                    tags = [str(t) for t in tags_val]
                else:
                    tags = []
                img.tags.clear()
                for t in tags:
                    tag_obj, _ = Tag.objects.get_or_create(name=t)
                    img.tags.add(tag_obj)

            if existing_qs.exists():
                updated += 1
            else:
                created += 1

        return created, updated, skipped


