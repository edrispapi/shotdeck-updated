"""
Cache utilities for option filters
"""
from django.core.cache import cache
from django.conf import settings
import json
from .models import (
    Movie, Tag, ActorOption, CameraOption, LensOption, LocationOption, SettingOption,
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption,
    DirectorOption, CinematographerOption, EditorOption,
    GenreOption, ColorOption, MediaTypeOption, AspectRatioOption,
    OpticalFormatOption, FormatOption, InteriorExteriorOption, TimeOfDayOption,
    NumberOfPeopleOption, GenderOption, AgeOption, EthnicityOption,
    FrameSizeOption, ShotTypeOption, CompositionOption, LensSizeOption,
    LensTypeOption, LightingOption, LightingTypeOption, CameraTypeOption,
    ResolutionOption, FrameRateOption
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
        'genre': GenreOption,
        'color': ColorOption,
        'media_type': MediaTypeOption,
        'aspect_ratio': AspectRatioOption,
        'optical_format': OpticalFormatOption,
        'format': FormatOption,
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

    model_class = model_mapping.get(filter_type)
    if not model_class:
        return None

    # Get all options, not just those with display_order
    options = model_class.objects.all().order_by('value')[:100]  # Limit to 100 options
    return [
        {
            'id': option.id,
            'value': option.value,
            'display_order': getattr(option, 'display_order', None),
            'metadata': getattr(option, 'metadata', None)
        }
        for option in options
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
        'genre', 'color', 'media_type', 'aspect_ratio', 'optical_format',
        'format', 'interior_exterior', 'time_of_day', 'number_of_people',
        'gender', 'age', 'ethnicity', 'frame_size', 'shot_type',
        'composition', 'lens_size', 'lens_type', 'lighting',
        'lighting_type', 'camera_type', 'resolution', 'frame_rate',
        'actor', 'camera', 'lens', 'location', 'setting',
        'film_stock', 'shot_time', 'description_filter', 'vfx_backing'
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
