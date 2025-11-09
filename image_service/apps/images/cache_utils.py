"""
Cache utilities for option filters
"""
from django.core.cache import cache
from django.conf import settings
import json
from .models import (
    # Original models
    Movie, Tag, ActorOption, CameraOption, LensOption, LocationOption, SettingOption,
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption,
    DirectorOption, CinematographerOption, EditorOption,
    GenreOption, ColorOption, MediaTypeOption, AspectRatioOption,
    OpticalFormatOption, FormatOption, InteriorExteriorOption, TimeOfDayOption,
    TimePeriodOption, NumberOfPeopleOption, GenderOption, AgeOption, EthnicityOption,
    FrameSizeOption, ShotTypeOption, CompositionOption, LensSizeOption,
    LensTypeOption, LightingOption, LightingTypeOption, CameraTypeOption,
    ResolutionOption, FrameRateOption,
    # New models added for comprehensive filter support
    CostumeDesignerOption, ProductionDesignerOption, ColoristOption,
    YearOption, ShadeOption, FilmingLocationOption, LocationTypeOption, ArtistOption
)

# Cache keys
FILTER_CACHE_KEY = "filters:{filter_type}:v{version}"
FILTER_VERSION_KEY = "filter_version:{filter_type}"

# Cache timeout (24 hours)
CACHE_TIMEOUT = 24 * 60 * 60


def get_filter_cache_key(filter_type, version=None):
    """Generate cache key for filter options"""
    if version is None:
        version = get_filter_version(filter_type)
    return FILTER_CACHE_KEY.format(filter_type=filter_type, version=version)


def get_filter_version(filter_type):
    """Get current version for filter type"""
    version = cache.get(FILTER_VERSION_KEY.format(filter_type=filter_type))
    if version is None:
        version = 1
        set_filter_version(filter_type, version)
    return version


def set_filter_version(filter_type, version):
    """Set version for filter type"""
    cache.set(FILTER_VERSION_KEY.format(filter_type=filter_type), version, CACHE_TIMEOUT)


def invalidate_filter_cache(filter_type):
    """Invalidate cache for specific filter type by incrementing version"""
    current_version = get_filter_version(filter_type)
    new_version = current_version + 1
    set_filter_version(filter_type, new_version)
    return new_version


def get_cached_filter_options(filter_type):
    """Get filter options from cache or database"""
    cache_key = get_filter_cache_key(filter_type)
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return cached_data

    # Cache miss - get from database
    options = get_filter_options_from_db(filter_type)
    if options is not None:
        cache.set(cache_key, options, CACHE_TIMEOUT)

    return options


def get_filter_options_from_db(filter_type):
    """Get filter options from database"""
    model_mapping = {
        # Original models
        'genre': GenreOption,
        'color': ColorOption,
        'media_type': MediaTypeOption,
        'aspect_ratio': AspectRatioOption,
        'optical_format': OpticalFormatOption,
        'format': FormatOption,
        'interior_exterior': InteriorExteriorOption,
        'time_of_day': TimeOfDayOption,
        'time_period': TimePeriodOption,
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
        # New models added for comprehensive filter support
        'director': DirectorOption,
        'cinematographer': CinematographerOption,
        'editor': EditorOption,
        'costume_designer': CostumeDesignerOption,
        'production_designer': ProductionDesignerOption,
        'colorist': ColoristOption,
        'movie': Movie,
        'year': YearOption,
        'shade': ShadeOption,
        'filming_location': FilmingLocationOption,
        'location_type': LocationTypeOption,
        'artist': ArtistOption,
    }

    model_class = model_mapping.get(filter_type)
    if not model_class:
        return None

    # Handle Movie model differently since it doesn't have display_order
    if model_class == Movie:
        # Get unique movies by title, preferring ones with higher image counts
        from django.db.models import Max
        unique_movies = (model_class.objects
                        .values('title', 'year')
                        .annotate(
                            movie_id=Max('id'),
                            image_count=Max('image_count'),
                            slug=Max('slug')
                        )
                        .order_by('-image_count', 'title')[:100])  # Prioritize movies with more images

        return [
            {
                'id': movie['movie_id'],
                'value': movie['title'],
                'label': f"{movie['title']} ({movie['year']})" if movie['year'] else movie['title'],
                'slug': movie['slug'],
                'display_order': None,
                'metadata': {'year': movie['year'], 'image_count': movie['image_count']}
            }
            for movie in unique_movies
        ]

    # For Option models, prioritize standardized options (with display_order > 0) over database-populated options
    standardized_options = model_class.objects.filter(display_order__gt=0).order_by('display_order')
    standardized_count = standardized_options.count()

    if standardized_count > 0:
        # Return standardized options first, then fill with database options if needed
        remaining_slots = 100 - standardized_count
        if remaining_slots > 0:
            # Get database options that have display_order=0 or null (avoiding duplicates)
            db_options = model_class.objects.filter(display_order__in=[0, None]).order_by('value')
            all_options = list(standardized_options) + list(db_options)
        else:
            all_options = list(standardized_options)
    else:
        # Fallback to old behavior if no standardized options exist
        all_options = model_class.objects.all().order_by('value')

    return [
        {
            'id': option.id,
            'value': option.value,
            'display_order': getattr(option, 'display_order', None),
            'metadata': getattr(option, 'metadata', None)
        }
        for option in all_options
    ]


