from django.core.management.base import BaseCommand
from django.db import transaction
from apps.images.models import (
    GenreOption, ColorOption, MediaTypeOption, AspectRatioOption,
    OpticalFormatOption, FormatOption, InteriorExteriorOption, TimeOfDayOption,
    NumberOfPeopleOption, GenderOption, AgeOption, EthnicityOption,
    FrameSizeOption, ShotTypeOption, CompositionOption, LensSizeOption,
    LensTypeOption, LightingOption, LightingTypeOption, CameraTypeOption,
    ResolutionOption, FrameRateOption, TimePeriodOption, LabProcessOption, MovieOption,
    ActorOption, CameraOption, LensOption, LocationOption, SettingOption,
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption
)
from apps.images.cache_utils import invalidate_all_filter_cache
import json


class Command(BaseCommand):
    help = 'Synchronize filter options with external data sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Source of filter data (json_file, api, manual)',
            default='json_file'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Path to JSON file containing filter data',
            default='filters_data.json'
        )
        parser.add_argument(
            '--filter-type',
            type=str,
            help='Specific filter type to sync (optional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all filter options before syncing',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting all filter options...')
            self.reset_all_filters()

        if options['filter_type']:
            self.sync_single_filter(options['filter_type'], options)
        else:
            self.sync_all_filters(options)

        # Invalidate cache after sync
        if not options['dry_run']:
            self.stdout.write('Invalidating filter caches...')
            invalidate_all_filter_cache()

        self.stdout.write(self.style.SUCCESS('Filter synchronization completed'))

    def reset_all_filters(self):
        """Reset all filter options"""
        filter_models = [
            GenreOption, ColorOption, MediaTypeOption, AspectRatioOption,
            OpticalFormatOption, FormatOption, InteriorExteriorOption, TimeOfDayOption,
            NumberOfPeopleOption, GenderOption, AgeOption, EthnicityOption,
            FrameSizeOption, ShotTypeOption, CompositionOption, LensSizeOption,
            LensTypeOption, LightingOption, LightingTypeOption, CameraTypeOption,
            ResolutionOption, FrameRateOption
        ]

        for model in filter_models:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f'  Deleted {count} options from {model.__name__}')

    def sync_all_filters(self, options):
        """Sync all filter types"""
        filter_mappings = self.get_filter_mappings()

        for filter_type, model_class in filter_mappings.items():
            self.stdout.write(f'\nSyncing {filter_type}...')
            # Debug: print first few items
            data = self.get_filter_data(filter_type, options)
            if data:
                self.stdout.write(f'  Sample data: {data[:2]}')
            if data:
                self.sync_filter_type(filter_type, model_class, options, data)

    def sync_single_filter(self, filter_type, options):
        """Sync a specific filter type"""
        filter_mappings = self.get_filter_mappings()

        if filter_type not in filter_mappings:
            self.stderr.write(f'Unknown filter type: {filter_type}')
            return

        model_class = filter_mappings[filter_type]
        self.stdout.write(f'Syncing {filter_type}...')
        self.sync_filter_type(filter_type, model_class, options)

    def get_filter_mappings(self):
        """Get mapping of filter types to model classes"""
        return {
            'movie': MovieOption,
            'actors': ActorOption,
            'camera': CameraOption,
            'lens': LensOption,
            'location': LocationOption,
            'setting': SettingOption,
            'film_stock': FilmStockOption,
            'shot_time': ShotTimeOption,
            'description': DescriptionOption,
            'vfx_backing': VfxBackingOption,
            'genre': GenreOption,
            'color': ColorOption,
            'media_type': MediaTypeOption,
            'aspect_ratio': AspectRatioOption,
            'optical_format': OpticalFormatOption,
            'format': FormatOption,
            'int_ext': InteriorExteriorOption,
            'time_of_day': TimeOfDayOption,
            'numpeople': NumberOfPeopleOption,
            'gender': GenderOption,
            'subject_age': AgeOption,
            'subject_ethnicity': EthnicityOption,
            'frame_size': FrameSizeOption,
            'shot_type': ShotTypeOption,
            'composition': CompositionOption,
            'lens_type': LensSizeOption,
            'lighting': LightingOption,
            'lighting_type': LightingTypeOption,
            'time_period': TimePeriodOption,
            'lab_process': LabProcessOption,
        }

    def sync_filter_type(self, filter_type, model_class, options, data=None):
        """Sync a specific filter type"""
        # Get data from source if not provided
        if data is None:
            data = self.get_filter_data(filter_type, options)

        if not data:
            self.stdout.write(f'  No data found for {filter_type}')
            return

        existing_values = set(model_class.objects.values_list('value', flat=True))
        existing_options = {opt.value: opt for opt in model_class.objects.all()}
        created_count = 0
        updated_count = 0

        for item in data:
            # Handle different data formats
            if isinstance(item, dict):
                if 'value' in item and isinstance(item['value'], dict):
                    # Nested format: {'value': {'value': 'Action', 'display_order': 1, ...}, 'display_order': 0}
                    nested_value = item['value']
                    value = nested_value.get('value')
                    display_order = nested_value.get('display_order', item.get('display_order', 0))
                    metadata = nested_value.get('metadata', {})
                elif 'value' in item:
                    # Simple format: {'value': 'Action', 'display_order': 1, ...}
                    value = item['value']
                    display_order = item.get('display_order', 0)
                    metadata = item.get('metadata', {})
                else:
                    self.stderr.write(f'  Skipping invalid item (no value key): {item}')
                    continue
            elif isinstance(item, str):
                value = item
                display_order = 0
                metadata = {}
            else:
                self.stderr.write(f'  Skipping invalid item: {item}')
                continue

            # Debug: print value type
            # self.stdout.write(f'  Processing value: {value} (type: {type(value)})')

            if options['dry_run']:
                if value in existing_values:
                    self.stdout.write(f'  Would update: {value}')
                else:
                    self.stdout.write(f'  Would create: {value}')
                continue

            if value in existing_values:
                # Update existing option
                option = existing_options[value]
                if (option.display_order != display_order or
                    option.metadata != metadata):
                    option.display_order = display_order
                    option.metadata = metadata
                    option.save()
                    updated_count += 1
            else:
                # Create new option
                model_class.objects.create(
                    value=value,
                    display_order=display_order,
                    metadata=metadata
                )
                created_count += 1

        if not options['dry_run']:
            self.stdout.write(f'  Created: {created_count}, Updated: {updated_count}')

    def get_filter_data(self, filter_type, options):
        """Get filter data from specified source"""
        if options['source'] == 'json_file':
            return self.get_data_from_json_file(filter_type, options['file'])
        elif options['source'] == 'api':
            return self.get_data_from_api(filter_type)
        elif options['source'] == 'manual':
            return self.get_data_from_manual_input(filter_type)
        else:
            self.stderr.write(f'Unknown source: {options["source"]}')
            return []

    def get_data_from_json_file(self, filter_type, file_path):
        """Get filter data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Look for filter type in data
            if filter_type in data:
                filter_data = data[filter_type]
                # Convert to expected format
                if isinstance(filter_data, list):
                    return [
                        {'value': item, 'display_order': i}
                        for i, item in enumerate(filter_data)
                    ]
                elif isinstance(filter_data, dict):
                    return [
                        {'value': k, 'display_order': v.get('order', 0), 'metadata': v}
                        for k, v in filter_data.items()
                    ]

            return []
        except Exception as e:
            self.stderr.write(f'Error reading JSON file: {e}')
            return []

    def get_data_from_api(self, filter_type):
        """Get filter data from external API"""
        # Placeholder for API integration
        self.stdout.write(f'  API integration for {filter_type} not implemented yet')
        return []

    def get_data_from_manual_input(self, filter_type):
        """Get filter data from manual input"""
        self.stdout.write(f'  Manual input for {filter_type} not implemented yet')
        self.stdout.write('  Use --source=json_file for now')
        return []

    def get_default_filter_data(self):
        """Get default filter data for common cases"""
        return {
            'genre': [
                {'value': 'Action', 'display_order': 1},
                {'value': 'Drama', 'display_order': 2},
                {'value': 'Comedy', 'display_order': 3},
                {'value': 'Thriller', 'display_order': 4},
                {'value': 'Horror', 'display_order': 5},
            ],
            'color': [
                {'value': 'warm', 'display_order': 1},
                {'value': 'cool', 'display_order': 2},
                {'value': 'neutral', 'display_order': 3},
            ],
            'media_type': [
                {'value': 'movie', 'display_order': 1},
                {'value': 'tv', 'display_order': 2},
                {'value': 'commercial', 'display_order': 3},
            ],
            # Add more defaults as needed
        }
