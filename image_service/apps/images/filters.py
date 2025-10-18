# مسیر: image_service/apps/images/filters.py
import django_filters
from django.db import models
from django.core.cache import cache
from typing import Dict, List, Any
import time
import logging
from .models import Movie, Tag

logger = logging.getLogger(__name__)

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
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption,
    # Additional crew filters
    DirectorOption, CinematographerOption, EditorOption,
    ColoristOption, CostumeDesignerOption, ProductionDesignerOption,
    # New models
    ShadeOption, ArtistOption, FilmingLocationOption, LocationTypeOption, YearOption
)

class ImageFilter(django_filters.FilterSet):
    """Filter for Image model - matches all ForeignKey/ManyToMany fields + tags"""

    # Search filters (support both 'search' and 'q' parameters)
    search = django_filters.CharFilter(method='search_text', label="Search")
    q = django_filters.CharFilter(method='search_text', label="Search (alias for 'search')")

    # Tags filter (ManyToMany)
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__name',
        to_field_name='name',
        queryset=Tag.objects.all(),
        conjoined=True,
        label="Tags (by name, comma-separated)"
    )

    # All ForeignKey/ManyToMany fields from Image model as filters
    actor = django_filters.CharFilter(method='filter_by_option', label="Actor")
    age = django_filters.CharFilter(method='filter_by_option', label="Age")
    artist = django_filters.CharFilter(method='filter_by_option', label="Artist")
    aspect_ratio = django_filters.CharFilter(method='filter_by_option', label="Aspect Ratio")
    camera = django_filters.CharFilter(method='filter_by_option', label="Camera")
    camera_type = django_filters.CharFilter(method='filter_by_option', label="Camera Type")
    cinematographer = django_filters.CharFilter(method='filter_by_option', label="Cinematographer")
    color = django_filters.CharFilter(method='filter_by_option', label="Color")
    colorist = django_filters.CharFilter(method='filter_by_option', label="Colorist")
    composition = django_filters.CharFilter(method='filter_by_option', label="Composition")
    genre = django_filters.CharFilter(method='filter_by_option', label="Genre")
    costume_designer = django_filters.CharFilter(method='filter_by_option', label="Costume Designer")
    description_filter = django_filters.CharFilter(method='filter_by_option', label="Description Filter")
    director = django_filters.CharFilter(method='filter_by_option', label="Director")
    editor = django_filters.CharFilter(method='filter_by_option', label="Editor")
    ethnicity = django_filters.CharFilter(method='filter_by_option', label="Ethnicity")
    film_stock = django_filters.CharFilter(method='filter_by_option', label="Film Stock")
    filming_location = django_filters.CharFilter(method='filter_by_option', label="Filming Location")
    format = django_filters.CharFilter(method='filter_by_option', label="Format")
    frame_rate = django_filters.CharFilter(method='filter_by_option', label="Frame Rate")
    frame_size = django_filters.CharFilter(method='filter_by_option', label="Frame Size")
    gender = django_filters.CharFilter(method='filter_by_option', label="Gender")
    interior_exterior = django_filters.CharFilter(method='filter_by_option', label="Interior/Exterior")
    lab_process = django_filters.CharFilter(method='filter_by_option', label="Lab Process")
    lens = django_filters.CharFilter(method='filter_by_option', label="Lens")
    lens_size = django_filters.CharFilter(method='filter_by_option', label="Lens Size")
    lens_type = django_filters.CharFilter(method='filter_by_option', label="Lens Type")
    lighting = django_filters.CharFilter(method='filter_by_option', label="Lighting")
    lighting_type = django_filters.CharFilter(method='filter_by_option', label="Lighting Type")
    location = django_filters.CharFilter(method='filter_by_option', label="Location")
    location_type = django_filters.CharFilter(method='filter_by_option', label="Location Type")
    media_type = django_filters.CharFilter(method='filter_by_option', label="Media Type")
    movie = django_filters.CharFilter(method='filter_by_option', label="Movie")
    movie_slug = django_filters.CharFilter(method='filter_by_movie_slug', label="Movie Slug")
    number_of_people = django_filters.CharFilter(method='filter_by_option', label="Number of People")
    optical_format = django_filters.CharFilter(method='filter_by_option', label="Optical Format")
    production_designer = django_filters.CharFilter(method='filter_by_option', label="Production Designer")
    resolution = django_filters.CharFilter(method='filter_by_option', label="Resolution")
    setting = django_filters.CharFilter(method='filter_by_option', label="Setting")
    shade = django_filters.CharFilter(method='filter_by_option', label="Shade")
    shot_time = django_filters.CharFilter(method='filter_by_option', label="Shot Time")
    shot_type = django_filters.CharFilter(method='filter_by_option', label="Shot Type")
    time_of_day = django_filters.CharFilter(method='filter_by_option', label="Time of Day")
    time_period = django_filters.CharFilter(method='filter_by_option', label="Time Period")
    vfx_backing = django_filters.CharFilter(method='filter_by_option', label="VFX Backing")
    year = django_filters.CharFilter(method='filter_by_option', label="Year")

    # Direct field filters (not Option models)
    release_year = django_filters.NumberFilter(field_name='release_year', label="Release Year")
    release_year__gte = django_filters.NumberFilter(field_name='release_year', lookup_expr='gte', label="Release Year From")
    release_year__lte = django_filters.NumberFilter(field_name='release_year', lookup_expr='lte', label="Release Year To")

    class Meta:
        model = Image
        fields = []  # All fields are handled by individual filters above

    # Custom filter methods for name/ID support
    def filter_by_option(self, queryset, name, value):
        """Generic filter method that handles both ID and name lookups"""
        if not value:
            return queryset

        # Special handling for movie field (not an Option model)
        if name == 'movie':
            return self._filter_by_movie(queryset, value)

        # Special handling for media_type to be more inclusive
        if name == 'media_type':
            return self._filter_by_media_type(queryset, value)

        # Special handling for age to support partial matching (e.g., "Child" matches "Child (0-12)")
        if name == 'age':
            return self._filter_by_age(queryset, value)

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
            # Crew filters
            'director': DirectorOption,
            'cinematographer': CinematographerOption,
            'editor': EditorOption,
            'costume_designer': CostumeDesignerOption,
            'production_designer': ProductionDesignerOption,
            'colorist': ColoristOption,
            # Other filters
            'actor': ActorOption,
            'artist': ArtistOption,
            'camera': CameraOption,
            'lens': LensOption,
            'location': LocationOption,
            'filming_location': FilmingLocationOption,
            'location_type': LocationTypeOption,
            'setting': SettingOption,
            'year': YearOption,
            'shade': ShadeOption,
            'film_stock': FilmStockOption,
            'shot_time': ShotTimeOption,
            'description_filter': DescriptionOption,
            'vfx_backing': VfxBackingOption,
        }

        model_class = field_map.get(name)
        if not model_class:
            return queryset

        return self._filter_by_option(queryset, model_class, name, value)

    def _filter_by_age(self, queryset, value):
        """Special handling for age filter to support partial matching"""
        if not value:
            return queryset

        # Split by comma for multiple values
        age_terms = [v.strip() for v in value.split(',') if v.strip()]

        if not age_terms:
            return queryset

        from django.db.models import Q
        from .models import AgeOption

        # Build Q objects for partial matching
        q_objects = Q()
        for term in age_terms:
            # Case-insensitive partial matching on age values
            q_objects |= Q(age__value__icontains=term)

        return queryset.filter(q_objects)

    def _filter_by_movie(self, queryset, value):
        """Filter images by movie title (special handling for Movie model)"""
        if not value:
            return queryset

        # Split by comma for multiple values
        movie_titles = [v.strip() for v in value.split(',') if v.strip()]

        if not movie_titles:
            return queryset

        # Import Movie model
        from .models import Movie
        from django.db.models import Max

        movie_ids = []

        for title in movie_titles:
            # Find the movie with this title that has the highest image count
            # This matches the logic used in cache_utils for filter options
            movie = (Movie.objects
                    .filter(title__iexact=title)
                    .order_by('-image_count', '-id')  # Prefer movies with more images, then higher ID
                    .first())

            if movie:
                movie_ids.append(movie.id)

        if movie_ids:
            return queryset.filter(movie_id__in=movie_ids)

        # If no movies found, return empty queryset
        return queryset.none()

    def filter_by_movie_slug(self, queryset, name, value):
        """Filter images by movie slug"""
        if not value:
            return queryset

        # Split by comma for multiple values
        movie_slugs = [v.strip() for v in value.split(',') if v.strip()]

        if not movie_slugs:
            return queryset

        # Import Movie model
        from .models import Movie

        # Find movie IDs by slug (exact match)
        movie_ids = Movie.objects.filter(slug__in=movie_slugs).values_list('id', flat=True)

        if movie_ids:
            return queryset.filter(movie_id__in=movie_ids)

        # If no movies found, return empty queryset
        return queryset.none()

    def _filter_by_media_type(self, queryset, value):
        """Filter images by media type with inclusive movie handling"""
        if not value:
            return queryset

        # Normalize the input value for case-insensitive matching
        search_value = value.lower().strip()

        # Special handling for movie-related searches
        movie_types = ['movie', 'film', 'cinematic', 'feature film', 'motion picture', 'theatrical']
        if any(movie_type in search_value for movie_type in movie_types):
            # Include all movie-related media types
            movie_media_types = [
                'movie', 'Feature Film', 'Film', 'Motion Picture', 'Cinematic',
                'Theatrical', 'Digital', 'Broadcast'
            ]
            return queryset.filter(media_type__value__in=movie_media_types)
        else:
            # Use standard option filtering for other media types
            return self._filter_by_option(queryset, MediaTypeOption, 'media_type', value)

    def _filter_by_option(self, queryset, model_class, field_name, value):
        """Generic method to filter by option using either ID or name - optimized for performance"""
        if not value:
            return queryset

        # Split by comma for multiple values
        values = [v.strip() for v in value.split(',') if v.strip()]

        if not values:
            return queryset

        option_ids = []
        name_lookups = []

        # Separate IDs from names for efficient querying
        for val in values:
            # Try to find by ID first
            try:
                option_ids.append(int(val))
                continue
            except ValueError:
                pass

            # Collect names for batch lookup
            name_lookups.append(val)

        # Batch lookup for names (case-insensitive)
        if name_lookups:
            try:
                # Use Q objects for case-insensitive OR queries
                from django.db.models import Q
                q_objects = Q()
                for name in name_lookups:
                    q_objects |= Q(value__iexact=name)

                name_options = model_class.objects.filter(q_objects).values_list('id', flat=True)
                option_ids.extend(name_options)
            except Exception:
                pass

        if option_ids:
            # Remove duplicates
            option_ids = list(set(option_ids))

            # Apply the filter - if no images match, return empty queryset
            if field_name == 'genre':
                return queryset.filter(**{f'{field_name}__id__in': option_ids})
            else:
                filter_kwargs = {f'{field_name}__id__in': option_ids}
                return queryset.filter(**filter_kwargs)

        # If no matching options found, return empty queryset
        # This ensures filters work correctly - if no data matches, return no results
        return queryset.none()

    def search_text(self, queryset, name, value):
        """Optimized text search with proper indexing support"""
        if not value or len(value.strip()) < 2:
            return queryset

        search_value = value.strip()
        return queryset.filter(
            models.Q(title__icontains=search_value) |
            models.Q(description__icontains=search_value) |
            models.Q(tags__name__icontains=search_value)
        ).distinct()

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

    def get_filter_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for filter usage"""
        # This would be populated by monitoring middleware
        return {
            'most_used_filters': ['color', 'shot_type', 'lighting', 'genre'],
            'average_filter_time': 0.05,  # seconds
            'total_filter_queries': 1000,
            'cache_hit_rate': 0.75
        }

    def optimize_filter_query(self, queryset, applied_filters: Dict[str, Any]) -> 'QuerySet':
        """Apply query optimizations based on applied filters"""
        # Add specific optimizations for common filter combinations
        filter_keys = set(applied_filters.keys())

        # Optimize for common filter combinations
        if filter_keys == {'color', 'lighting'}:
            # Use composite index for color + lighting queries
            pass  # Already optimized by database indexes

        elif filter_keys == {'shot_type', 'time_of_day'}:
            # Use composite index for shot + time queries
            pass

        elif 'search' in filter_keys and len(filter_keys) == 1:
            # Optimize single search queries
            queryset = queryset.select_related('movie')  # Add movie for search context

        return queryset


class MovieFilter(django_filters.FilterSet):
    """Filter for Movie model - matches all Movie model fields"""
    title = django_filters.CharFilter(lookup_expr='icontains')
    year = django_filters.NumberFilter()
    year__gte = django_filters.NumberFilter(field_name='year', lookup_expr='gte')
    year__lte = django_filters.NumberFilter(field_name='year', lookup_expr='lte')
    genre = django_filters.CharFilter(lookup_expr='icontains')
    director = django_filters.CharFilter(field_name='director__value', lookup_expr='icontains')
    cinematographer = django_filters.CharFilter(field_name='cinematographer__value', lookup_expr='icontains')
    country = django_filters.CharFilter(lookup_expr='icontains')
    language = django_filters.CharFilter(lookup_expr='icontains')
    cast = django_filters.CharFilter(lookup_expr='icontains')
    colorist = django_filters.CharFilter(lookup_expr='icontains')
    costume_designer = django_filters.CharFilter(lookup_expr='icontains')
    production_designer = django_filters.CharFilter(lookup_expr='icontains')
    editor = django_filters.CharFilter(field_name='editor__value', lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    duration = django_filters.NumberFilter()

    class Meta:
        model = Movie
        fields = ['title', 'year', 'genre', 'director', 'cinematographer', 'country', 'language', 'cast', 'colorist', 'costume_designer', 'production_designer', 'editor', 'description', 'duration']


class TagFilter(django_filters.FilterSet):
    """Filter for Tag model - matches all Tag model fields"""
    name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Tag
        fields = ['name']