def get_cached_entity_slugs(entity_type):
    """Get entity slugs from cache or database"""
    cache_key = f"entity_slugs:{entity_type}:v1"
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return cached_data

    # Cache miss - get from database
    slugs = get_entity_slugs_from_db(entity_type)
    if slugs is not None:
        cache.set(cache_key, slugs, CACHE_TIMEOUT)

    return slugs


def get_entity_slugs_from_db(entity_type):
    """Get entity slugs from database"""
    model_mapping = {
        'movies': (Movie, 'title', 'slug'),
        'directors': (DirectorOption, 'value', 'slug'),
        'cinematographers': (CinematographerOption, 'value', 'slug'),
        'editors': (EditorOption, 'value', 'slug'),
        'actors': (ActorOption, 'value', 'slug'),
        'tags': (Tag, 'name', 'slug'),
        'cameras': (CameraOption, 'value', None),  # No slug field
        'lenses': (LensOption, 'value', None),     # No slug field
        'locations': (LocationOption, 'value', None), # No slug field
        'settings': (SettingOption, 'value', None),   # No slug field
        'film_stocks': (FilmStockOption, 'value', None), # No slug field
        'shot_times': (ShotTimeOption, 'value', None),   # No slug field
        'descriptions': (DescriptionOption, 'value', None), # No slug field
        'vfx_backings': (VfxBackingOption, 'value', None), # No slug field
    }

    mapping = model_mapping.get(entity_type)
    if not mapping:
        return None

    model_class, value_field, slug_field = mapping

    if slug_field:
        # Models with slug field
        entities = model_class.objects.exclude(slug__isnull=True).exclude(slug='').values(value_field, 'slug')
        return [
            {
                'value': entity[value_field],
                'slug': entity['slug']
            }
            for entity in entities
        ]
    else:
        # Models without slug field, use value as slug
        entities = model_class.objects.all().values(value_field)
        return [
            {
                'value': entity[value_field],
                'slug': entity[value_field]
            }
            for entity in entities
        ]


def get_all_cached_filters():
    """Get all filter options from cache"""
    filter_types = [
        # Original filters
        'genre', 'color', 'media_type', 'aspect_ratio', 'optical_format',
        'format', 'interior_exterior', 'time_of_day', 'time_period', 'number_of_people',
        'gender', 'age', 'ethnicity', 'frame_size', 'shot_type',
        'composition', 'lens_size', 'lens_type', 'lighting',
        'lighting_type', 'camera_type', 'resolution', 'frame_rate',
        'actor', 'camera', 'lens', 'location', 'setting',
        'film_stock', 'shot_time', 'description_filter', 'vfx_backing',
        # New filters added for comprehensive 37 filter support
        'director', 'cinematographer', 'editor', 'costume_designer',
        'production_designer', 'colorist', 'movie', 'year', 'shade',
        'filming_location', 'location_type'
    ]

    all_filters = {}
    for filter_type in filter_types:
        options = get_cached_filter_options(filter_type)
        if options:
            all_filters[filter_type] = options

    # Add entity slugs
    entity_types = ['movies', 'directors', 'cinematographers', 'editors', 'actors', 'tags']
    for entity_type in entity_types:
        slugs = get_cached_entity_slugs(entity_type)
        if slugs:
            all_filters[f'{entity_type}_slugs'] = slugs

    return all_filters


def invalidate_all_filter_cache():
    """Invalidate cache for all filter types"""
    filter_types = [
        'genre', 'color', 'media_type', 'aspect_ratio', 'optical_format',
        'format', 'interior_exterior', 'time_of_day', 'number_of_people',
        'gender', 'age', 'ethnicity', 'frame_size', 'shot_type',
        'composition', 'lens_size', 'lens_type', 'lighting',
        'lighting_type', 'camera_type', 'resolution', 'frame_rate'
    ]

    for filter_type in filter_types:
        invalidate_filter_cache(filter_type)


# Cache decorators
def cache_filter_options(filter_type):
    """Decorator to cache filter options"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = get_filter_cache_key(filter_type)
            cached_data = cache.get(cache_key)

            if cached_data is not None:
                return cached_data

            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, CACHE_TIMEOUT)
            return result
        return wrapper
    return decorator


def invalidate_cache_on_save(model_class, filter_type):
    """Invalidate cache when model is saved"""
    def save_handler(sender, instance, **kwargs):
        invalidate_filter_cache(filter_type)

    from django.db.models.signals import post_save, post_delete
    post_save.connect(save_handler, sender=model_class)
    post_delete.connect(save_handler, sender=model_class)
