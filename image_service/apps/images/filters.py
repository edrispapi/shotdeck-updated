# مسیر: image_service/apps/images/filters.py
import django_filters
from django.db import models
from .models import (
    Image, Tag,
    # All option models for filtering
    GenreOption, ColorOption, MediaTypeOption, AspectRatioOption,
    OpticalFormatOption, FormatOption, InteriorExteriorOption, TimeOfDayOption,
    NumberOfPeopleOption, GenderOption, AgeOption, EthnicityOption,
    FrameSizeOption, ShotTypeOption, CompositionOption, LensSizeOption,
    LensTypeOption, LightingOption, LightingTypeOption, CameraTypeOption,
    ResolutionOption, FrameRateOption, TimePeriodOption, LabProcessOption,
    ActorOption, CameraOption, LensOption, LocationOption, SettingOption,
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption
)

class ImageFilter(django_filters.FilterSet):
    # Existing filters
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__name',
        to_field_name='name',
        queryset=Tag.objects.all(),
        conjoined=True,
        label="Tags (by name, comma-separated)"
    )
    q = django_filters.CharFilter(method='search_text', label="Search in title and description")
    release_year__gte = django_filters.NumberFilter(field_name='release_year', lookup_expr='gte')
    release_year__lte = django_filters.NumberFilter(field_name='release_year', lookup_expr='lte')

    # New filters for option fields - now support both ID and name with dropdown options
    media_type = django_filters.CharFilter(method='filter_by_option', label="Media Type (ID or name)")
    genre = django_filters.CharFilter(method='filter_by_option', label="Genre (ID or name)")
    color = django_filters.CharFilter(method='filter_by_option', label="Color (ID or name)")
    aspect_ratio = django_filters.CharFilter(method='filter_by_option', label="Aspect Ratio")
    optical_format = django_filters.CharFilter(method='filter_by_option', label="Optical Format")
    format = django_filters.CharFilter(method='filter_by_option', label="Film Format")
    lab_process = django_filters.CharFilter(method='filter_by_option', label="Lab Process")
    time_period = django_filters.CharFilter(method='filter_by_option', label="Time Period")
    interior_exterior = django_filters.CharFilter(method='filter_by_option', label="Interior/Exterior")
    time_of_day = django_filters.CharFilter(method='filter_by_option', label="Time of Day")
    number_of_people = django_filters.CharFilter(method='filter_by_option', label="Number of People")
    gender = django_filters.CharFilter(method='filter_by_option', label="Gender")
    age = django_filters.CharFilter(method='filter_by_option', label="Age")
    ethnicity = django_filters.CharFilter(method='filter_by_option', label="Ethnicity")
    frame_size = django_filters.CharFilter(method='filter_by_option', label="Frame Size")
    shot_type = django_filters.CharFilter(method='filter_by_option', label="Shot Type")
    composition = django_filters.CharFilter(method='filter_by_option', label="Composition")
    lens_size = django_filters.CharFilter(method='filter_by_option', label="Lens Size")
    lens_type = django_filters.CharFilter(method='filter_by_option', label="Lens Type")
    lighting = django_filters.CharFilter(method='filter_by_option', label="Lighting")
    lighting_type = django_filters.CharFilter(method='filter_by_option', label="Lighting Type")
    camera_type = django_filters.CharFilter(method='filter_by_option', label="Camera Type")
    resolution = django_filters.CharFilter(method='filter_by_option', label="Resolution")
    frame_rate = django_filters.CharFilter(method='filter_by_option', label="Frame Rate")
    actor = django_filters.CharFilter(method='filter_by_option', label="Actor")
    camera = django_filters.CharFilter(method='filter_by_option', label="Camera")
    lens = django_filters.CharFilter(method='filter_by_option', label="Lens")
    location = django_filters.CharFilter(method='filter_by_option', label="Location")
    setting = django_filters.CharFilter(method='filter_by_option', label="Setting")
    film_stock = django_filters.CharFilter(method='filter_by_option', label="Film Stock")
    shot_time = django_filters.CharFilter(method='filter_by_option', label="Shot Time")
    description_filter = django_filters.CharFilter(method='filter_by_option', label="Description")
    vfx_backing = django_filters.CharFilter(method='filter_by_option', label="VFX Backing")

    # Special filters for empty option filters
    search = django_filters.CharFilter(
        method='search_text',
        label="Search",
        help_text="Search in title and description"
    )
    shade = django_filters.CharFilter(
        method='shade_filter',
        label="Color Picker",
        help_text="HEX_COLOR~COLOR_DISTANCE~PROPORTION"
    )

    class Meta:
        model = Image
        fields = [
            'release_year',  # Keep existing fields
            'search', 'shade',  # Special filters
            # All option fields are now handled by individual filters above
        ]

    # Custom filter methods for name/ID support
    def filter_by_option(self, queryset, name, value):
        """Generic filter method that handles both ID and name lookups"""
        if not value:
            return queryset

        # Map field names to their corresponding models
        field_map = {
            'media_type': MediaTypeOption,
            'genre': GenreOption,
            'color': ColorOption,
            'aspect_ratio': AspectRatioOption,
            'optical_format': OpticalFormatOption,
            'format': FormatOption,
            'lab_process': LabProcessOption,
            'time_period': TimePeriodOption,
            'interior_exterior': InteriorExteriorOption,
            'time_of_day': TimeOfDayOption,
            'number_of_people': NumberOfPeopleOption,
            'gender': GenderOption,
            'age': AgeOption,
            'ethnicity': EthnicityOption,
            'frame_size': FrameSizeOption,
            'shot_type': ShotTypeOption,
            'composition': CompositionOption,
            'lens_size': LensSizeOption,
            'lens_type': LensTypeOption,
            'lighting': LightingOption,
            'lighting_type': LightingTypeOption,
            'camera_type': CameraTypeOption,
            'resolution': ResolutionOption,
            'frame_rate': FrameRateOption,
            'actor': ActorOption,
            'camera': CameraOption,
            'lens': LensOption,
            'location': LocationOption,
            'setting': SettingOption,
            'film_stock': FilmStockOption,
            'shot_time': ShotTimeOption,
            'description_filter': DescriptionOption,
            'vfx_backing': VfxBackingOption,
        }

        model_class = field_map.get(name)
        if not model_class:
            return queryset

        return self._filter_by_option(queryset, model_class, name, value)


    def _filter_by_option(self, queryset, model_class, field_name, value):
        """Generic method to filter by option using either ID or name"""
        if not value:
            return queryset

        # Split by comma for multiple values
        values = [v.strip() for v in value.split(',')]

        option_ids = []
        for val in values:
            # Try to find by ID first
            try:
                option_ids.append(int(val))
                continue
            except ValueError:
                pass

            # Try to find by name/value (case-insensitive)
            try:
                options = model_class.objects.filter(value__iexact=val)
                for option in options:
                    option_ids.append(option.id)
            except:
                pass

        if option_ids:
            # Handle ManyToManyField differently
            if field_name == 'genre':
                # For ManyToManyField, use __in lookup
                return queryset.filter(**{f'{field_name}__id__in': option_ids})
            else:
                # For ForeignKey fields
                filter_kwargs = {f'{field_name}__id__in': option_ids}
                return queryset.filter(**filter_kwargs)

        # If no matching options found, return empty queryset
        return queryset.none()

    def search_text(self, queryset, name, value):
        return queryset.filter(
            models.Q(title__icontains=value) | models.Q(description__icontains=value)
        )

    def shade_filter(self, queryset, name, value):
        """
        Filter by color picker format: HEX_COLOR~COLOR_DISTANCE~PROPORTION
        """
        if not value:
            return queryset

        try:
            # Parse the format: HEX_COLOR~COLOR_DISTANCE~PROPORTION
            parts = value.split('~')
            if len(parts) == 3:
                hex_color, color_distance, proportion = parts
                color_distance = int(color_distance)
                proportion = float(proportion)

                # Filter images by color similarity
                matching_images = []
                for image in queryset:
                    if image.primary_color_hex:
                        if self.color_distance_hex(hex_color, image.primary_color_hex) <= color_distance:
                            matching_images.append(image.id)
                    elif image.dominant_colors:
                        for color_data in image.dominant_colors:
                            if color_data.get('hex'):
                                if self.color_distance_hex(hex_color, color_data['hex']) <= color_distance:
                                    matching_images.append(image.id)
                                    break

                return queryset.filter(id__in=matching_images) if matching_images else queryset.none()
        except (ValueError, AttributeError):
            pass

        return queryset

    @staticmethod
    def color_distance_hex(hex1, hex2):
        """Calculate Euclidean distance between two hex colors"""
        try:
            rgb1 = ImageFilter.hex_to_rgb(hex1)
            rgb2 = ImageFilter.hex_to_rgb(hex2)

            # Euclidean distance in RGB space
            distance = sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5
            return int(distance)
        except (ValueError, TypeError):
            return 999  # Large distance for invalid colors

    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))