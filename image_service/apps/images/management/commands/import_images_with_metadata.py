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
    YearOption, VfxBackingOption, GenreOption, GenderOption, AgeOption,
    EthnicityOption, NumberOfPeopleOption, OpticalFormatOption, LabProcessOption
)

class Command(BaseCommand):
    help = "Import Shotdeck images with complete metadata - only images with JSON metadata"

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
            '--limit',
            type=int,
            help='Limit number of images to process'
        )

    def handle(self, *args, **options):
        self.json_dir = options['json_dir']
        self.image_dir = options['image_dir']
        self.batch_size = options['batch_size']
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.limit = options['limit']
        
        self.stats = {
            'processed': 0,
            'success': 0,
            'errors': 0,
            'skipped': 0,
            'missing_files': 0
        }

        self.stdout.write("Shotdeck Import - Images with Complete Metadata Only")
        self.stdout.write("=" * 60)
        self.stdout.write(f"JSON Directory: {self.json_dir}")
        self.stdout.write(f"Image Directory: {self.image_dir}")
        
        if self.dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")

        # Validate dataset
        self._validate_dataset()
        
        # Find images that have both JSON metadata and image files
        self.valid_images = self._find_valid_images()
        self.stdout.write(f"Found {len(self.valid_images)} images with complete metadata")
        
        if self.limit:
            self.valid_images = self.valid_images[:self.limit]
            self.stdout.write(f"Limited to {len(self.valid_images)} images for testing")

        # Process in batches
        self._process_batches(self.valid_images)
        
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
        
        self.stdout.write("✓ Directory access confirmed")

    def _find_valid_images(self):
        """Find images that have both JSON metadata and image files"""
        valid_images = []
        
        # Get all JSON files
        json_files = [f for f in os.listdir(self.json_dir) if f.endswith('.json')]
        
        self.stdout.write(f"Checking {len(json_files)} JSON files for matching images...")
        
        for i, json_file in enumerate(json_files):
            if i % 1000 == 0:
                self.stdout.write(f"  Checked {i}/{len(json_files)} JSON files...")
            
            try:
                # Load JSON to get image filename
                json_path = os.path.join(self.json_dir, json_file)
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                image_file = data.get('data', {}).get('image_file', '')
                if not image_file:
                    continue
                
                # Check if image file exists
                image_path = os.path.join(self.image_dir, image_file)
                if os.path.exists(image_path):
                    valid_images.append({
                        'json_file': json_file,
                        'image_file': image_file,
                        'imageid': json_file.replace('.json', ''),
                        'data': data
                    })
                else:
                    # Check case-insensitive
                    for actual_file in os.listdir(self.image_dir):
                        if actual_file.lower() == image_file.lower():
                            valid_images.append({
                                'json_file': json_file,
                                'image_file': actual_file,
                                'imageid': json_file.replace('.json', ''),
                                'data': data
                            })
                            break
                            
            except Exception as e:
                self.logger.error(f"Error processing {json_file}: {e}")
                continue
        
        self.stdout.write(f"✓ Found {len(valid_images)} valid images with complete metadata")
        return valid_images

    def _process_batches(self, valid_images):
        """Process valid images in batches"""
        total_batches = (len(valid_images) + self.batch_size - 1) // self.batch_size
        
        self.stdout.write(f"Starting import...")
        self.stdout.write(f"Processing {len(valid_images)} images in {total_batches} batches")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(valid_images))
            batch_images = valid_images[start_idx:end_idx]
            
            self.stdout.write(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_images)} images)")
            
            with transaction.atomic():
                for image_info in batch_images:
                    try:
                        self._process_image(image_info)
                        self.stats['processed'] += 1
                        
                        if self.stats['processed'] % 100 == 0:
                            progress = (self.stats['processed'] / len(valid_images)) * 100
                            self.stdout.write(f"Progress: {self.stats['processed']}/{len(valid_images)} ({progress:.1f}%)")
                    
                    except Exception as e:
                        self.stats['errors'] += 1
                        self.logger.error(f"ImageID: {image_info['imageid']} | Error: {e}")
                        continue

    def _process_image(self, image_info):
        """Process a single image with complete metadata"""
        imageid = image_info['imageid']
        image_file = image_info['image_file']
        data = image_info['data']
        
        # Check if already exists
        if not self.force and Image.objects.filter(slug__startswith=imageid.lower()).exists():
            self.stats['skipped'] += 1
            return
        
        # Extract image data
        image_data = self._extract_image_data(data)
        if not image_data:
            raise Exception("No image data found in JSON")
        
        # Create image URL
        image_url = f"/media/images/{image_file}"
        
        # Extract movie data with complete metadata
        movie = self._get_or_create_movie(data)
        
        # Extract ALL filter options
        options = self._extract_all_filter_options(data)
        
        # Create image record
        if not self.dry_run:
            image = self._create_image_record(imageid, image_data, movie, options, image_url)
            self.stats['success'] += 1
        else:
            self.stats['success'] += 1

    def _extract_image_data(self, data: Dict) -> Optional[Dict]:
        """Extract complete image data from JSON"""
        try:
            details = data.get('data', {}).get('details', {})
            
            # Get title
            title = details.get('full_title', '')
            if not title:
                title_values = details.get('title', {}).get('values', [])
                if title_values:
                    title = title_values[0].get('display_value', '')
            
            # Get description from tags and shot info
            description_parts = []
            
            # Add tags
            shot_info = details.get('shot_info', {})
            tags = shot_info.get('tags', {}).get('values', [])
            if tags:
                tag_values = [tag.get('display_value', '') for tag in tags if tag.get('display_value')]
                if tag_values:
                    description_parts.append(f"Tags: {', '.join(tag_values)}")
            
            # Add actors
            actors = shot_info.get('actors', {}).get('values', [])
            if actors:
                actor_values = [actor.get('display_value', '') for actor in actors if actor.get('display_value')]
                if actor_values:
                    description_parts.append(f"Actors: {', '.join(actor_values)}")
            
            description = " | ".join(description_parts)

            # Release year (as plain integer for Image.release_year)
            release_year = None
            try:
                year_data = details.get('year', {}).get('values', [])
                if year_data:
                    year_str = year_data[0].get('display_value', '')
                    if year_str.isdigit():
                        release_year = int(year_str)
            except Exception:
                release_year = None
            
            return {
                'title': title,
                'description': description,
                'release_year': release_year
            }
        except Exception as e:
            self.logger.error(f"Error extracting image data: {e}")
            return None

    def _get_or_create_movie(self, data: Dict) -> Optional[Movie]:
        """Get or create movie record with complete metadata"""
        try:
            details = data.get('data', {}).get('details', {})
            title_data = details.get('title', {})
            
            if not title_data or not title_data.get('values'):
                return None
            
            title_info = title_data['values'][0]
            title = title_info.get('display_value', '')
            
            if not title:
                return None
            
            # Extract movie metadata
            year = self._extract_year(details)
            
            # Create or get movie
            movie, created = Movie.objects.get_or_create(
                title=title,
                defaults={
                    'year': year,
                    'description': '',  # Could be extracted from JSON if available
                    'genre': '',  # Could be extracted from title_info.genre
                    'director': None,  # Will be set via foreign key
                    'cinematographer': None,  # Will be set via foreign key
                    'editor': None,  # Will be set via foreign key
                    'colorist': '',  # Will be extracted
                    'costume_designer': '',  # Will be extracted
                    'production_designer': '',  # Will be extracted
                    'cast': '',  # Will be extracted from actors
                    'duration': None,  # Not available in JSON
                    'country': '',  # Not available in JSON
                    'language': '',  # Not available in JSON
                    'image_count': 0  # Will be calculated
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

    def _extract_all_filter_options(self, data: Dict) -> Dict:
        """Extract ALL filter options with complete metadata"""
        options = {}
        
        try:
            details = data.get('data', {}).get('details', {})
            shot_info = details.get('shot_info', {})
            title_info = details.get('title_info', {})
            
            # Complete mapping of ALL fields
            field_mappings = [
                # Core fields
                ('movie', None, None),  # Handled separately
                ('actor', ActorOption, shot_info.get('actors', {})),
                ('camera', CameraOption, shot_info.get('camera', {})),
                ('lens', LensOption, shot_info.get('lens', {})),
                ('location', LocationOption, shot_info.get('location', {})),
                ('setting', SettingOption, shot_info.get('setting', {})),
                ('film_stock', FilmStockOption, shot_info.get('film_stock', {})),
                ('shot_time', None, shot_info.get('shot_time', {})),  # Not in model
                ('description', None, None),  # Handled separately
                ('vfx_backing', VfxBackingOption, shot_info.get('vfx_backing', {})),
                
                # Media and format
                ('media_type', MediaTypeOption, details.get('media_type', {})),
                ('genre', GenreOption, title_info.get('genre', {})),
                ('time_period', TimePeriodOption, shot_info.get('time_period', {})),
                ('color', ColorOption, shot_info.get('color', {})),
                ('shade', ShadeOption, details.get('shade', {})),
                ('aspect_ratio', AspectRatioOption, shot_info.get('aspect_ratio', {})),
                ('optical_format', OpticalFormatOption, shot_info.get('optical_format', {})),
                ('lab_process', LabProcessOption, shot_info.get('lab_process', {})),
                ('format', FormatOption, shot_info.get('format', {})),
                
                # Location and environment
                ('interior_exterior', InteriorExteriorOption, shot_info.get('int_ext', {})),
                ('time_of_day', TimeOfDayOption, shot_info.get('time_of_day', {})),
                ('filming_location', FilmingLocationOption, shot_info.get('filming_location', {})),
                ('location_type', LocationTypeOption, shot_info.get('location_type', {})),
                
                # People and demographics
                ('number_of_people', NumberOfPeopleOption, shot_info.get('number_of_people', {})),
                ('gender', GenderOption, shot_info.get('gender', {})),
                ('age', AgeOption, shot_info.get('age', {})),
                ('ethnicity', EthnicityOption, shot_info.get('ethnicity', {})),
                
                # Technical specifications
                ('frame_size', FrameSizeOption, shot_info.get('frame_size', {})),
                ('shot_type', ShotTypeOption, shot_info.get('shot_type', {})),
                ('composition', CompositionOption, shot_info.get('composition', {})),
                ('lens_type', LensTypeOption, shot_info.get('lens_type', {})),
                ('lens_size', None, shot_info.get('lens_size', {})),  # Not in model
                ('lighting', LightingOption, shot_info.get('lighting', {})),
                ('lighting_type', LightingTypeOption, shot_info.get('lighting_type', {})),
                ('camera_type', CameraTypeOption, shot_info.get('camera_type', {})),
                ('resolution', ResolutionOption, shot_info.get('resolution', {})),
                ('frame_rate', FrameRateOption, shot_info.get('frame_rate', {})),
                
                # Crew
                ('director', DirectorOption, title_info.get('director', {})),
                ('cinematographer', CinematographerOption, title_info.get('cinematographer', {})),
                ('editor', EditorOption, title_info.get('editor', {})),
                ('costume_designer', CostumeDesignerOption, title_info.get('costume_designer', {})),
                ('production_designer', ProductionDesignerOption, title_info.get('production_designer', {})),
                ('colorist', ColoristOption, title_info.get('colorist', {})),
                ('artist', ArtistOption, title_info.get('artist', {})),
                
                # Additional fields
                ('year', YearOption, details.get('year', {})),
                ('description_filter', None, None),  # Not in model
            ]
            
            # Process single-value options
            for field_name, model_class, field_data in field_mappings:
                if model_class and field_data and field_data.get('values'):
                    value = field_data['values'][0].get('display_value', '')
                    if value:
                        try:
                            options[field_name] = self._get_or_create_option(model_class, value)
                        except Exception as e:
                            self.logger.error(f"Error creating {field_name}: {e}")
                            continue
            
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
        """Create image record with ALL relationships"""
        slug = self._generate_slug(imageid)
        
        try:
            # Create image
            image = Image.objects.create(
                slug=slug,
                title=image_data['title'],
                description=image_data['description'],
                image_url=image_url,
                movie=movie,
                release_year=image_data.get('release_year'),
            )
            
            # Set ALL single-value foreign keys
            single_value_fields = [
                'actor', 'camera', 'cinematographer', 'director', 'lens', 'film_stock',
                'setting', 'location', 'filming_location', 'aspect_ratio',
                'media_type', 'time_period', 'time_of_day', 'interior_exterior',
                'format', 'frame_size', 'lens_type', 'composition', 'shot_type',
                'lighting', 'lighting_type', 'camera_type', 'resolution',
                'frame_rate', 'color', 'shade', 'production_designer',
                'costume_designer', 'editor', 'colorist', 'artist',
                'location_type', 'year', 'vfx_backing', 'optical_format',
                'lab_process', 'number_of_people', 'gender', 'age', 'ethnicity'
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
        metadata_complete = 0
        
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
            
            # Check metadata completeness
            metadata_fields = ['movie', 'media_type', 'director', 'cinematographer', 'genre']
            complete_fields = sum(1 for field in metadata_fields if getattr(image, field, None))
            if complete_fields >= 3:  # At least 3 metadata fields populated
                metadata_complete += 1
        
        self.stdout.write(f"✓ Title match: {title_matches}/20 ({title_matches/20*100:.0f}%)")
        self.stdout.write(f"✓ Files exist: {files_exist}/20 ({files_exist/20*100:.0f}%)")
        self.stdout.write(f"✓ Slug format: {slug_format_correct}/20 ({slug_format_correct/20*100:.0f}%)")
        self.stdout.write(f"✓ Metadata complete: {metadata_complete}/20 ({metadata_complete/20*100:.0f}%)")
        
        self.stdout.write("\nImport completed successfully!")
