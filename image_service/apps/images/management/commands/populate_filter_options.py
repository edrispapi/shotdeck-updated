#!/usr/bin/env python
"""
Management command to populate all filter option tables with comprehensive data
that matches the Swagger API documentation.
"""

from django.core.management.base import BaseCommand
from apps.images.models import (
    GenreOption, ColorOption, MediaTypeOption, AspectRatioOption,
    OpticalFormatOption, FormatOption, TimePeriodOption,
    InteriorExteriorOption, TimeOfDayOption, LightingOption,
    ShotTypeOption, CompositionOption, LensTypeOption, CameraTypeOption,
    GenderOption, AgeOption, EthnicityOption, FrameSizeOption,
    NumberOfPeopleOption, ActorOption, CameraOption, LensOption,
    LocationOption, SettingOption
)


class Command(BaseCommand):
    help = 'Populate all filter option tables with comprehensive data matching Swagger docs'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting comprehensive filter options population...')
        )

        # Data matching Swagger documentation exactly
        filter_data = {
            'genre': [
                "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
                "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
                "Romance", "Science Fiction", "Thriller", "War", "Western"
            ],
            'color': [
                "Warm", "Cool", "Mixed", "Saturated", "Desaturated", "Red", "Orange",
                "Yellow", "Green", "Cyan", "Blue", "Purple", "Magenta", "Pink", "White",
                "Sepia", "Black and White"
            ],
            'media_type': ["Movie", "TV", "Trailer", "Music Video", "Commercial"],
            'aspect_ratio': [
                "1 - square", "1.20", "1.33", "1.37", "1.43", "1.66", "1.78",
                "1.85", "1.90", "2.00", "2.20", "2.35", "2.39", "2.55", "2.67",
                "2.76+", "3.55"
            ],
            'optical_format': [
                "Anamorphic", "Spherical", "Super 35", "3 perf", "2 perf",
                "Open Gate", "3D"
            ],
            'format': [
                "Film - 35mm", "Film - 16mm", "Film - Super 8mm", "Film - 65mm / 70mm",
                "Film - IMAX", "Tape", "Digital", "Digital - Large Format", "Animation"
            ],
            'time_period': [
                "Future", "2020s", "2010s", "2000s", "1990s", "1980s", "1970s",
                "1960s", "1950s", "1940s", "1930s", "1920s", "1910s", "1900s",
                "1800s", "1700s", "Renaissance: 1400-1700", "Medieval: 500-1400",
                "Ancient: 2000BC-500AD", "Stone Age: pre-2000BC"
            ],
            'interior_exterior': ["Interior", "Exterior"],
            'time_of_day': ["Dawn", "Day", "Dusk", "Night", "Sunrise", "Sunset"],
            'lighting': [
                "Backlight", "Edge light", "Hard light", "High contrast", "Low contrast",
                "Side light", "Silhouette", "Soft light", "Top light", "Underlight"
            ],
            'shot_type': [
                "Aerial", "Overhead", "High angle", "Low angle", "Dutch angle",
                "Establishing shot", "Over the shoulder", "Clean single", "2 shot",
                "3 shot", "Group shot", "Insert"
            ],
            'composition': [
                "Balanced", "Center", "Left heavy", "Right heavy", "Short side", "Symmetrical"
            ],
            'lens_type': [
                "Ultra Wide / Fisheye", "Wide", "Medium", "Long Lens", "Telephoto"
            ],
            'camera_type': [
                "Digital Cinema", "Film Camera", "Video Camera", "DSLR", "Mirrorless", "Other"
            ],
            'gender': ["Male", "Female", "Other"],
            'age': [
                "Baby", "Toddler", "Child", "Teenager", "Young Adult", "Mid-adult",
                "Middle age", "Senior"
            ],
            'ethnicity': [
                "Black", "White", "Latinx", "Middle Eastern", "South-East Asian",
                "East Asian", "South Asian", "Indigenous Peoples", "Mixed-race"
            ],
            'frame_size': [
                "Extreme Wide", "Wide", "Medium Wide", "Medium", "Medium Close Up",
                "Close Up", "Extreme Close Up"
            ],
            'number_of_people': ["None", "1", "2", "3", "4", "5", "6+"],
            'actor': [],  # This is populated dynamically from actual data
            'camera': [
                "Arri Alexa", "Red Dragon", "Sony F55", "Panavision", "Canon C300",
                "Blackmagic", "Other"
            ],
            'lens': [
                "Canon", "Zeiss", "Angenieux", "Panavision", "Arri", "Cooke",
                "Leica", "Other"
            ],
            'location': [
                "Urban", "Rural", "Indoor", "Outdoor", "Studio", "Location", "Other"
            ],  # Using Swagger values instead of current API values
            'setting': [
                "House", "Office", "Street", "Nature", "Vehicle", "Public Space", "Custom"
            ]  # Using Swagger values to align
        }

        # Model mapping
        model_mapping = {
            'genre': GenreOption,
            'color': ColorOption,
            'media_type': MediaTypeOption,
            'aspect_ratio': AspectRatioOption,
            'optical_format': OpticalFormatOption,
            'format': FormatOption,
            'time_period': TimePeriodOption,
            'interior_exterior': InteriorExteriorOption,
            'time_of_day': TimeOfDayOption,
            'lighting': LightingOption,
            'shot_type': ShotTypeOption,
            'composition': CompositionOption,
            'lens_type': LensTypeOption,
            'camera_type': CameraTypeOption,
            'gender': GenderOption,
            'age': AgeOption,
            'ethnicity': EthnicityOption,
            'frame_size': FrameSizeOption,
            'number_of_people': NumberOfPeopleOption,
            'actor': ActorOption,
            'camera': CameraOption,
            'lens': LensOption,
            'location': LocationOption,
            'setting': SettingOption
        }

        total_created = 0

        for filter_type, values in filter_data.items():
            if filter_type in model_mapping:
                model = model_mapping[filter_type]
                created_count = 0

                for i, value in enumerate(values):
                    obj, created = model.objects.get_or_create(
                        value=value,
                        defaults={'display_order': i + 1}
                    )
                    if created:
                        created_count += 1
                        total_created += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {filter_type}: {created_count} new options created "
                        f"({len(values)} total available)"
                    )
                )

        # Special handling for year data (not in Option models)
        # Years are handled separately in the cache system
        year_options = ["2020s", "2010s", "2000s", "1990s", "1980s", "1970s", "Pre-1970"]
        self.stdout.write(
            self.style.WARNING(
                f"⚠️  Year options need to be handled separately: {year_options}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 Filter options population complete! {total_created} new options created."
            )
        )

        # Clear cache to ensure new data is available
        from django.core.cache import cache
        cache.clear()
        self.stdout.write(self.style.SUCCESS("🗑️  Cache cleared to reflect new data"))
