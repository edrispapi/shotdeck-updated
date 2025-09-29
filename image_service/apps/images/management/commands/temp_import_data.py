import os
import json
import glob
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.images.models import (
    Movie, Image, GenreOption, ColorOption, AspectRatioOption,
    OpticalFormatOption, FormatOption, InteriorExteriorOption,
    TimeOfDayOption, NumberOfPeopleOption, GenderOption, AgeOption,
    EthnicityOption, FrameSizeOption, ShotTypeOption, CompositionOption,
    LensSizeOption, LensTypeOption, LightingOption, LightingTypeOption,
    TimePeriodOption, LabProcessOption, MediaTypeOption, LensOption,
    FilmStockOption, ShotTimeOption, VfxBackingOption, LocationOption, SettingOption
)


class Command(BaseCommand):
    help = 'Bulk import all JSON files from a directory'

    def add_arguments(self, parser):
        parser.add_argument(
            'directory',
            type=str,
            help='Directory containing JSON files to import'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of files to process in each batch'
        )

    def get_or_create_option(self, model_class, value):
        """Get or create an option, handling None values"""
        if not value:
            return None
        try:
            return model_class.objects.get(value=value)
        except model_class.DoesNotExist:
            try:
                return model_class.objects.create(value=value)
            except:
                return None

    def process_json_file(self, file_path):
        """Process a single JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(f'Error reading {file_path}: {e}')
            return False

        try:
            # Extract data from JSON structure
            image_data = data.get('data', {})
            details = image_data.get('details', {})
            shot_info = details.get('shot_info', {})

            # Extract movie information
            title_info = details.get('title', {})
            movie_title = title_info.get('values', [{}])[0].get('display_value') if title_info.get('values') else None
            movie_year = details.get('year', {}).get('values', [{}])[0].get('display_value')
            
            movie = None
            if movie_title:
                movie_slug = f"{movie_title.lower().replace(' ', '-')}-{movie_year}" if movie_year else movie_title.lower().replace(' ', '-')
                movie, created = Movie.objects.get_or_create(
                    slug=movie_slug[:50],  # Limit slug length
                    defaults={
                        'title': movie_title,
                        'year': int(movie_year) if movie_year and movie_year.isdigit() else None,
                        'description': details.get('title_info', {}).get('description', movie_title),
                    }
                )

            # Extract image information
            title = details.get('full_title', details.get('title', {}).get('values', [{}])[0].get('display_value', ''))
            slug = image_data.get('imageid', '')
            description = details.get('title_info', {}).get('description', title)
            image_file = image_data.get('image_file', f'{slug}.jpg')
            release_year = int(movie_year) if movie_year and movie_year.isdigit() else None

            # Create image
            image, created = Image.objects.get_or_create(
                slug=slug if slug else f'{title.lower().replace(" ", "-")[:40]}-{hash(title) % 10000}',
                defaults={
                    'title': title[:200],  # Limit title length
                    'description': description[:500] if description else '',
                    'movie': movie,
                    'image_url': f'/media/{image_file}',
                    'release_year': release_year,
                    # Filter fields
                    'media_type': self.get_or_create_option(MediaTypeOption, 
                        details.get('media_type', {}).get('values', [{}])[0].get('display_value')),
                    'color': self.get_or_create_option(ColorOption, 
                        shot_info.get('color', {}).get('values', [{}])[0].get('display_value')),
                    'aspect_ratio': self.get_or_create_option(AspectRatioOption, 
                        shot_info.get('aspect_ratio', {}).get('values', [{}])[0].get('display_value')),
                    'optical_format': self.get_or_create_option(OpticalFormatOption, 
                        shot_info.get('optical_format', {}).get('values', [{}])[0].get('display_value')),
                    'format': self.get_or_create_option(FormatOption, 
                        shot_info.get('format', {}).get('values', [{}])[0].get('display_value')),
                    'interior_exterior': self.get_or_create_option(InteriorExteriorOption, 
                        shot_info.get('int_ext', {}).get('values', [{}])[0].get('display_value')),
                    'time_of_day': self.get_or_create_option(TimeOfDayOption, 
                        shot_info.get('time_of_day', {}).get('values', [{}])[0].get('display_value')),
                    'frame_size': self.get_or_create_option(FrameSizeOption, 
                        shot_info.get('frame_size', {}).get('values', [{}])[0].get('display_value')),
                    'shot_type': self.get_or_create_option(ShotTypeOption, 
                        shot_info.get('shot_type', {}).get('values', [{}])[0].get('display_value')),
                    'composition': self.get_or_create_option(CompositionOption, 
                        shot_info.get('composition', {}).get('values', [{}])[0].get('display_value')),
                    'lighting': self.get_or_create_option(LightingOption, 
                        shot_info.get('lighting', {}).get('values', [{}])[0].get('display_value')),
                    'lighting_type': self.get_or_create_option(LightingTypeOption, 
                        shot_info.get('lighting_type', {}).get('values', [{}])[0].get('display_value')),
                    'time_period': self.get_or_create_option(TimePeriodOption, 
                        shot_info.get('time_period', {}).get('values', [{}])[0].get('display_value')),
                    'lab_process': self.get_or_create_option(LabProcessOption, 
                        image_data.get('lab_process')),
                    # New filter fields
                    'lens': self.get_or_create_option(LensOption,
                        shot_info.get('lens', {}).get('values', [{}])[0].get('display_value')),
                    'film_stock': self.get_or_create_option(FilmStockOption,
                        shot_info.get('film_stock', {}).get('values', [{}])[0].get('display_value')),
                    'shot_time': self.get_or_create_option(ShotTimeOption,
                        shot_info.get('shot_time', {}).get('values', [{}])[0].get('display_value')),
                    'vfx_backing': self.get_or_create_option(VfxBackingOption,
                        shot_info.get('vfx_backing', {}).get('values', [{}])[0].get('display_value')),
                    # Additional location and setting fields (taking first value if multiple exist)
                    'location': self.get_or_create_option(LocationOption,
                        shot_info.get('location', {}).get('values', [{}])[0].get('display_value')),
                    'setting': self.get_or_create_option(SettingOption,
                        shot_info.get('setting', {}).get('values', [{}])[0].get('display_value')),
                }
            )

            # Add genres (many-to-many)
            if details.get('title_info', {}).get('genre', {}).get('values'):
                if not created:
                    image.genre.clear()
                for genre_value in details['title_info']['genre']['values']:
                    genre_option = self.get_or_create_option(GenreOption, genre_value.get('display_value'))
                    if genre_option:
                        image.genre.add(genre_option)

            return True

        except Exception as e:
            self.stdout.write(f'Error processing {file_path}: {e}')
            return False

    def handle(self, *args, **options):
        directory = options['directory']
        batch_size = options['batch_size']

        # If no directory specified, use the mounted host data
        if directory == '/host_data' or not directory:
            directory = '/host_data'

        if not os.path.exists(directory):
            self.stdout.write(self.style.ERROR(f'Directory {directory} does not exist'))
            self.stdout.write('Make sure the host directory is mounted at /host_data in the container')
            return

        # Get all JSON files
        json_files = glob.glob(os.path.join(directory, '*.json'))
        total_files = len(json_files)

        self.stdout.write(f'Found {total_files} JSON files to process')
        self.stdout.write(f'Processing in batches of {batch_size}')

        processed = 0
        successful = 0
        failed = 0

        for i in range(0, total_files, batch_size):
            batch_files = json_files[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_files + batch_size - 1) // batch_size

            self.stdout.write(f'Processing batch {batch_num}/{total_batches} ({len(batch_files)} files)')

            batch_successful = 0
            batch_failed = 0

            for file_path in batch_files:
                if self.process_json_file(file_path):
                    batch_successful += 1
                else:
                    batch_failed += 1

            processed += len(batch_files)
            successful += batch_successful
            failed += batch_failed

            self.stdout.write(f'Batch {batch_num} complete: {batch_successful} successful, {batch_failed} failed')
            self.stdout.write(f'Progress: {processed}/{total_files} files ({successful} successful, {failed} failed)')

        self.stdout.write(self.style.SUCCESS(
            f'Bulk import complete! Processed {total_files} files. '
            f'Successful: {successful}, Failed: {failed}'
        ))

import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.text import slugify
from apps.images.models import Movie, Image, Tag, MediaTypeOption, GenreOption, ColorOption, AspectRatioOption, OpticalFormatOption, FormatOption, InteriorExteriorOption, TimeOfDayOption, NumberOfPeopleOption, GenderOption, AgeOption, EthnicityOption, FrameSizeOption, ShotTypeOption, CompositionOption, LensSizeOption, LensTypeOption, LightingOption, LightingTypeOption, TimePeriodOption, LabProcessOption, MovieOption, ActorOption, CameraOption, LensOption, LocationOption, SettingOption, FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption


class Command(BaseCommand):
    help = 'Import data from JSON file'

    def get_or_create_option(self, model_class, value):
        """Get or create an option by value"""
        if not value:
            return None
        try:
            # Try exact match first
            return model_class.objects.get(value=value)
        except model_class.DoesNotExist:
            try:
                # Try case-insensitive match
                return model_class.objects.filter(value__iexact=value).first()
            except:
                pass
        except model_class.MultipleObjectsReturned:
            # If multiple objects exist, return the first one
            return model_class.objects.filter(value__iexact=value).first()

        # Try to create it if it doesn't exist
        try:
            return model_class.objects.create(value=value)
        except:
            return None


    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to the JSON file containing the data to import'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before importing'
        )

    def handle(self, *args, **options):
        json_file_path = options['json_file']

        if not os.path.exists(json_file_path):
            raise CommandError(f'File "{json_file_path}" does not exist')

        self.stdout.write(f'Loading data from {json_file_path}...')

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON file: {e}')
        except Exception as e:
            raise CommandError(f'Error reading file: {e}')

        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Image.objects.all().delete()
            Movie.objects.all().delete()
            Tag.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared'))

        # Import Movies
        if 'movies' in data:
            self.stdout.write(f'Importing {len(data["movies"])} movies...')
            for movie_data in data['movies']:
                movie, created = Movie.objects.get_or_create(
                    slug=movie_data.get('slug'),
                    defaults={
                        'title': movie_data.get('title', ''),
                        'year': movie_data.get('year'),
                        'director': movie_data.get('director', ''),
                        'genre': movie_data.get('genre', ''),
                        'description': movie_data.get('description', ''),
                        'cast': movie_data.get('cast', ''),
                        'cinematographer': movie_data.get('cinematographer', ''),
                        'colorist': movie_data.get('colorist', ''),
                    }
                )
                if created:
                    self.stdout.write(f'Created movie: {movie.title}')
                else:
                    self.stdout.write(f'Updated movie: {movie.title}')

        # Import Tags
        if 'tags' in data:
            self.stdout.write(f'Importing {len(data["tags"])} tags...')
            for tag_data in data['tags']:
                tag, created = Tag.objects.get_or_create(
                    slug=tag_data.get('slug'),
                    defaults={
                        'name': tag_data.get('name', ''),
                    }
                )
                if created:
                    self.stdout.write(f'Created tag: {tag.name}')

        # Import single image from JSON file
        self.stdout.write('Importing image from JSON file...')

        # پیدا کردن movie مرتبط
        movie = None
        title_info = data.get('data', {}).get('details', {}).get('title', {})
        movie_title = title_info.get('values', [{}])[0].get('display_value') if title_info.get('values') else None
        movie_year = data.get('data', {}).get('release_year')

        if movie_title:
            # Create slug from title
            movie_slug = slugify(movie_title)
            if Movie.objects.filter(slug=movie_slug).exists():
                movie_slug = f"{movie_slug}-{movie_year}" if movie_year else movie_slug

            movie, created = Movie.objects.get_or_create(
                slug=movie_slug,
                defaults={
                    'title': movie_title,
                    'year': movie_year,
                    'description': f"{title_info.get('filter_name', 'Movie')}: {movie_title}",
                }
            )
            if created:
                self.stdout.write(f'Created movie: {movie.title}')

        # Set image_data to the data.data field
        image_data = data.get('data', {})

        # استخراج داده‌ها از ساختار صحیح JSON
        details = image_data.get('details', {})
        shot_info = details.get('shot_info', {})

        # استخراج فیلدهای اصلی تصویر
        title = details.get('full_title', details.get('title', {}).get('values', [{}])[0].get('display_value', ''))
        slug = image_data.get('imageid', '')
        description = details.get('title_info', {}).get('description', title)
        image_file = image_data.get('image_file', f'{slug}.jpg')
        release_year_str = details.get('year', {}).get('values', [{}])[0].get('display_value')
        release_year = int(release_year_str) if release_year_str and release_year_str.isdigit() else None

        # ایجاد یا بروزرسانی تصویر
        final_slug = slug if slug else f'{title.lower().replace(" ", "-")}-{uuid.uuid4().hex[:8]}'
        self.stdout.write(f'Creating image with slug: {final_slug}, title: {title}')

        image, created = Image.objects.get_or_create(
            slug=final_slug,
            defaults={
                'title': title,
                'description': description,
                'movie': movie,
                'image_url': f'/media/{image_file}',
                'release_year': release_year,
                # فیلترهای اصلی
                'media_type': self.get_or_create_option(MediaTypeOption, details.get('media_type', {}).get('values', [{}])[0].get('display_value')),
                'color': self.get_or_create_option(ColorOption, shot_info.get('color', {}).get('values', [{}])[0].get('display_value')),
                'aspect_ratio': self.get_or_create_option(AspectRatioOption, shot_info.get('aspect_ratio', {}).get('values', [{}])[0].get('display_value')),
                'optical_format': self.get_or_create_option(OpticalFormatOption, shot_info.get('optical_format', {}).get('values', [{}])[0].get('display_value')),
                'format': self.get_or_create_option(FormatOption, shot_info.get('format', {}).get('values', [{}])[0].get('display_value')),
                'interior_exterior': self.get_or_create_option(InteriorExteriorOption, shot_info.get('int_ext', {}).get('values', [{}])[0].get('display_value')),
                'time_of_day': self.get_or_create_option(TimeOfDayOption, shot_info.get('time_of_day', {}).get('values', [{}])[0].get('display_value')),
                'number_of_people': self.get_or_create_option(NumberOfPeopleOption, image_data.get('number_of_people')),
                'gender': self.get_or_create_option(GenderOption, image_data.get('gender')),
                'age': self.get_or_create_option(AgeOption, image_data.get('age')),
                'ethnicity': self.get_or_create_option(EthnicityOption, image_data.get('ethnicity')),
                'frame_size': self.get_or_create_option(FrameSizeOption, shot_info.get('frame_size', {}).get('values', [{}])[0].get('display_value')),
                'shot_type': self.get_or_create_option(ShotTypeOption, shot_info.get('shot_type', {}).get('values', [{}])[0].get('display_value')),
                'composition': self.get_or_create_option(CompositionOption, shot_info.get('composition', {}).get('values', [{}])[0].get('display_value')),
                'lens_size': self.get_or_create_option(LensSizeOption, shot_info.get('lens_size', {}).get('values', [{}])[0].get('display_value')),
                'lens_type': self.get_or_create_option(LensTypeOption, shot_info.get('lens_type', {}).get('values', [{}])[0].get('display_value')),
                'lighting': self.get_or_create_option(LightingOption, shot_info.get('lighting', {}).get('values', [{}])[0].get('display_value')),
                'lighting_type': self.get_or_create_option(LightingTypeOption, shot_info.get('lighting_type', {}).get('values', [{}])[0].get('display_value')),
                'time_period': self.get_or_create_option(TimePeriodOption, shot_info.get('time_period', {}).get('values', [{}])[0].get('display_value')),
                'lab_process': self.get_or_create_option(LabProcessOption, image_data.get('lab_process')),
                # فیلترهای جدید از تحلیل داده‌های JSON
                'actor': self.get_or_create_option(ActorOption, shot_info.get('actors', {}).get('values', [{}])[0].get('display_value')),
                'camera': self.get_or_create_option(CameraOption, shot_info.get('camera', {}).get('values', [{}])[0].get('display_value')),
                'lens': self.get_or_create_option(LensOption, shot_info.get('lens', {}).get('values', [{}])[0].get('display_value')),
                'location': self.get_or_create_option(LocationOption, shot_info.get('location', {}).get('values', [{}])[0].get('display_value')),
                'setting': self.get_or_create_option(SettingOption, shot_info.get('setting', {}).get('values', [{}])[0].get('display_value')),
                'film_stock': self.get_or_create_option(FilmStockOption, shot_info.get('film_stock', {}).get('values', [{}])[0].get('display_value')),
                        'shot_time': self.get_or_create_option(ShotTimeOption, shot_info.get('shot_time', {}).get('values', [{}])[0].get('display_value') if isinstance(shot_info.get('shot_time'), dict) else shot_info.get('shot_time')),
                        'description_filter': self.get_or_create_option(DescriptionOption, shot_info.get('description') if isinstance(shot_info.get('description'), str) else shot_info.get('description', {}).get('values', [{}])[0].get('display_value')),
                        'vfx_backing': self.get_or_create_option(VfxBackingOption, shot_info.get('vfx_backing', {}).get('values', [{}])[0].get('display_value') if isinstance(shot_info.get('vfx_backing'), dict) else shot_info.get('vfx_backing')),
            }
        )

        self.stdout.write(f'Image created: {created}, image object: {image}')

        # اضافه کردن تگ‌ها
        if image_data.get('tags'):
            for tag_slug in image_data['tags']:
                try:
                    tag = Tag.objects.get(slug=tag_slug)
                    image.tags.add(tag)
                except Tag.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Tag with slug "{tag_slug}" not found for image {image.slug}'
                        )
                    )

        # اضافه کردن ژانرها (many-to-many)
        self.stdout.write(f'About to add genres, image is: {image}')
        if details.get('title_info', {}).get('genre', {}).get('values'):
            self.stdout.write(f'Found genres to add: {len(details["title_info"]["genre"]["values"])}')
            # Clear existing genres if this is an update
            if not created:
                image.genre.clear()
            for genre_value in details['title_info']['genre']['values']:
                self.stdout.write(f'Adding genre: {genre_value.get("display_value")}')
                genre_option = self.get_or_create_option(GenreOption, genre_value.get('display_value'))
                self.stdout.write(f'Genre option created: {genre_option}')
                if genre_option:
                    image.genre.add(genre_option)
                    self.stdout.write(f'Genre added to image')

        if created:
            self.stdout.write(f'Created image: {image.title}')
        else:
            self.stdout.write(f'Updated image: {image.title}')

        self.stdout.write(self.style.SUCCESS('Data import completed successfully!'))

        # نمایش آمار نهایی
        self.stdout.write('\nFinal statistics:')
        self.stdout.write(f'Movies: {Movie.objects.count()}')
        self.stdout.write(f'Images: {Image.objects.count()}')
        self.stdout.write(f'Tags: {Tag.objects.count()}')