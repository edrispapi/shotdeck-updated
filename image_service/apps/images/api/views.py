# Path: /image_service/apps/images/api/views.py
from apps.images.filters import ImageFilter, MovieFilter, TagFilter
import logging
import time
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.conf import settings

from apps.images.filters import ImageFilter
from apps.images.models import (
    Image, Movie, Tag,
    # Base option models
    BaseOption, GenreOption, ColorOption, MediaTypeOption, AspectRatioOption,
    OpticalFormatOption, FormatOption, TimePeriodOption, LabProcessOption, InteriorExteriorOption, TimeOfDayOption,
    NumberOfPeopleOption, GenderOption, AgeOption, EthnicityOption,
    FrameSizeOption, ShotTypeOption, CompositionOption, LensSizeOption,
    LensTypeOption, LightingOption, LightingTypeOption, CameraTypeOption,
    ResolutionOption, FrameRateOption, MovieOption, ActorOption, CameraOption,
    LensOption, LocationOption, SettingOption,
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption,
    # New models
    ShadeOption, ArtistOption, FilmingLocationOption, LocationTypeOption, YearOption,
    ColoristOption, CostumeDesignerOption, ProductionDesignerOption,
    DirectorOption, CinematographerOption, EditorOption
)
from .serializers import (
    ImageSerializer, MovieImageSerializer, ImageListSerializer, MovieSerializer, TagSerializer,
    # Option serializers
    GenreOptionSerializer, ColorOptionSerializer, MediaTypeOptionSerializer,
    AspectRatioOptionSerializer, OpticalFormatOptionSerializer, FormatOptionSerializer,
    InteriorExteriorOptionSerializer, TimeOfDayOptionSerializer, NumberOfPeopleOptionSerializer,
    GenderOptionSerializer, AgeOptionSerializer, EthnicityOptionSerializer,
    FrameSizeOptionSerializer, ShotTypeOptionSerializer, CompositionOptionSerializer,
    LensSizeOptionSerializer, LensTypeOptionSerializer, LightingOptionSerializer,
    LightingTypeOptionSerializer, CameraTypeOptionSerializer, ResolutionOptionSerializer,
    FrameRateOptionSerializer, MovieOptionSerializer, ActorOptionSerializer, CameraOptionSerializer,
    LensOptionSerializer, LocationOptionSerializer, SettingOptionSerializer,
    FilmStockOptionSerializer, ShotTimeOptionSerializer,
    DescriptionOptionSerializer, VfxBackingOptionSerializer,
    DirectorOptionSerializer, CinematographerOptionSerializer, EditorOptionSerializer,
    ColoristOptionSerializer, CostumeDesignerOptionSerializer, ProductionDesignerOptionSerializer,
    # New serializers
    ShadeOptionSerializer, ArtistOptionSerializer, FilmingLocationOptionSerializer,
    LocationTypeOptionSerializer, YearOptionSerializer
)
from messaging.producers import send_event
from apps.common.serializers import Error401Serializer, Error403Serializer, Error404Serializer
from apps.images.cache_utils import get_cached_filter_options, get_all_cached_filters, invalidate_filter_cache

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Health check endpoint for the image service"""

    def get(self, request):
        """Return service health status"""
        try:
            # Check database connectivity
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()

            # Check if we can access models
            image_count = Image.objects.count()

            return Response({
                "status": "healthy",
                "database": "connected",
                "image_count": image_count,
                "timestamp": serializers.DateTimeField().to_representation(serializers.DateTimeField().get_default())
            })

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return Response(
                {"status": "unhealthy", "error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


# Helper function to create selectable options
def create_options_list(option_strings):
    """Convert list of strings to list of selectable option objects"""
    return [{"value": opt, "label": opt} for opt in option_strings]

# Filter configuration removed - no longer needed

TIME_PERIOD_RANGES = {
    'future': {'gte': 2026}, '2020s': {'gte': 2020, 'lte': 2029}, '2010s': {'gte': 2010, 'lte': 2019},
    '2000s': {'gte': 2000, 'lte': 2009}, '1990s': {'gte': 1990, 'lte': 1999}, '1980s': {'gte': 1980, 'lte': 1989},
    '1970s': {'gte': 1970, 'lte': 1979}, '1960s': {'gte': 1960, 'lte': 1969}, '1950s': {'gte': 1950, 'lte': 1959},
    '1940s': {'gte': 1940, 'lte': 1949}, '1930s': {'gte': 1930, 'lte': 1939}, '1920s': {'gte': 1920, 'lte': 1929},
    '1910s': {'gte': 1910, 'lte': 1919}, '1900s': {'gte': 1900, 'lte': 1909}, '1800s': {'gte': 1800, 'lte': 1899},
    '1700s': {'gte': 1700, 'lte': 1799}, 'renaissance': {'gte': 1400, 'lte': 1700}, 'medieval': {'gte': 500, 'lte': 1400},
    'ancient': {'gte': -2000, 'lte': 500}, 'stone_age': {'lte': -2000},
}


class ImageViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for managing images with optimized performance - READ ONLY
    """
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ImageFilter
    lookup_field = 'slug'

    def get_queryset(self):
        """Optimized queryset with select_related for all foreign key fields"""
        return Image.objects.select_related(
            'movie', 'actor', 'camera', 'cinematographer', 'director', 'lens', 'film_stock',
            'setting', 'location', 'filming_location', 'aspect_ratio', 'time_period',
            'time_of_day', 'interior_exterior', 'number_of_people', 'gender', 'age',
            'ethnicity', 'frame_size', 'shot_type', 'composition', 'lens_type',
            'lighting', 'lighting_type', 'camera_type', 'resolution', 'frame_rate',
            'vfx_backing', 'shade', 'artist', 'location_type', 'media_type', 'color',
            'optical_format', 'format', 'lab_process'
        ).prefetch_related('tags', 'genre')

    def filter_queryset(self, queryset):
        """Optimized filtering with performance monitoring"""
        start_time = time.time()

        # Apply standard filtering
        filtered_queryset = super().filter_queryset(queryset)

        # Apply additional optimizations based on applied filters
        applied_filters = {}
        if hasattr(self.request, 'query_params'):
            applied_filters = dict(self.request.query_params.lists())

        # Apply filter-specific optimizations
        filter_instance = self.filterset_class(data=self.request.query_params, queryset=filtered_queryset)
        if hasattr(filter_instance, 'optimize_filter_query'):
            filtered_queryset = filter_instance.optimize_filter_query(filtered_queryset, applied_filters)

        # Log performance for slow queries
        duration = time.time() - start_time
        if duration > 0.1:  # Log queries taking > 100ms
            logger.info(
                f'Slow filter query: {dict(self.request.query_params)} '
                f'took {duration:.3f}s, returned {filtered_queryset.count()} results'
            )

        return filtered_queryset

    filter_backends = [DjangoFilterBackend]
    filterset_class = ImageFilter
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return ImageListSerializer  # Lighter serializer for list views
        return ImageSerializer  # Full serializer for detail views

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Send event to message queue
        try:
            send_event('image_created', {
                'image_id': serializer.instance.id,
                'title': serializer.instance.title,
                'movie_slug': serializer.instance.movie.slug if serializer.instance.movie else None,
            })
        except Exception as e:
            logger.warning(f"Failed to send image_created event: {e}")

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # Invalidate cache after update
        filter_type = self.get_filter_type()
        invalidate_filter_cache(filter_type)
        return response

    def retrieve(self, request, *args, **kwargs):
        """
        Get detailed image information with complete metadata.
        """
        image = self.get_object()
        # Use full ImageSerializer to get all metadata fields
        serializer = self.get_serializer(image)
        return Response({
            'success': True,
            'data': serializer.data
        })


    def _build_json_file_index(self):
        """
        Build an index of JSON data for fast lookups.
        Maps titles to data entries.
        """
        from pathlib import Path
        import json

        backup_file = Path(settings.BASE_DIR) / 'images_only_backup.json'
        index = {
            'by_title': {},
            'by_slug': {},
            'last_updated': None
        }

        if not backup_file.exists():
            return index

        print("Building JSON data index for fast lookups...")

        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                data_list = json.load(f)

            for item in data_list:
                if 'fields' in item:
                    fields = item['fields']
                    title = fields.get('title', '').strip()
                    slug = fields.get('slug', '').strip()

                    if title:
                        # Store by title (lowercase for case-insensitive matching)
                        index['by_title'][title.lower()] = item

                    if slug:
                        # Store by slug
                        index['by_slug'][slug.lower()] = item

        except (json.JSONDecodeError, KeyError):
            pass

        print(f"Index built: {len(index['by_title'])} titles indexed")
        return index

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        # Invalidate cache after partial update
        filter_type = self.get_filter_type()
        invalidate_filter_cache(filter_type)
        return response

    def get_filter_type(self):
        """Get filter type for cache invalidation"""
        return 'image'

    def list(self, request, *args, **kwargs):
        """
        List images using database queries with filtering
        """
        try:
            # Get the filtered queryset first to get accurate counts
            queryset = self.filter_queryset(self.get_queryset())

            # Apply pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={'request': request})
                paginated_response = self.get_paginated_response(serializer.data)
                data = paginated_response.data
            else:
                # If pagination didn't return a page (should be rare since default
                # pagination is enabled), enforce a maximum page size here so the
                # response always returns at most the default page size (20).
                try:
                    page_size = settings.REST_FRAMEWORK.get('PAGE_SIZE', 20)
                except Exception:
                    page_size = 20

                limited_qs = queryset[:page_size]
                serializer = self.get_serializer(limited_qs, many=True, context={'request': request})
                data = {
                    'results': serializer.data,
                    'count': queryset.count(),
                    'next': None,
                    'previous': None
                }

            # Extract pagination info
            results = data['results']
            count = len(results)  # Count of items in current page

            # Get total count from pagination data or queryset - ensure it's never null/empty
            total = data.get('count')
            if total is None or total == 'null':
                # Fallback: get count from queryset if pagination didn't set it
                if hasattr(queryset, 'count'):
                    total = queryset.count()
                else:
                    total = len(results)
            total = int(total)  # Ensure it's an integer

            # Get applied filters (non-empty values from request)
            applied_filters = {}
            for key, value in request.query_params.items():
                if key not in ['limit', 'offset', 'page'] and value and value != ['']:
                    applied_filters[key] = value[0] if isinstance(value, list) else value

            custom_response = {
                'success': True,
                'count': total,  # Total count of all matching results
                'results': results,  # Current page results
                'filters_applied': applied_filters,
                'message': 'Images retrieved from database',
                'source': 'database'
            }

            return Response(custom_response)

        except Exception as e:
            return Response({
                'success': False,
                'count': 0,
                'results': [],
                'error': f'Database query failed: {str(e)}',
                'message': 'Using database queries'
            }, status=500)




    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    # def retrieve(self, request, *args, **kwargs):
    #     """
    #     Get detailed movie information with comprehensive statistics and related data.
    #     """
    #     movie = self.get_object()
    #
    #     # Get all images for this movie with related data
    #     images = movie.images.select_related(
    #         'director', 'cinematographer', 'camera', 'lens', 'lighting_type',
    #         'shot_type', 'location', 'time_period', 'color'
    #     ).prefetch_related('genre', 'tags')
    #
    #     # Calculate comprehensive statistics for ALL fields
    #     total_images = images.count()

        # # Genre distribution
        # genres_data = images.values('genre__value').annotate(
        #     count=Count('id')
        # ).filter(genre__value__isnull=False).order_by('-count')[:10]

        # # Tag distribution
        # tags_data = []
        # for image in images:
        #     for tag in image.tags.all():
        #         tags_data.append(tag.name)

        # from collections import Counter
        # tag_counts = Counter(tags_data).most_common(10)
        # tags_formatted = [{'name': tag, 'count': count} for tag, count in tag_counts]

        # # Actor distribution (from actors field in images)
        # actors_data = images.values('actor__value').annotate(
        #     count=Count('id')
        # ).filter(actor__value__isnull=False).order_by('-count')[:10]

        # # Aspect ratio distribution
        # aspect_ratios_data = images.values('aspect_ratio__value').annotate(
        #     count=Count('id')
        # ).filter(aspect_ratio__value__isnull=False).order_by('-count')[:10]

        # # Camera distribution
        # cameras_data = images.values('camera__value').annotate(
        #     count=Count('id')
        # ).filter(camera__value__isnull=False).order_by('-count')[:10]

        # # Cinematographer distribution
        # cinematographers_data = images.values('cinematographer__value').annotate(
        #     count=Count('id')
        # ).filter(cinematographer__value__isnull=False).order_by('-count')[:10]

        # # Color distribution
        # colors_data = images.values('color__value').annotate(
        #     count=Count('id')
        # ).filter(color__value__isnull=False).order_by('-count')[:10]

        # # Colorist distribution
        # colorists_data = images.values('colorist__value').annotate(
        #     count=Count('id')
        # ).filter(colorist__value__isnull=False).order_by('-count')[:10]

        # # Composition distribution
        # compositions_data = images.values('composition__value').annotate(
        #     count=Count('id')
        # ).filter(composition__value__isnull=False).order_by('-count')[:10]

        # # Costume designer distribution
        # costume_designers_data = images.values('costume_designer__value').annotate(
        #     count=Count('id')
        # ).filter(costume_designer__value__isnull=False).order_by('-count')[:10]

        # # Director distribution
        # directors_data = images.values('director__value').annotate(
        #     count=Count('id')
        # ).filter(director__value__isnull=False).order_by('-count')[:10]

        # # Editor distribution
        # editors_data = images.values('editor__value').annotate(
        #     count=Count('id')
        # ).filter(editor__value__isnull=False).order_by('-count')[:10]

        # # Film stock distribution
        # film_stocks_data = images.values('film_stock__value').annotate(
        #     count=Count('id')
        # ).filter(film_stock__value__isnull=False).order_by('-count')[:10]

        # # Filming location distribution
        # filming_locations_data = images.values('filming_location__value').annotate(
        #     count=Count('id')
        # ).filter(filming_location__value__isnull=False).order_by('-count')[:10]

        # # Format distribution
        # formats_data = images.values('format__value').annotate(
        #     count=Count('id')
        # ).filter(format__value__isnull=False).order_by('-count')[:10]

        # # Frame size distribution
        # frame_sizes_data = images.values('frame_size__value').annotate(
        #     count=Count('id')
        # ).filter(frame_size__value__isnull=False).order_by('-count')[:10]

        # # Interior/Exterior distribution
        # interior_exterior_data = images.values('interior_exterior__value').annotate(
        #     count=Count('id')
        # ).filter(interior_exterior__value__isnull=False).order_by('-count')[:10]

        # # Lens distribution
        # lenses_data = images.values('lens__value').annotate(
        #     count=Count('id')
        # ).filter(lens__value__isnull=False).order_by('-count')[:10]

        # # Lens size distribution
        # lens_sizes_data = images.values('lens_size__value').annotate(
        #     count=Count('id')
        # ).filter(lens_size__value__isnull=False).order_by('-count')[:10]

        # # Lighting distribution
        # lighting_data = images.values('lighting__value').annotate(
        #     count=Count('id')
        # ).filter(lighting__value__isnull=False).order_by('-count')[:10]

        # # Lighting type distribution
        # lighting_types_data = images.values('lighting_type__value').annotate(
        #     count=Count('id')
        # ).filter(lighting_type__value__isnull=False).order_by('-count')[:10]

        # # Production designer distribution
        # production_designers_data = images.values('production_designer__value').annotate(
        #     count=Count('id')
        # ).filter(production_designer__value__isnull=False).order_by('-count')[:10]

        # # Set distribution
        # sets_data = images.values('setting__value').annotate(
        #     count=Count('id')
        # ).filter(setting__value__isnull=False).order_by('-count')[:10]

        # # Shot time distribution
        # shot_times_data = images.values('shot_time__value').annotate(
        #     count=Count('id')
        # ).filter(shot_time__value__isnull=False).order_by('-count')[:10]

        # # Shot type distribution
        # shot_types_data = images.values('shot_type__value').annotate(
        #     count=Count('id')
        # ).filter(shot_type__value__isnull=False).order_by('-count')[:10]

        # # Story location distribution
        # story_locations_data = images.values('location__value').annotate(
        #     count=Count('id')
        # ).filter(location__value__isnull=False).order_by('-count')[:10]

        # # Time period distribution
        # time_periods_data = images.values('time_period__value').annotate(
        #     count=Count('id')
        # ).filter(time_period__value__isnull=False).order_by('-count')[:10]

        # # Time of day distribution
        # time_of_day_data = images.values('time_of_day__value').annotate(
        #     count=Count('id')
        # ).filter(time_of_day__value__isnull=False).order_by('-count')[:10]

        # # Format the response
        # response_data = {
        #     'movie': {
        #         'id': movie.id,
        #         'slug': movie.slug,
        #         'title': movie.title,
        #         'year': movie.year,
        #         'director': movie.director.value if movie.director else None,
        #         'cinematographer': movie.cinematographer.value if movie.cinematographer else None,
        #         'editor': movie.editor.value if movie.editor else None,
        #         'colorist': movie.colorist if movie.colorist else None,
        #         'production_designer': movie.production_designer if movie.production_designer else None,
        #         'costume_designer': movie.costume_designer if movie.costume_designer else None,
        #     },
        #     'detailed_statistics': {
        #         'total_images': total_images,
        #         'actors': [
        #             {'name': item['actor__value'], 'count': item['count']}
        #             for item in actors_data
        #         ],
        #         'aspect_ratios': [
        #             {'name': item['aspect_ratio__value'], 'count': item['count']}
        #             for item in aspect_ratios_data
        #         ],
        #         'cameras': [
        #             {'name': item['camera__value'], 'count': item['count']}
        #             for item in cameras_data
        #         ],
        #         'cinematographers': [
        #             {'name': item['cinematographer__value'], 'count': item['count']}
        #             for item in cinematographers_data
        #         ],
        #         'colors': [
        #             {'name': item['color__value'], 'count': item['count']}
        #             for item in colors_data
        #         ],
        #         'colorists': [
        #             {'name': item['colorist__value'], 'count': item['count']}
        #             for item in colorists_data
        #         ],
        #         'compositions': [
        #             {'name': item['composition__value'], 'count': item['count']}
        #             for item in compositions_data
        #         ],
        #         'costume_designers': [
        #             {'name': item['costume_designer__value'], 'count': item['count']}
        #             for item in costume_designers_data
        #         ],
        #         'directors': [
        #             {'name': item['director__value'], 'count': item['count']}
        #             for item in directors_data
        #         ],
        #         'editors': [
        #             {'name': item['editor__value'], 'count': item['count']}
        #             for item in editors_data
        #         ],
        #         'film_stocks': [
        #             {'name': item['film_stock__value'], 'count': item['count']}
        #             for item in film_stocks_data
        #         ],
        #         'filming_locations': [
        #             {'name': item['filming_location__value'], 'count': item['count']}
        #             for item in filming_locations_data
        #         ],
        #         'formats': [
        #             {'name': item['format__value'], 'count': item['count']}
        #             for item in formats_data
        #         ],
        #         'frame_sizes': [
        #             {'name': item['frame_size__value'], 'count': item['count']}
        #             for item in frame_sizes_data
        #         ],
        #         'genres': [
        #             {'name': item['genre__value'], 'count': item['count']}
        #             for item in genres_data
        #         ],
        #         'interior_exterior': [
        #             {'name': item['interior_exterior__value'], 'count': item['count']}
        #             for item in interior_exterior_data
        #         ],
        #         'lenses': [
        #             {'name': item['lens__value'], 'count': item['count']}
        #             for item in lenses_data
        #         ],
        #         'lens_sizes': [
        #             {'name': item['lens_size__value'], 'count': item['count']}
        #             for item in lens_sizes_data
        #         ],
        #         'lighting': [
        #             {'name': item['lighting__value'], 'count': item['count']}
        #             for item in lighting_data
        #         ],
        #         'lighting_types': [
        #             {'name': item['lighting_type__value'], 'count': item['count']}
        #             for item in lighting_types_data
        #         ],
        #         'production_designers': [
        #             {'name': item['production_designer__value'], 'count': item['count']}
        #             for item in production_designers_data
        #         ],
        #         'sets': [
        #             {'name': item['setting__value'], 'count': item['count']}
        #             for item in sets_data
        #         ],
        #         'shot_times': [
        #             {'name': item['shot_time__value'], 'count': item['count']}
        #             for item in shot_times_data
        #         ],
        #         'shot_types': [
        #             {'name': item['shot_type__value'], 'count': item['count']}
        #             for item in shot_types_data
        #         ],
        #         'story_locations': [
        #             {'name': item['location__value'], 'count': item['count']}
        #             for item in story_locations_data
        #         ],
        #         'tags': tags_formatted,
        #         'time_periods': [
        #             {'name': item['time_period__value'], 'count': item['count']}
        #             for item in time_periods_data
        #         ],
        #         'time_of_day': [
        #             {'name': item['time_of_day__value'], 'count': item['count']}
        #             for item in time_of_day_data
        #         ],
        #     },
        #     'field_coverage': {
        #         'total_images': total_images,
        #         'actors_coverage': len(actors_data),
        #         'cameras_coverage': len(cameras_data),
        #         'directors_coverage': len(directors_data),
        #         'genres_coverage': len(genres_data),
        #         'tags_coverage': len(tags_formatted),
        #     },
        #     'crew_summary': {
        #         'production_designer': movie.production_designer if movie.production_designer else None,
        #         'costume_designer': movie.costume_designer if movie.costume_designer else None,
        #     }
        # }

        # return Response(response_data)



    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]



class BaseOptionViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'options']
    """
    Base ViewSet for option models with caching support.
    """
    filter_backends = [DjangoFilterBackend]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    def get_filter_type(self):
        """Get filter type for cache invalidation - override in subclasses"""
        return self.__class__.__name__.lower().replace('optionsviewset', '')

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # Invalidate cache after update
        filter_type = self.get_filter_type()
        invalidate_filter_cache(filter_type)
        return response

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        # Invalidate cache after partial update
        filter_type = self.get_filter_type()
        invalidate_filter_cache(filter_type)
        return response


class DirectorOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return DirectorOption.objects.all()
        except:
            return DirectorOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = DirectorOptionSerializer


class CinematographerOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return CinematographerOption.objects.all()
        except:
            return CinematographerOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = CinematographerOptionSerializer


class EditorOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return EditorOption.objects.all()
        except:
            return EditorOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = EditorOptionSerializer


class ColoristOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return ColoristOption.objects.all()
        except:
            return ColoristOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = ColoristOptionSerializer


class CostumeDesignerOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return CostumeDesignerOption.objects.all()
        except:
            return CostumeDesignerOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = CostumeDesignerOptionSerializer


class ProductionDesignerOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return ProductionDesignerOption.objects.all()
        except:
            return ProductionDesignerOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = ProductionDesignerOptionSerializer


class GenreOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return GenreOption.objects.all()
        except:
            # Return empty queryset that won't execute SQL
            return GenreOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            # Return empty response if database table doesn't exist
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = GenreOptionSerializer


class ColorOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return ColorOption.objects.all()
        except:
            # Return empty queryset that won't execute SQL
            return ColorOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            # Return empty response if database table doesn't exist
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = ColorOptionSerializer


class MediaTypeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return MediaTypeOption.objects.all()
        except:
            # Return empty queryset that won't execute SQL
            return MediaTypeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            # Return empty response if database table doesn't exist
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = MediaTypeOptionSerializer


class AspectRatioOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return AspectRatioOption.objects.all()
        except:
            return AspectRatioOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = AspectRatioOptionSerializer


class OpticalFormatOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return OpticalFormatOption.objects.all()
        except:
            return OpticalFormatOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = OpticalFormatOptionSerializer


class FormatOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return FormatOption.objects.all()
        except:
            return FormatOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = FormatOptionSerializer


class InteriorExteriorOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return InteriorExteriorOption.objects.all()
        except:
            return InteriorExteriorOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = InteriorExteriorOptionSerializer


class TimeOfDayOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return TimeOfDayOption.objects.all()
        except:
            return TimeOfDayOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = TimeOfDayOptionSerializer


class NumberOfPeopleOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return NumberOfPeopleOption.objects.all()
        except:
            return NumberOfPeopleOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = NumberOfPeopleOptionSerializer


class GenderOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return GenderOption.objects.all()
        except:
            return GenderOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = GenderOptionSerializer


class AgeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return AgeOption.objects.all()
        except:
            return AgeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = AgeOptionSerializer


class EthnicityOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return EthnicityOption.objects.all()
        except:
            return EthnicityOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = EthnicityOptionSerializer


class FrameSizeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return FrameSizeOption.objects.all()
        except:
            return FrameSizeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = FrameSizeOptionSerializer


class ShotTypeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return ShotTypeOption.objects.all()
        except:
            return ShotTypeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = ShotTypeOptionSerializer


class CompositionOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return CompositionOption.objects.all()
        except:
            return CompositionOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = CompositionOptionSerializer


class LensSizeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return LensSizeOption.objects.all()
        except:
            return LensSizeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = LensSizeOptionSerializer


class LensTypeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return LensTypeOption.objects.all()
        except:
            return LensTypeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = LensTypeOptionSerializer


class LightingOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return LightingOption.objects.all()
        except:
            return LightingOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = LightingOptionSerializer


class LightingTypeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return LightingTypeOption.objects.all()
        except:
            return LightingTypeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = LightingTypeOptionSerializer


class CameraTypeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return CameraTypeOption.objects.all()
        except:
            return CameraTypeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = CameraTypeOptionSerializer


class ResolutionOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return ResolutionOption.objects.all()
        except:
            return ResolutionOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = ResolutionOptionSerializer


class FrameRateOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return FrameRateOption.objects.all()
        except:
            return FrameRateOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = FrameRateOptionSerializer


class MovieOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return MovieOption.objects.all()
        except:
            return MovieOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = MovieOptionSerializer


class ActorOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return ActorOption.objects.all()
        except:
            return ActorOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = ActorOptionSerializer


class CameraOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return CameraOption.objects.all()
        except:
            return CameraOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = CameraOptionSerializer


class LensOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return LensOption.objects.all()
        except:
            return LensOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = LensOptionSerializer


class LocationOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return LocationOption.objects.all()
        except:
            return LocationOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = LocationOptionSerializer


class SettingOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return SettingOption.objects.all()
        except:
            return SettingOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = SettingOptionSerializer


class FilmStockOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return FilmStockOption.objects.all()
        except:
            return FilmStockOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = FilmStockOptionSerializer


class ShotTimeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return ShotTimeOption.objects.all()
        except:
            return ShotTimeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = ShotTimeOptionSerializer


class DescriptionOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return DescriptionOption.objects.all()
        except:
            return DescriptionOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = DescriptionOptionSerializer


class VfxBackingOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return VfxBackingOption.objects.all()
        except:
            return VfxBackingOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = VfxBackingOptionSerializer


# New ViewSets for additional filters
class ShadeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return ShadeOption.objects.all()
        except:
            return ShadeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = ShadeOptionSerializer


class ArtistOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return ArtistOption.objects.all()
        except:
            return ArtistOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = ArtistOptionSerializer


class FilmingLocationOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return FilmingLocationOption.objects.all()
        except:
            return FilmingLocationOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = FilmingLocationOptionSerializer


class LocationTypeOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return LocationTypeOption.objects.all()
        except:
            return LocationTypeOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = LocationTypeOptionSerializer


class MovieViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for managing movies with optimized performance - READ ONLY
    """
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MovieFilter
    lookup_field = 'slug'

    def get_queryset(self):
        """Optimized queryset with dynamic field selection for better performance"""
        queryset = super().get_queryset()

        # Movie model doesn't have heavy color analysis fields, so no defer needed

        # Optimize ordering based on available fields
        ordering = self.request.query_params.get('ordering', '-year')
        if ordering in ['-year', 'year', 'title', '-title']:
            queryset = queryset.order_by(ordering)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return MovieSerializer  # Use full serializer for now
        return MovieSerializer  # Full serializer for detail views

    def retrieve(self, request, *args, **kwargs):
        """
        Get detailed movie information with related images and statistics.
        """
        movie = self.get_object()

        # Get all images for this movie with optimized queries
        images = movie.images.select_related(
            'movie', 'director', 'cinematographer', 'shot_type', 'lighting', 'color'
        ).prefetch_related('genre', 'tags')[:20]  # Limit to 20 images for performance

        # Serialize movie data
        movie_serializer = self.get_serializer(movie)

        # Serialize images data
        from .serializers import ImageListSerializer
        images_serializer = ImageListSerializer(images, many=True, context={'request': request})

        # Calculate basic statistics
        total_images = movie.images.count()

        response_data = {
            'success': True,
            'movie': movie_serializer.data,
            'images': images_serializer.data,
            'statistics': {
                'total_images': total_images,
                'images_shown': len(images_serializer.data)
            }
        }

        return Response(response_data)

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]


class TagViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for managing tags with optimized performance - READ ONLY
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TagFilter
    lookup_field = 'slug'

    def get_queryset(self):
        """Optimized queryset with dynamic field selection for better performance"""
        queryset = super().get_queryset()

        # Optimize ordering based on available fields
        ordering = self.request.query_params.get('ordering', 'name')
        if ordering in ['name', '-name']:
            queryset = queryset.order_by(ordering)

        return queryset

    def list(self, request, *args, **kwargs):
        """Disable list endpoint - return 404"""
        from rest_framework.response import Response
        return Response({"error": "Tags list endpoint is not available"}, status=404)

    def retrieve(self, request, *args, **kwargs):
        """
        Get detailed tag information including usage statistics.
        Returns tag data, a small sample of images using the tag, and statistics:
          - total_images: total number of images with this tag
          - movies_count: distinct movies represented in those images
          - top_cooccurring_tags: other tags that co-occur with this tag (id, slug, name, count)
          - top_colors: distribution of colors for images with this tag (color id, value, count)
        """
        tag = self.get_object()

        # Sample images for this tag (limit for performance)
        images_qs = tag.images.select_related('movie', 'color', 'media_type').prefetch_related('tags')[:20]
        images_serializer = MovieImageSerializer(images_qs, many=True, context={'request': request})

        # Basic counts
        total_images = tag.images.count()
        movies_count = tag.images.filter(movie__isnull=False).values('movie').distinct().count()

        # Top co-occurring tags (other tags that appear on images that have this tag)
        co_tags_qs = (
            Tag.objects
            .filter(images__in=tag.images.all())
            .exclude(id=tag.id)
            .annotate(count=Count('images'))
            .order_by('-count')[:10]
        )
        top_cooccurring_tags = [
            {'id': t.id, 'slug': t.slug, 'name': t.name, 'count': t.count}
            for t in co_tags_qs
        ]

        # Top colors for images with this tag
        top_colors_qs = (
            tag.images
            .filter(color__isnull=False)
            .values('color__id', 'color__value')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        top_colors = [
            {'id': c['color__id'], 'value': c['color__value'], 'count': c['count']}
            for c in top_colors_qs
        ]

        tag_serializer = TagSerializer(tag)

        response_data = {
            'success': True,
            'tag': tag_serializer.data,
            'images': images_serializer.data,
            'statistics': {
                'total_images': total_images,
                'images_shown': len(images_serializer.data),
                'movies_count': movies_count,
                'top_cooccurring_tags': top_cooccurring_tags,
                'top_colors': top_colors,
            }
        }

        return Response(response_data)

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]


class YearOptionViewSet(BaseOptionViewSet):
    def get_queryset(self):
        try:
            return YearOption.objects.all()
        except:
            return YearOption.objects.filter(pk__in=[])

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except:
            from rest_framework.response import Response
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    serializer_class = YearOptionSerializer


# Helper function to create selectable options from database
def create_options_from_db(queryset):
    """Convert database queryset to list of selectable option objects"""
    return [{"value": obj.value, "label": obj.value} for obj in queryset.order_by('display_order')]


class FiltersView(APIView):
    """
    API endpoint to retrieve all available filter options for images
    Returns filter configuration with options from database
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        Return filter configuration with options, or search images by filters if parameters provided
        """
        try:
            # Get query parameters safely
            query_params = getattr(request, 'query_params', request.GET)
            
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"FiltersView GET request with query_params: {dict(query_params)}")
            
            # Check if any search/filter parameters are provided
            search_params = {
                'search': query_params.get('search'),
                'tags': query_params.get('tags'),
                'movie': query_params.get('movie'),
                'actor': query_params.get('actor'),
                'camera': query_params.get('camera'),
                'lens': query_params.get('lens'),
                'location': query_params.get('location'),
                'setting': query_params.get('setting'),
                'film_stock': query_params.get('film_stock'),
                'shot_time': query_params.get('shot_time'),
                'description': query_params.get('description'),
                'vfx_backing': query_params.get('vfx_backing'),
                'media_type': query_params.get('media_type'),
                'genre': query_params.get('genre'),
                'time_period': query_params.get('time_period'),
                'color': query_params.get('color'),
                'shade': query_params.get('shade'),
                'aspect_ratio': query_params.get('aspect_ratio'),
                'optical_format': query_params.get('optical_format'),
                'lab_process': query_params.get('lab_process'),
                'format': query_params.get('format'),
                'interior_exterior': query_params.get('interior_exterior'),
                'time_of_day': query_params.get('time_of_day'),
                'number_of_people': query_params.get('number_of_people'),
                'gender': query_params.get('gender'),
                'age': query_params.get('age'),
                'ethnicity': query_params.get('ethnicity'),
                'frame_size': query_params.get('frame_size'),
                'shot_type': query_params.get('shot_type'),
                'composition': query_params.get('composition'),
                'lens_type': query_params.get('lens_type'),
                'lighting': query_params.get('lighting'),
                'lighting_type': query_params.get('lighting_type'),
                'director': query_params.get('director'),
                'cinematographer': query_params.get('cinematographer'),
                'editor': query_params.get('editor'),
                'costume_designer': query_params.get('costume_designer'),
                'production_designer': query_params.get('production_designer'),
                'colorist': query_params.get('colorist'),
                'artist': query_params.get('artist'),
                'filming_location': query_params.get('filming_location'),
                'location_type': query_params.get('location_type'),
                'year': query_params.get('year'),
                'frame_rate': query_params.get('frame_rate'),
                'lens_size': query_params.get('lens_size'),
                'resolution': query_params.get('resolution'),
                'description_filter': query_params.get('description_filter'),
                'limit': int(query_params.get('limit', 20)),
                'offset': int(query_params.get('offset', 0))
            }

            # Remove None values and check if any filters are applied
            applied_filters = {k: v for k, v in search_params.items() if v is not None and k not in ['limit', 'offset']}
            has_filters = len(applied_filters) > 0

            # If no meaningful filter parameters provided, return filter configuration
            # Check for actual filter parameters (not just defaults)
            filter_param_keys = ['search', 'tags', 'movie', 'actor', 'camera', 'lens', 'location', 'setting',
                               'film_stock', 'shot_time', 'description', 'vfx_backing', 'media_type', 'genre',
                               'time_period', 'color', 'shade', 'aspect_ratio', 'optical_format', 'lab_process',
                               'format', 'interior_exterior', 'time_of_day', 'number_of_people', 'gender', 'age',
                               'ethnicity', 'frame_size', 'shot_type', 'composition', 'lens_type', 'lighting',
                               'lighting_type', 'director', 'cinematographer', 'editor', 'colorist', 'costume_designer',
                               'production_designer', 'artist', 'filming_location', 'location_type', 'year',
                               'frame_rate', 'lens_size', 'resolution', 'description_filter']

            has_filter_params = any(query_params.get(key) for key in filter_param_keys)
            if not has_filter_params:
                return self._get_filter_configuration_with_options()

            # If filters are provided, perform filtered search
            return self._perform_filtered_search(search_params, applied_filters, request)

        except Exception as e:
            logger.error(f"Error in filters/search operation: {e}")
            return Response({
                'success': False,
                'count': 0,
                'results': [],
                'message': 'Error processing request',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_filter_configuration_with_options(self):
        """Get filter configuration with options and working/empty status"""
        try:
            # Get filter options from database using cached function
            filters_data = get_all_cached_filters()

            # Convert to the expected format
            filter_options = {}
            entity_slugs = {}

            for filter_name, options_list in filters_data.items():
                if options_list:
                    if filter_name.endswith('_slugs'):
                        # Handle slug fields separately
                        entity_slugs[filter_name] = options_list
                    else:
                        # Extract values from option objects, preserving the order from cache
                        values = [opt.get('value', str(opt)) for opt in options_list if opt]
                        filter_options[filter_name] = [{"value": v, "label": v} for v in values]  # No limit on options

            # Single-select dropdown filters with pre-existing options (no checkboxes, no typing)
            shotdeck_filters = [
                {
                    "id": "search",
                    "label": "Search",
                    "type": "text",
                    "placeholder": "Search titles and descriptions...",
                    "options": []
                },
                {
                    "id": "media_type",
                    "label": "Media Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('media_type', [])]
                },
                {
                    "id": "genre",
                    "label": "Genre",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('genre', [])]
                },
                {
                    "id": "color",
                    "label": "Color",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('color', [])]
                },
                {
                    "id": "aspect_ratio",
                    "label": "Aspect Ratio",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('aspect_ratio', [])]
                },
                {
                    "id": "optical_format",
                    "label": "Optical Format",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('optical_format', [])]
                },
                {
                    "id": "format",
                    "label": "Format",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('format', [])]
                },
                {
                    "id": "time_period",
                    "label": "Time Period",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('time_period', [])]
                },
                {
                    "id": "interior_exterior",
                    "label": "Interior/Exterior",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('interior_exterior', [])]
                },
                {
                    "id": "time_of_day",
                    "label": "Time of Day",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('time_of_day', [])]
                },
                {
                    "id": "lighting",
                    "label": "Lighting",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lighting', [])]
                },
                {
                    "id": "lighting_type",
                    "label": "Lighting Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lighting_type', [])]
                },
                {
                    "id": "shot_type",
                    "label": "Shot Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('shot_type', [])]
                },
                {
                    "id": "composition",
                    "label": "Composition",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('composition', [])]
                },
                {
                    "id": "lens_type",
                    "label": "Lens Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lens_type', [])]
                },
                {
                    "id": "camera_type",
                    "label": "Camera Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('camera_type', [])]
                },
                {
                    "id": "gender",
                    "label": "Gender",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('gender', [])]
                },
                {
                    "id": "age",
                    "label": "Age",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('age', [])]
                },
                {
                    "id": "ethnicity",
                    "label": "Ethnicity",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('ethnicity', [])]
                },
                {
                    "id": "frame_size",
                    "label": "Frame Size",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('frame_size', [])]
                },
                {
                    "id": "number_of_people",
                    "label": "Number of People",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('number_of_people', [])]
                },
                {
                    "id": "actor",
                    "label": "Actor",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('actor', [])]
                },
                {
                    "id": "camera",
                    "label": "Camera",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('camera', [])]
                },
                {
                    "id": "lens",
                    "label": "Lens",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lens', [])]
                },
                {
                    "id": "location",
                    "label": "Location",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('location', [])]
                },
                {
                    "id": "setting",
                    "label": "Setting",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('setting', [])]
                },
                {
                    "id": "director",
                    "label": "Director",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('director', [])]
                },
                {
                    "id": "cinematographer",
                    "label": "Cinematographer",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('cinematographer', [])]
                },
                {
                    "id": "editor",
                    "label": "Editor",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('editor', [])]
                },
                {
                    "id": "year",
                    "label": "Year",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('year', [])]
                },
                {
                    "id": "movie",
                    "label": "Movie",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('movie', [])]
                },
                {
                    "id": "shade",
                    "label": "Shade",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('shade', [])]
                },
                {
                    "id": "filming_location",
                    "label": "Filming Location",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('filming_location', [])]
                },
                {
                    "id": "location_type",
                    "label": "Location Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('location_type', [])]
                },
                {
                    "id": "costume_designer",
                    "label": "Costume Designer",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('costume_designer', [])]
                },
                {
                    "id": "production_designer",
                    "label": "Production Designer",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('production_designer', [])]
                },
                {
                    "id": "colorist",
                    "label": "Colorist",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('colorist', [])]
                },
                {
                    "id": "film_stock",
                    "label": "Film Stock",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('film_stock', [])]
                },
                {
                    "id": "artist",
                    "label": "Artist",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('artist', [])]
                }
            ]

            # Get the original filter options data to check which filters actually have data
            original_filters_data = get_all_cached_filters()

            # Check which filters have data and mark them accordingly
            working_filters = []
            empty_filters = []

            for filter_item in shotdeck_filters:
                filter_id = filter_item.get('id')

                # Special case for search (text input, always available)
                if filter_id == 'search':
                    working_filters.append(filter_id)
                    filter_item['disabled'] = False
                    filter_item['disabled_reason'] = None
                    continue

                # For dropdown filters, check if they exist in the original cached data
                has_data_in_cache = filter_id in original_filters_data and bool(original_filters_data[filter_id])

                if has_data_in_cache:
                    working_filters.append(filter_id)
                    filter_item['disabled'] = False
                    filter_item['disabled_reason'] = None
                else:
                    empty_filters.append(filter_id)
                    filter_item['disabled'] = True
                    filter_item['disabled_reason'] = 'No data available for this filter'

            response_data = {
                'success': True,
                'data': {
                    'filters': shotdeck_filters,
                    'working_filters': working_filters,
                    'empty_filters': empty_filters,
                    'working_filters_count': len(working_filters),
                    'empty_filters_count': len(empty_filters)
                },
                'smart_filtering': {
                    'enabled': True,
                    'working_filters_count': len(working_filters),
                    'empty_filters_count': len(empty_filters)
                }
            }

            return Response(response_data)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting filter configuration: {e}")
            return Response({
                'success': False,
                'error': str(e),
                'data': {'filters': [], 'working_filters': [], 'empty_filters': []}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_filter_configuration(self):
        """Get filter configuration from database instead of file-based system"""
        try:
            # Get filter options from database using cached function
            filters_data = get_all_cached_filters()

            # Convert to the expected format
            filter_options = {}
            entity_slugs = {}

            for filter_name, options_list in filters_data.items():
                if options_list:
                    if filter_name.endswith('_slugs'):
                        # Handle slug fields separately
                        entity_slugs[filter_name] = options_list
                    else:
                        # Extract values from option objects, preserving the order from cache
                        values = [opt.get('value', str(opt)) for opt in options_list if opt]
                        filter_options[filter_name] = [{"value": v, "label": v} for v in values]  # No limit on options

            # Single-select dropdown filters with pre-existing options (no checkboxes, no typing)
            shotdeck_filters = [
                {
                    "id": "search",
                        "label": "Search",
                    "type": "text",
                    "placeholder": "Search titles and descriptions...",
                    "options": []
                },
                {
                    "id": "media_type",
                    "label": "Media Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('media_type', [])]
                },
                {
                    "id": "genre",
                        "label": "Genre",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('genre', [])]
                },
                {
                    "id": "color",
                    "label": "Color",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('color', [])]
                },
                {
                    "id": "aspect_ratio",
                    "label": "Aspect Ratio",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('aspect_ratio', [])]
                },
                {
                    "id": "optical_format",
                    "label": "Optical Format",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('optical_format', [])]
                },
                {
                    "id": "format",
                    "label": "Film Format",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('format', [])]
                },
                {
                    "id": "time_period",
                    "label": "Time Period",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('time_period', [])]
                },
                {
                    "id": "interior_exterior",
                    "label": "Interior/Exterior",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('interior_exterior', [])]
                },
                {
                    "id": "time_of_day",
                    "label": "Time of Day",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('time_of_day', [])]
                },
                {
                    "id": "lighting",
                        "label": "Lighting",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lighting', [])]
                },
                {
                    "id": "lighting_type",
                    "label": "Lighting Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lighting_type', [])]
                },
                {
                    "id": "shot_type",
                    "label": "Shot Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('shot_type', [])]
                },
                {
                    "id": "composition",
                    "label": "Composition",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('composition', [])]
                },
                {
                    "id": "lens_type",
                    "label": "Lens Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lens_type', [])]
                },
                {
                    "id": "camera_type",
                    "label": "Camera Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('camera_type', [])]
                },
                {
                    "id": "gender",
                    "label": "Gender",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('gender', [])]
                },
                {
                    "id": "age",
                    "label": "Age",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('age', [])]
                },
                {
                    "id": "ethnicity",
                    "label": "Ethnicity",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('ethnicity', [])]
                },
                {
                    "id": "frame_size",
                    "label": "Frame Size",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('frame_size', [])]
                },
                {
                    "id": "number_of_people",
                    "label": "Number of People",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('number_of_people', [])]
                },
                {
                    "id": "actor",
                    "label": "Actor",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('actor', [])]
                },
                {
                    "id": "camera",
                    "label": "Camera",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('camera', [])]
                },
                {
                    "id": "lens",
                    "label": "Lens",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lens', [])]
                },
                {
                    "id": "location",
                    "label": "Location",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('location', [])]
                },
                {
                    "id": "setting",
                    "label": "Setting",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('setting', [])]
                },
                {
                    "id": "director",
                    "label": "Director",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('director', [])]
                },
                {
                    "id": "cinematographer",
                    "label": "Cinematographer",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('cinematographer', [])]
                },
                {
                    "id": "editor",
                    "label": "Editor",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('editor', [])]
                },
                {
                    "id": "year",
                    "label": "Year",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('year', [])]
                },
                {
                    "id": "movie",
                    "label": "Movie",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('movie', [])]
                },
                {
                    "id": "shade",
                    "label": "Shade",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('shade', [])]
                },
                {
                    "id": "filming_location",
                    "label": "Filming Location",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('filming_location', [])]
                },
                {
                    "id": "location_type",
                    "label": "Location Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('location_type', [])]
                },
                {
                    "id": "costume_designer",
                    "label": "Costume Designer",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('costume_designer', [])]
                },
                {
                    "id": "production_designer",
                    "label": "Production Designer",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('production_designer', [])]
                },
                {
                    "id": "colorist",
                    "label": "Colorist",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('colorist', [])]
                },
                {
                    "id": "film_stock",
                    "label": "Film Stock",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('film_stock', [])]
                },
                {
                    "id": "music video",
                    "label": "Music Video",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('music video', [])]
                },
                {
                    "id": "artist",
                    "label": "Artist",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('artist', [])]
                },
                {
                    "id": "tv",
                    "label": "TV",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('tv', [])]
                },
                {
                    "id": "resolution",
                    "label": "Resolution",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('resolution', [])]
                },
                {
                    "id": "frame_rate",
                    "label": "Frame Rate",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('frame_rate', [])]
                },
                {
                    "id": "lens_size",
                    "label": "Lens Size",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lens_size', [])]
                }
            ]


            return {
                "filters": shotdeck_filters,
                "entity_slugs": entity_slugs,
                "source": "database",
                "message": "ShotDeck-style dropdown filters loaded from database"
            }

        except Exception as e:
            # Fallback to empty filters if file system fails
            return {
                "filters": [
                    {
                        "filter": "search",
                        "options": [],
                        "label": "Search",
                        "format": "Text",
                        "type": "text"
                    }
                ],
                "error": f"Could not load filters from file system: {str(e)}",
                "source": "file-based-fallback"
            }

    def _perform_filtered_search(self, search_params, applied_filters, request):
        """
        Perform search based on applied filters using database and ImageFilter
        Implements smart filtering to skip filters with no matching data
        Falls back to JSON-based search if database is unavailable
        """
        try:
            from apps.images.filters import ImageFilter

            # Build queryset using ImageFilter
            queryset = Image.objects.all()

            # SMART FILTERING: Remove filters that would result in zero results
            smart_filtered_params = search_params.copy()
            removed_filters = []

            # Test each filter individually and remove those with no results
            for filter_name, filter_value in search_params.items():
                if filter_name in ['limit', 'offset', 'search'] or not filter_value:  # Don't test search filter
                    continue

                try:
                    # Test if this filter alone has any results
                    test_params = {filter_name: filter_value}
                    test_filterset = ImageFilter(data=test_params, queryset=queryset)

                    if test_filterset.is_valid():
                        test_count = test_filterset.qs.count()
                        if test_count == 0:
                            # This filter has no matching data, remove it
                            smart_filtered_params.pop(filter_name, None)
                            removed_filters.append(filter_name)
                    else:
                        # Invalid filter, remove it
                        smart_filtered_params.pop(filter_name, None)
                        removed_filters.append(filter_name)
                except Exception as e:
                    # If testing this filter causes an exception, remove it
                    logger.warning(f"Error testing filter {filter_name}={filter_value}: {e}")
                    smart_filtered_params.pop(filter_name, None)
                    removed_filters.append(filter_name)

            # Check if smart filtering removed all filters (prevent 500 error)
            active_filters = [k for k in smart_filtered_params.keys() if k not in ['limit', 'offset']]
            if not active_filters:
                # When all filters are removed, return all images
                filtered_queryset = queryset
                total_count = filtered_queryset.count()

                # Apply pagination
                limit = min(int(search_params.get('limit', 20)), 100)
                offset = int(search_params.get('offset', 0))
                paginated_results = filtered_queryset[offset:offset + limit]

                serializer = ImageSerializer(paginated_results, many=True, context={'request': request})

                active_filters = []
                smart_filtering_info = {
                    'enabled': True,
                    'description': 'Smart filtering automatically skipped filters with no matching data',
                    'removed_filters': removed_filters,
                    'active_filters': active_filters,
                    'note': 'All filters were removed - showing all images'
                }

                return Response({
                    'success': True,
                    'count': total_count,
                    'results': serializer.data,
                    'total': total_count,
                    'filters_applied': {},  # No filters were actually applied
                    'smart_filtering': smart_filtering_info,
                    'message': f'Smart filtering removed all filters (showing all {total_count} images)',
                    'source': 'database'
                })

            # Create final filter instance with smart-filtered parameters
            filterset = ImageFilter(data=smart_filtered_params, queryset=queryset)

            # Check if filters are valid
            if not filterset.is_valid():
                return Response({
                    'success': False,
                    'message': 'Invalid filter parameters',
                    'errors': filterset.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # Apply smart-filtered filters
            filtered_queryset = filterset.qs

            # Apply pagination
            limit = min(int(search_params.get('limit', 20)), 100)  # Max 100 results
            offset = int(search_params.get('offset', 0))

            # Get total count before pagination
            total_count = filtered_queryset.count()

            # Apply pagination
            paginated_results = filtered_queryset[offset:offset + limit]

            # Serialize results
            serializer = ImageSerializer(paginated_results, many=True, context={'request': request})

            # Ensure count and total are never null/empty - always valid integers
            page_count = len(serializer.data)
            total_count = int(total_count) if total_count is not None else 0

            # Prepare smart filtering info
            active_filters = [k for k in smart_filtered_params.keys() if k not in ['limit', 'offset']]
            smart_filtering_info = {
                'enabled': True,
                'description': 'Smart filtering automatically skipped filters with no matching data',
                'removed_filters': removed_filters,
                'active_filters': active_filters,
                'note': 'You can select options from ALL categories - the system intelligently uses filters with data'
            }

            # Update applied_filters to reflect the smart-filtered active filters
            final_applied_filters = {k: smart_filtered_params[k] for k in active_filters}

            return Response({
                'success': True,
                'count': total_count,  # Total count of all matching results
                'results': serializer.data,  # Current page results
                'total': total_count,  # Alias for backward compatibility
                'filters_applied': final_applied_filters,
                'smart_filtering': smart_filtering_info,
                'message': f'Image search completed with smart filtering (removed {len(removed_filters)} empty filters)',
                'source': 'database'
            })

        except Exception as e:
            logger.error(f"Error performing database search: {e}")
            logger.info("Falling back to JSON-based search")

            # Fall back to JSON-based search
            return self._perform_json_fallback_search(search_params, applied_filters, request)

    def _perform_json_fallback_search(self, search_params, applied_filters, request):
        """
        Perform search using JSON data when database is unavailable
        """
        try:
            import json
            import os
            from pathlib import Path

            # Path to JSON data - use backup file in project directory
            json_path = Path(settings.BASE_DIR) / 'images_only_backup.json'
            if not json_path.exists():
                return Response({
                    'success': False,
                    'message': 'JSON data not found',
                    'error': f'Path {json_path} does not exist',
                    'source': 'json-fallback-error'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Use the single backup file
            json_files = [json_path]

            # Search through JSON files for matching entries
            matching_results = []
            total_found = 0

            limit = min(int(search_params.get('limit', 20)), 100)
            offset = int(search_params.get('offset', 0))

            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data_list = json.load(f)

                    # Handle both single objects and lists
                    if isinstance(data_list, list):
                        items_to_process = data_list
                    else:
                        items_to_process = [data_list]

                    for data in items_to_process:
                        # Check if this entry matches the filters
                        if self._matches_filters(data, applied_filters):
                            # Format as image result
                            image_data = self._format_json_as_image(data, json_file.name)
                            matching_results.append(image_data)
                            total_found += 1

                            # Stop if we have enough results
                            if len(matching_results) >= (limit + offset):
                                break

                        # Break out of inner loop if we have enough results
                        if len(matching_results) >= (limit + offset):
                            break

                except Exception as e:
                    logger.warning(f"Error processing {json_file}: {e}")
                    continue

            # Apply pagination
            paginated_results = matching_results[offset:offset + limit]

            return Response({
                'success': True,
                'count': total_found,  # Total count of all matching results
                'results': paginated_results,  # Current page results
                'total': total_found,  # Alias for backward compatibility
                'filters_applied': applied_filters,
                'smart_filtering': {
                    'enabled': True,
                    'description': 'JSON fallback search - filters applied directly to JSON data',
                    'note': 'Database unavailable, using JSON data for search results'
                },
                'message': 'Image search completed from JSON data',
                'source': 'json-fallback'
            })

        except Exception as e:
            logger.error(f"Error performing JSON fallback search: {e}")
            return Response({
                'success': False,
                'count': 0,
                'results': [],
                'message': 'Error performing JSON search',
                'error': str(e),
                'source': 'json-fallback-error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _matches_filters(self, data, applied_filters):
        """
        Check if JSON data matches the applied filters
        """
        if not applied_filters:
            return True

        # Extract relevant fields from JSON data
        json_filters = self._extract_filters_from_json(data)

        # Check each applied filter
        for filter_name, filter_value in applied_filters.items():
            if filter_name in json_filters:
                json_value = json_filters[filter_name]
                # Case-insensitive partial match
                if isinstance(json_value, list):
                    if not any(str(filter_value).lower() in str(v).lower() for v in json_value):
                        return False
                else:
                    if str(filter_value).lower() not in str(json_value).lower():
                        return False
            else:
                # If filter not present in JSON, consider it a match for smart filtering
                continue

        return True

    def _extract_filters_from_json(self, data):
        """
        Extract filter values from JSON data structure (Django fixture format)
        """
        filters = {}

        # Handle Django fixture format where data is in 'fields'
        if 'fields' in data:
            fields = data['fields']

            # Map fields to search filters
            filter_mappings = {
                'search': ['title', 'description'],
                'tags': ['tags'],
                'movie': ['movie'],
                'actor': ['actor'],
                'camera': ['camera'],
                'lens': ['lens'],
                'location': ['location', 'filming_location'],
                'setting': ['setting'],
                'film_stock': ['film_stock'],
                'shot_time': ['shot_time'],
                'description': ['description'],
                'vfx_backing': ['vfx_backing'],
                'media_type': ['media_type'],
                'genre': ['genre'],
                'time_period': ['time_period'],
                'color': ['color'],
                'shade': ['shade'],
                'aspect_ratio': ['aspect_ratio'],
                'optical_format': ['optical_format'],
                'lab_process': ['lab_process'],
                'format': ['format'],
                'interior_exterior': ['interior_exterior'],
                'time_of_day': ['time_of_day'],
                'number_of_people': ['number_of_people'],
                'gender': ['gender'],
                'ethnicity': ['ethnicity'],
                'frame_size': ['frame_size'],
                'shot_type': ['shot_type'],
                'composition': ['composition'],
                'lens_type': ['lens_type'],
                'lighting': ['lighting'],
                'lighting_type': ['lighting_type'],
                'director': ['director'],
                'cinematographer': ['cinematographer'],
                'editor': ['editor']
            }

            for filter_name, possible_keys in filter_mappings.items():
                for key in possible_keys:
                    if key in fields and fields[key] is not None:
                        if isinstance(fields[key], list):
                            filters[filter_name] = fields[key]
                        else:
                            filters[filter_name] = str(fields[key])
                        break

        return filters

    def _format_json_as_image(self, data, filename):
        """
        Format JSON data as an image result (Django fixture format)
        """
        fields = data.get('fields', {})

        # Get title from fields
        title = fields.get('title', 'Unknown Title')

        # Use slug as ID if available, otherwise use pk
        image_id = fields.get('slug', str(data.get('pk', 'unknown')))

        # Use image_url from fields
        image_url = fields.get('image_url', f"/media/{image_id}.jpg")

        return {
            'id': image_id,
            'title': title,
            'image_url': image_url,
            'year': fields.get('year', fields.get('release_year', '')),
            'media_type': fields.get('media_type', ''),
            'description': fields.get('description', ''),
            'filters': self._extract_filters_from_json(data)
        }

    def _generate_mock_search_results(self, search_params, applied_filters):
        """
        Generate mock search results for testing
        """
        # This is a placeholder - in real implementation this would query actual images
        return [
            {
                'id': 1,
                'title': 'Sample Image 1',
                'image_url': 'https://example.com/image1.jpg',
                'filters_matched': applied_filters
            },
            {
                'id': 2,
                'title': 'Sample Image 2',
                'image_url': 'https://example.com/image2.jpg',
                'filters_matched': applied_filters
            }
        ]


