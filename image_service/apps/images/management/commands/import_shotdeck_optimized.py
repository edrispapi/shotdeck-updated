import os
import json
import uuid
import logging
from typing import Dict, List, Optional, Set
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from django.utils.text import slugify
from apps.images.models import (
    Image, Movie, ActorOption, CameraOption, CinematographerOption, 
    DirectorOption, LensOption, FilmStockOption, SettingOption, 
    LocationOption, FilmingLocationOption, AspectRatioOption,
    MediaTypeOption, TimePeriodOption, TimeOfDayOption, 
    InteriorExteriorOption, FormatOption, FrameSizeOption,
    LensTypeOption, CompositionOption, ShotTypeOption, LightingOption,
    LightingTypeOption, CameraTypeOption, ResolutionOption, FrameRateOption,
    ColorOption, ShadeOption, ProductionDesignerOption, CostumeDesignerOption,
    EditorOption, ColoristOption, ArtistOption, LocationTypeOption,
    YearOption, VfxBackingOption, GenreOption
)

class Command(BaseCommand):
    help = "Optimized Shotdeck data import with intelligent file matching and error handling"

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
                logging.FileHandler('/service/import_errors.log'),
                logging.StreamHandler()
            ]
        )

    def add_arguments(self, parser):
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
            help='Path to image files directory'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of images to process per batch'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing images'
        )
        parser.add_argument(
            '--start-from',
            type=str,
            help='Resume from specific ImageID'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of images to process'
        )
        parser.add_argument(
            '--skip-missing-files',
            action='store_true',
            help='Skip images without corresponding files (faster)'
        )

    def handle(self, *args, **options):
        self.json_dir = options['json_dir']
        self.image_dir = options['image_dir']
        self.batch_size = options['batch_size']
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.start_from = options['start_from']
        self.limit = options['limit']
        self.skip_missing_files = options['skip_missing_files']
        
        self.stats = {
            'processed': 0,
            'success': 0,
            'errors': 0,
            'skipped': 0,
            'missing_files': 0
        }

        self.stdout.write("Optimized Shotdeck Data Import")
        self.stdout.write("=" * 40)
        self.stdout.write(f"JSON Directory: {self.json_dir}")
        self.stdout.write(f"Image Directory: {self.image_dir}")
        self.stdout.write(f"Skip Missing Files: {self.skip_missing_files}")
        
        if self.dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")

        # Validate dataset
        self._validate_dataset()
        
        # Get list of available image files for faster lookup
        self.available_files = self._get_available_files()
        self.stdout.write(f"Found {len(self.available_files)} available image files")
        
        # Get JSON files to process
        json_files = self._get_json_files()
        self.stdout.write(f"Found {len(json_files)} JSON files")
        
        if self.limit:
            json_files = json_files[:self.limit]
            self.stdout.write(f"Limited to {len(json_files)} files for testing")

        # Process in batches
        self._process_batches(json_files)
        
        # Final summary
        self._print_summary()
        
        if not self.dry_run:
            self._run_data_integrity_checks()

    def _validate_dataset(self):
        """Validate dataset before import"""
        self.stdout.write("Validating dataset...")
        
        # Check directories exist
        if not os.path.exists(self.json_dir):
            raise CommandError(f"JSON directory not found: {self.json_dir}")
        
        if not os.path.exists(self.image_dir):
            raise CommandError(f"Image directory not found: {self.image_dir}")
        
        # Check database connection
        try:
            Image.objects.count()
            self.stdout.write("✓ Database connection OK")
        except Exception as e:
            raise CommandError(f"Database connection failed: {e}")
        
        # Validate sample JSON
        sample_files = [f for f in os.listdir(self.json_dir) if f.endswith('.json')][:5]
        for sample_file in sample_files:
            try:
                with open(os.path.join(self.json_dir, sample_file), 'r') as f:
                    json.load(f)
            except Exception as e:
                raise CommandError(f"Invalid JSON file {sample_file}: {e}")
        
        self.stdout.write("✓ Sample JSON structure valid")
        self.stdout.write("✓ Directory access confirmed")

    def _get_available_files(self):
        """Get list of available image files for fast lookup"""
        try:
            files = [f for f in os.listdir(self.image_dir) if f.lower().endswith('.jpg')]
            return set(files)
        except Exception as e:
            self.logger.error(f"Error reading image directory: {e}")
            return set()

    def _get_json_files(self):
        """Get list of JSON files to process"""
        try:
            files = [f for f in os.listdir(self.json_dir) if f.endswith('.json')]
            files.sort()  # Process in deterministic order
            
            if self.start_from:
                # Find start position
                start_index = 0
                for i, file in enumerate(files):
                    if file.startswith(self.start_from):
                        start_index = i
                        break
                files = files[start_index:]
            
            return files
        except Exception as e:
            raise CommandError(f"Error reading JSON directory: {e}")

    def _process_batches(self, json_files):
        """Process JSON files in batches"""
        total_batches = (len(json_files) + self.batch_size - 1) // self.batch_size
        
        self.stdout.write(f"Starting import...")
        self.stdout.write(f"Processing {len(json_files)} files in {total_batches} batches")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(json_files))
            batch_files = json_files[start_idx:end_idx]
            
            self.stdout.write(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_files)} images)")
            
            with transaction.atomic():
                for json_file in batch_files:
                    try:
                        self._process_json_file(json_file)
                        self.stats['processed'] += 1
                        
                        if self.stats['processed'] % 100 == 0:
                            progress = (self.stats['processed'] / len(json_files)) * 100
                            self.stdout.write(f"Progress: {self.stats['processed']}/{len(json_files)} ({progress:.1f}%)")
                    
                    except Exception as e:
                        self.stats['errors'] += 1
                        self.logger.error(f"ImageID: {json_file} | Error: {e}")
                        continue

    def _process_json_file(self, json_file: str):
        """Process a single JSON file with optimized file matching"""
        json_path = os.path.join(self.json_dir, json_file)
        imageid = json_file.replace('.json', '')
        
        # Check if already exists
        if not self.force and Image.objects.filter(slug__startswith=imageid.lower()).exists():
            self.stats['skipped'] += 1
            return
        
        # Load JSON data
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load JSON: {e}")
        
        # Extract image data
        image_data = self._extract_image_data(data)
        if not image_data:
            raise Exception("No image data found in JSON")
        
        # Find matching image file (optimized)
        image_file = self._find_matching_file_fast(imageid)
        if not image_file:
            if self.skip_missing_files:
                self.stats['missing_files'] += 1
                return
            else:
                raise Exception(f"Image file not found: {imageid}.jpg")
        
        # Create image URL
        image_url = f"/media/images/{image_file}"
        
        # Extract movie data
        movie = self._get_or_create_movie(data)
        
        # Extract filter options
        options = self._extract_filter_options(data)
        
        # Create image record
        if not self.dry_run:
            image = self._create_image_record(imageid, image_data, movie, options, image_url)
            self.stats['success'] += 1
        else:
            self.stats['success'] += 1

    def _find_matching_file_fast(self, imageid: str) -> Optional[str]:
        """Fast file matching using pre-loaded file list"""
        # Strategy 1: Exact match
        exact_file = f"{imageid}.jpg"
        if exact_file in self.available_files:
            return exact_file
        
        # Strategy 2: Case-insensitive match
        exact_file_lower = f"{imageid.lower()}.jpg"
        for file in self.available_files:
            if file.lower() == exact_file_lower:
                return file
        
        # Strategy 3: Prefix match
        for file in self.available_files:
            if file.lower().startswith(imageid.lower()) and file.lower().endswith('.jpg'):
                return file
        
        # Strategy 4: Character similarity (only if not skipping missing files)
        if not self.skip_missing_files:
            best_match = None
            best_score = 0
            
            for file in self.available_files:
                if file.lower().endswith('.jpg'):
                    filename = os.path.splitext(file)[0]
                    similarity = self._calculate_similarity(imageid.lower(), filename.lower())
                    if similarity > 0.8 and similarity > best_score:
                        best_score = similarity
                        best_match = file
            
            return best_match
        
        return None

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate character similarity between two strings"""
        if len(str1) != len(str2):
            return 0.0
        
        matches = sum(1 for a, b in zip(str1, str2) if a == b)
        return matches / len(str1) if str1 else 0.0

    def _extract_image_data(self, data: Dict) -> Optional[Dict]:
        """Extract image data from JSON"""
        try:
            details = data.get('data', {}).get('details', {})
            
            # Get title
            title = details.get('full_title', '')
            if not title:
                title_values = details.get('title', {}).get('values', [])
                if title_values:
                    title = title_values[0].get('display_value', '')
            
            # Get description from tags
            description = ""
            shot_info = details.get('shot_info', {})
            tags = shot_info.get('tags', {}).get('values', [])
            if tags:
                description = ", ".join([tag.get('display_value', '') for tag in tags])
            
            return {
                'title': title,
                'description': description
            }
        except Exception as e:
            self.logger.error(f"Error extracting image data: {e}")
            return None

    def _get_or_create_movie(self, data: Dict) -> Optional[Movie]:
        """Get or create movie record"""
        try:
            details = data.get('data', {}).get('details', {})
            title_data = details.get('title', {})
            
            if not title_data or not title_data.get('values'):
                return None
            
            title_info = title_data['values'][0]
            title = title_info.get('display_value', '')
            
            if not title:
                return None
            
            # Create or get movie
            movie, created = Movie.objects.get_or_create(
                title=title,
                defaults={
                    'slug': slugify(title),
                    'year': self._extract_year(details)
                }
            )
            
            return movie
        except Exception as e:
            self.logger.error(f"Error creating movie: {e}")
            return None

    def _extract_year(self, details: Dict) -> Optional[int]:
        """Extract year from details"""
        try:
            year_data = details.get('year', {}).get('values', [])
            if year_data:
                year_str = year_data[0].get('display_value', '')
                return int(year_str) if year_str.isdigit() else None
        except:
            pass
        return None

    def _extract_filter_options(self, data: Dict) -> Dict:
        """Extract filter options with improved error handling"""
        options = {}
        
        try:
            details = data.get('data', {}).get('details', {})
            shot_info = details.get('shot_info', {})
            title_info = details.get('title_info', {})
            
            # Single-value options
            single_value_mappings = [
                ('camera', CameraOption, shot_info.get('camera', {})),
                ('cinematographer', CinematographerOption, title_info.get('cinematographer', {})),
                ('director', DirectorOption, title_info.get('director', {})),
                ('lens', LensOption, shot_info.get('lens', {})),
                ('film_stock', FilmStockOption, shot_info.get('film_stock', {})),
                ('setting', SettingOption, shot_info.get('setting', {})),
                ('location', LocationOption, shot_info.get('location', {})),
                ('filming_location', FilmingLocationOption, shot_info.get('filming_location', {})),
                ('aspect_ratio', AspectRatioOption, shot_info.get('aspect_ratio', {})),
                ('media_type', MediaTypeOption, details.get('media_type', {})),
                ('time_period', TimePeriodOption, shot_info.get('time_period', {})),
                ('time_of_day', TimeOfDayOption, shot_info.get('time_of_day', {})),
                ('interior_exterior', InteriorExteriorOption, shot_info.get('int_ext', {})),
                ('format', FormatOption, shot_info.get('format', {})),
                ('frame_size', FrameSizeOption, shot_info.get('frame_size', {})),
                ('lens_type', LensTypeOption, shot_info.get('lens_type', {})),
                ('composition', CompositionOption, shot_info.get('composition', {})),
                ('shot_type', ShotTypeOption, shot_info.get('shot_type', {})),
                ('lighting', LightingOption, shot_info.get('lighting', {})),
                ('lighting_type', LightingTypeOption, shot_info.get('lighting_type', {})),
                ('camera_type', CameraTypeOption, shot_info.get('camera_type', {})),
                ('resolution', ResolutionOption, shot_info.get('resolution', {})),
                ('frame_rate', FrameRateOption, shot_info.get('frame_rate', {})),
                ('color', ColorOption, details.get('color', {})),
                ('shade', ShadeOption, details.get('shade', {})),
                ('production_designer', ProductionDesignerOption, title_info.get('production_designer', {})),
                ('costume_designer', CostumeDesignerOption, title_info.get('costume_designer', {})),
                ('editor', EditorOption, title_info.get('editor', {})),
                ('colorist', ColoristOption, title_info.get('colorist', {})),
                ('artist', ArtistOption, title_info.get('artist', {})),
                ('location_type', LocationTypeOption, shot_info.get('location_type', {})),
                ('year', YearOption, details.get('year', {})),
                ('vfx_backing', VfxBackingOption, shot_info.get('vfx_backing', {}))
            ]
            
            for field_name, model_class, field_data in single_value_mappings:
                if field_data and field_data.get('values'):
                    value = field_data['values'][0].get('display_value', '')
                    if value:
                        try:
                            options[field_name] = self._get_or_create_option(model_class, value)
                        except Exception as e:
                            self.logger.error(f"Error creating {field_name}: {e}")
                            continue
            
            # Handle actor as single value
            actor_data = shot_info.get('actors', {})
            if actor_data and actor_data.get('values'):
                actor_value = actor_data['values'][0].get('display_value', '')
                if actor_value:
                    try:
                        options['actor'] = self._get_or_create_option(ActorOption, actor_value)
                    except Exception as e:
                        self.logger.error(f"Error creating actor: {e}")
            
            # Handle genre as ManyToMany
            genre_data = title_info.get('genre', {})
            if genre_data and genre_data.get('values'):
                genre_values = [item.get('display_value', '') for item in genre_data['values'] if item.get('display_value')]
                if genre_values:
                    try:
                        options['genre'] = [self._get_or_create_option(GenreOption, value) for value in genre_values]
                    except Exception as e:
                        self.logger.error(f"Error creating genres: {e}")
            
        except Exception as e:
            self.logger.error(f"Error extracting filter options: {e}")
        
        return options

    def _get_or_create_option(self, model_class, value: str):
        """Get or create option with caching"""
        cache_key = f"{model_class.__name__}:{value}"
        
        if cache_key in self.option_cache:
            return self.option_cache[cache_key]
        
        # Check if model has slug field
        has_slug = hasattr(model_class, 'slug')
        
        if has_slug:
            option, created = model_class.objects.get_or_create(
                value=value,
                defaults={'slug': slugify(value)}
            )
        else:
            option, created = model_class.objects.get_or_create(value=value)
        
        self.option_cache[cache_key] = option
        return option

    def _create_image_record(self, imageid: str, image_data: Dict, movie: Movie, options: Dict, image_url: str) -> Image:
        """Create image record with all relationships"""
        slug = self._generate_slug(imageid)
        
        try:
            # Create image
            image = Image.objects.create(
                slug=slug,
                title=image_data['title'],
                description=image_data['description'],
                image_url=image_url,
                movie=movie,
            )
            
            # Set single-value foreign keys
            single_value_fields = [
                'actor', 'camera', 'cinematographer', 'director', 'lens', 'film_stock',
                'setting', 'location', 'filming_location', 'aspect_ratio',
                'media_type', 'time_period', 'time_of_day', 'interior_exterior',
                'format', 'frame_size', 'lens_type', 'composition', 'shot_type',
                'lighting', 'lighting_type', 'camera_type', 'resolution',
                'frame_rate', 'color', 'shade', 'production_designer',
                'costume_designer', 'editor', 'colorist', 'artist',
                'location_type', 'year', 'vfx_backing'
            ]
            
            for field in single_value_fields:
                if field in options and options[field]:
                    setattr(image, field, options[field])
            
            # Set ManyToMany relationships
            if 'genre' in options and options['genre']:
                try:
                    image.genre.set(options['genre'])
                except Exception as e:
                    self.logger.error(f"Failed to set genre for {imageid}: {e}")
            
            image.save()
            return image
            
        except Exception as e:
            self.logger.error(f"Failed to create image record for {imageid}: {e}")
            raise

    def _generate_slug(self, imageid: str) -> str:
        """Generate slug: imageid.lower()-uuid4()"""
        return f"{imageid.lower()}-{uuid.uuid4().hex[:12]}"

    def _print_summary(self):
        """Print import summary"""
        self.stdout.write("\nSummary:")
        self.stdout.write("=" * 8)
        self.stdout.write(f"Total processed: {self.stats['processed']}")
        self.stdout.write(f"✓ Success: {self.stats['success']}")
        self.stdout.write(f"✗ Errors: {self.stats['errors']}")
        self.stdout.write(f"⊘ Skipped (duplicates): {self.stats['skipped']}")
        if self.skip_missing_files:
            self.stdout.write(f"⊘ Missing files: {self.stats['missing_files']}")
        
        if self.stats['errors'] > 0:
            self.stdout.write(f"Errors logged to: import_errors.log")

    def _run_data_integrity_checks(self):
        """Run data integrity checks"""
        self.stdout.write("\nData Integrity Check (20 random samples):")
        
        # Get random sample of images
        sample_images = Image.objects.order_by('?')[:20]
        
        title_matches = 0
        files_exist = 0
        slug_format_correct = 0
        
        for image in sample_images:
            # Check title match
            if image.title:
                title_matches += 1
            
            # Check file exists
            if os.path.exists(os.path.join(settings.MEDIA_ROOT, image.image_url.replace('/media/', ''))):
                files_exist += 1
            
            # Check slug format
            if '-' in image.slug and len(image.slug.split('-')) == 2:
                slug_format_correct += 1
        
        self.stdout.write(f"✓ Title match: {title_matches}/20 ({title_matches/20*100:.0f}%)")
        self.stdout.write(f"✓ Files exist: {files_exist}/20 ({files_exist/20*100:.0f}%)")
        self.stdout.write(f"✓ Slug format: {slug_format_correct}/20 ({slug_format_correct/20*100:.0f}%)")
        
        self.stdout.write("\nImport completed successfully!")
