# Path: /image_service/apps/images/api/views.py
from apps.images.filters import ImageFilter, MovieFilter, TagFilter
import logging
import time
import math
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from django.utils.text import slugify

from apps.images.models import (
    Image, Movie, Tag, BaseOption,
    GenreOption, ColorOption, MediaTypeOption, AspectRatioOption,
    OpticalFormatOption, FormatOption, TimePeriodOption, LabProcessOption,
    InteriorExteriorOption, TimeOfDayOption, NumberOfPeopleOption, GenderOption,
    AgeOption, EthnicityOption, FrameSizeOption, ShotTypeOption, CompositionOption,
    LensSizeOption, LensTypeOption, LightingOption, LightingTypeOption, CameraTypeOption,
    ResolutionOption, FrameRateOption, MovieOption, ActorOption, CameraOption,
    LensOption, LocationOption, SettingOption, FilmStockOption, ShotTimeOption,
    DescriptionOption, VfxBackingOption, ShadeOption, ArtistOption,
    FilmingLocationOption, LocationTypeOption, YearOption, ColoristOption,
    CostumeDesignerOption, ProductionDesignerOption, DirectorOption,
    CinematographerOption, EditorOption
)

from .serializers import (
    ImageSerializer, MovieImageSerializer, ImageListSerializer, MovieSerializer, TagSerializer,
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
    ShadeOptionSerializer, ArtistOptionSerializer, FilmingLocationOptionSerializer,
    LocationTypeOptionSerializer, YearOptionSerializer, FiltersResponseSerializer
)

from messaging.producers import send_event
from apps.common.serializers import Error401Serializer, Error403Serializer, Error404Serializer
from apps.images.cache_utils import get_cached_filter_options, get_all_cached_filters, invalidate_filter_cache
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Health check endpoint for the image service"""
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            image_count = Image.objects.count()
            return Response({
                "status": "healthy",
                "database": "connected",
                "image_count": image_count,
                "timestamp": timezone.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return Response(
                {"status": "unhealthy", "error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


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
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ImageFilter
    lookup_field = 'slug'

    # FIX 1: Add a default ordering to the viewset. This prevents the pagination
    # from trying to order by a non-existent 'id' field.
    # We use '-created_at' to show the newest images first.
    ordering = ['-created_at']

    def get_queryset(self):
        # Optimized querysets based on the request action (list vs. retrieve)
        if self.action == 'list':
            # FIX 2: Changed '.only('id', ...)' to '.only('id', ...)' to match the model field name.
            # Also removed the complex caching from here as it's better handled at a higher level if needed.
            # The 'created_at' field is included for the default ordering.
            return Image.objects.only(
                'id', 'slug', 'title', 'image_url', 'created_at',
                'movie__title', 'movie__year', 'director__value', 'cinematographer__value'
            ).select_related('movie', 'director', 'cinematographer')
        
        if self.action == 'retrieve':
            return Image.objects.select_related(
                'movie', 'actor', 'camera', 'cinematographer', 'director', 'lens', 'film_stock',
                'setting', 'location', 'filming_location', 'aspect_ratio', 'time_period',
                'time_of_day', 'interior_exterior', 'number_of_people', 'gender', 'age',
                'ethnicity', 'frame_size', 'shot_type', 'composition', 'lens_type',
                'lighting', 'lighting_type', 'camera_type', 'resolution', 'frame_rate',
                'vfx_backing', 'shade', 'artist', 'location_type', 'media_type', 'color',
                'optical_format', 'format', 'lab_process'
            ).prefetch_related('tags', 'genre')
        
        # Fallback for any other actions.
        return super().get_queryset()

    def filter_queryset(self, queryset):
        start_time = time.time()
        filtered = super().filter_queryset(queryset)
        applied = dict(self.request.query_params.lists())

        filter_instance = self.filterset_class(data=self.request.query_params, queryset=filtered)
        if hasattr(filter_instance, 'optimize_filter_query'):
            filtered = filter_instance.optimize_filter_query(filtered, applied)

        duration = time.time() - start_time
        if duration > 0.1:
            logger.info(f"Slow filter query: {self.request.query_params} took {duration:.3f}s, {filtered.count()} results")
        return filtered

    def get_serializer_class(self):
        return ImageListSerializer if self.action == 'list' else ImageSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        try:
            # FIX 3: Changed 'serializer.instance.id' to 'serializer.instance.id'
            send_event('image_created', {
                'image_id': serializer.instance.id,
                'title': serializer.instance.title,
                'movie_slug': serializer.instance.movie.slug if serializer.instance.movie else None,
            })
        except Exception as e:
            logger.warning(f"Failed to send image_created event: {e}")
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=self.get_success_headers(serializer.data))

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        invalidate_filter_cache('image')
        return response

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        invalidate_filter_cache('image')
        return response

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_value = self.kwargs.get(self.lookup_field)

        if lookup_value:
            try:
                return queryset.get(slug=lookup_value)
            except Image.DoesNotExist:
                normalized = slugify(lookup_value)
                if normalized:
                    title_guess = normalized.replace('-', ' ')
                    fallback = (
                        Image.objects.only('id', 'slug', 'title')
                        .filter(title__iexact=title_guess)
                        .first()
                    )
                    if fallback:
                        self.kwargs[self.lookup_field] = fallback.slug
                        return super().get_object()
        return super().get_object()

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        serializer = self.get_serializer(image)
        return Response({'success': True, 'data': serializer.data})

    def list(self, request, *args, **kwargs):
        try:
            start_time = time.time()
            queryset = self.filter_queryset(self.get_queryset())

            base_page_size = 20
            filtered_page_size = 15

            non_pagination_params = {
                key: value for key, value in request.query_params.items()
                if key not in {'page', 'page_size', 'ordering'}
            }
            has_filters = any(value for value in non_pagination_params.values())

            try:
                requested_page_size = int(request.query_params.get('page_size'))
            except (TypeError, ValueError):
                requested_page_size = None

            default_page_size = filtered_page_size if has_filters else base_page_size
            if requested_page_size and requested_page_size > 0:
                page_size = min(max(1, requested_page_size), default_page_size)
            else:
                page_size = default_page_size

            if self.paginator is not None:
                self.paginator.page_size = page_size
                if hasattr(self.paginator, 'max_page_size'):
                    self.paginator.max_page_size = default_page_size

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={'request': request})
                data = self.get_paginated_response(serializer.data).data
            else:
                limited = queryset[:page_size]
                serializer = self.get_serializer(limited, many=True, context={'request': request})
                data = {
                    'results': serializer.data,
                    'count': queryset.count(),
                    'next': None,
                    'previous': None,
                }

            total = int(data.get('count', queryset.count()) or 0)
            results = data.get('results', [])
            page_count = len(results)

            current_page = max(int(request.query_params.get('page', 1) or 1), 1)
            total_pages = math.ceil(total / page_size) if page_size else 1
            total_pages = max(total_pages, 1)

            execution_time = time.time() - start_time
            response = {
                'success': True,
                'count': page_count,
                'total': total,
                'page': current_page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': current_page < total_pages,
                'has_previous': current_page > 1,
                'results': results,
                'filters_applied': dict(request.query_params),
                'message': 'Images retrieved from database',
                'source': 'database',
                'performance': {
                    'execution_time': f"{execution_time:.2f}s",
                    'items_per_page': page_size
                }
            }
            if data.get('next'): response['next'] = data['next']
            if data.get('previous'): response['previous'] = data['previous']
            return Response(response)
        except Exception as e:
            logger.error(f"Error in image list: {e}", exc_info=True) # Added exc_info for better debugging
            return Response({
                'success': False, 'count': 0, 'results': [], 'error': str(e),
                'message': 'Database query failed'
            }, status=500)


class BaseOptionViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'options']
    filter_backends = [DjangoFilterBackend]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_filter_type(self):
        return self.__class__.__name__.lower().replace('optionviewset', '').replace('optionsviewset', '')

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        invalidate_filter_cache(self.get_filter_type())
        return response

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        invalidate_filter_cache(self.get_filter_type())
        return response


option_viewsets = [
    (DirectorOption, DirectorOptionSerializer),
    (CinematographerOption, CinematographerOptionSerializer),
    (EditorOption, EditorOptionSerializer),
    (ColoristOption, ColoristOptionSerializer),
    (CostumeDesignerOption, CostumeDesignerOptionSerializer),
    (ProductionDesignerOption, ProductionDesignerOptionSerializer),
    (GenreOption, GenreOptionSerializer),
    (ColorOption, ColorOptionSerializer),
    (MediaTypeOption, MediaTypeOptionSerializer),
    (AspectRatioOption, AspectRatioOptionSerializer),
    (OpticalFormatOption, OpticalFormatOptionSerializer),
    (FormatOption, FormatOptionSerializer),
    (InteriorExteriorOption, InteriorExteriorOptionSerializer),
    (TimeOfDayOption, TimeOfDayOptionSerializer),
    (NumberOfPeopleOption, NumberOfPeopleOptionSerializer),
    (GenderOption, GenderOptionSerializer),
    (AgeOption, AgeOptionSerializer),
    (EthnicityOption, EthnicityOptionSerializer),
    (FrameSizeOption, FrameSizeOptionSerializer),
    (ShotTypeOption, ShotTypeOptionSerializer),
    (CompositionOption, CompositionOptionSerializer),
    (LensSizeOption, LensSizeOptionSerializer),
    (LensTypeOption, LensTypeOptionSerializer),
    (LightingOption, LightingOptionSerializer),
    (LightingTypeOption, LightingTypeOptionSerializer),
    (CameraTypeOption, CameraTypeOptionSerializer),
    (ResolutionOption, ResolutionOptionSerializer),
    (FrameRateOption, FrameRateOptionSerializer),
    (MovieOption, MovieOptionSerializer),
    (ActorOption, ActorOptionSerializer),
    (CameraOption, CameraOptionSerializer),
    (LensOption, LensOptionSerializer),
    (LocationOption, LocationOptionSerializer),
    (SettingOption, SettingOptionSerializer),
    (FilmStockOption, FilmStockOptionSerializer),
    (ShotTimeOption, ShotTimeOptionSerializer),
    (DescriptionOption, DescriptionOptionSerializer),
    (VfxBackingOption, VfxBackingOptionSerializer),
    (ShadeOption, ShadeOptionSerializer),
    (ArtistOption, ArtistOptionSerializer),
    (FilmingLocationOption, FilmingLocationOptionSerializer),
    (LocationTypeOption, LocationTypeOptionSerializer),
    (YearOption, YearOptionSerializer),
]

for model, serializer in option_viewsets:
    name = model.__name__ + "ViewSet"
    globals()[name] = type(name, (BaseOptionViewSet,), {
        'queryset': model.objects.all(),
        'serializer_class': serializer,
    })


class MovieViewSet(ReadOnlyModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MovieFilter
    lookup_field = 'slug'

    def get_queryset(self):
        qs = super().get_queryset()
        ordering = self.request.query_params.get('ordering', '-year')
        if ordering in ['-year', 'year', 'title', '-title']:
            qs = qs.order_by(ordering)
        return qs

    def retrieve(self, request, *args, **kwargs):
        movie = self.get_object()
        images = movie.images.select_related(
            'movie', 'director', 'cinematographer', 'shot_type', 'lighting', 'color'
        ).prefetch_related('genre', 'tags')[:20]
        movie_serializer = self.get_serializer(movie)
        images_serializer = ImageListSerializer(images, many=True, context={'request': request})
        total_images = movie.images.count()
        return Response({
            'success': True,
            'movie': movie_serializer.data,
            'images': images_serializer.data,
            'statistics': {
                'total_images': total_images,
                'images_shown': len(images_serializer.data)
            }
        })

    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.action in ['create', 'update', 'partial_update', 'destroy'] else [permissions.AllowAny()]


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TagFilter
    lookup_field = 'slug'

    def get_queryset(self):
        qs = super().get_queryset()
        ordering = self.request.query_params.get('ordering', 'name')
        if ordering in ['name', '-name']:
            qs = qs.order_by(ordering)
        return qs

    def list(self, request, *args, **kwargs):
        return Response({"error": "Tags list endpoint is not available"}, status=404)

    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.action in ['create', 'update', 'partial_update', 'destroy'] else [permissions.AllowAny()]


class FiltersView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: FiltersResponseSerializer},
        description="List of available filter fields with dropdown options."
    )
    def get(self, request):
        query_params = request.GET
        logger.info(f"FiltersView GET: {dict(query_params)}")

        filter_param_keys = [
            'search', 'tags', 'movie', 'actor', 'camera', 'lens', 'location', 'setting',
            'film_stock', 'shot_time', 'description', 'vfx_backing', 'media_type', 'genre',
            'time_period', 'color', 'shade', 'aspect_ratio', 'optical_format', 'lab_process',
            'format', 'interior_exterior', 'time_of_day', 'number_of_people', 'gender', 'age',
            'ethnicity', 'frame_size', 'shot_type', 'composition', 'lens_type', 'lighting',
            'lighting_type', 'director', 'cinematographer', 'editor', 'colorist', 'costume_designer',
            'production_designer', 'artist', 'filming_location', 'location_type', 'year',
            'frame_rate', 'lens_size', 'resolution'
        ]
        has_filter_params = any(query_params.get(key) for key in filter_param_keys)

        if not has_filter_params:
            return self._get_filter_configuration_with_options()

        search_params = {k: query_params.get(k) for k in filter_param_keys + ['limit', 'offset']}
        search_params['limit'] = int(search_params.get('limit', 20))
        search_params['offset'] = int(search_params.get('offset', 0))
        applied_filters = {k: v for k, v in search_params.items() if v and k not in ['limit', 'offset']}
        return self._perform_filtered_search(search_params, applied_filters, request)

    def _get_filter_configuration_with_options(self):
        try:
            filters_data = get_all_cached_filters()
            filter_options = {}
            for name, opts in filters_data.items():
                if opts and not name.endswith('_slugs'):
                    values = [opt.get('value', str(opt)) for opt in opts if opt]
                    filter_options[name] = [{"value": v, "label": v} for v in values]

            shotdeck_filters = [
                {"id": "search", "label": "Search", "type": "text", "placeholder": "Search titles and descriptions...", "options": []},
                {"id": "media_type", "label": "Media Type", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('media_type', [])]},
                {"id": "genre", "label": "Genre", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('genre', [])]},
                {"id": "color", "label": "Color", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('color', [])]},
                {"id": "aspect_ratio", "label": "Aspect Ratio", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('aspect_ratio', [])]},
                {"id": "optical_format", "label": "Optical Format", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('optical_format', [])]},
                {"id": "format", "label": "Format", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('format', [])]},
                {"id": "time_period", "label": "Time Period", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('time_period', [])]},
                {"id": "interior_exterior", "label": "Interior/Exterior", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('interior_exterior', [])]},
                {"id": "time_of_day", "label": "Time of Day", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('time_of_day', [])]},
                {"id": "lighting", "label": "Lighting", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('lighting', [])]},
                {"id": "lighting_type", "label": "Lighting Type", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('lighting_type', [])]},
                {"id": "shot_type", "label": "Shot Type", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('shot_type', [])]},
                {"id": "composition", "label": "Composition", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('composition', [])]},
                {"id": "lens_type", "label": "Lens Type", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('lens_type', [])]},
                {"id": "camera_type", "label": "Camera Type", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('camera_type', [])]},
                {"id": "gender", "label": "Gender", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('gender', [])]},
                {"id": "age", "label": "Age", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('age', [])]},
                {"id": "ethnicity", "label": "Ethnicity", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('ethnicity', [])]},
                {"id": "frame_size", "label": "Frame Size", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('frame_size', [])]},
                {"id": "number_of_people", "label": "Number of People", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('number_of_people', [])]},
                {"id": "actor", "label": "Actor", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('actor', [])]},
                {"id": "camera", "label": "Camera", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('camera', [])]},
                {"id": "lens", "label": "Lens", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('lens', [])]},
                {"id": "location", "label": "Location", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('location', [])]},
                {"id": "setting", "label": "Setting", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('setting', [])]},
                {"id": "director", "label": "Director", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('director', [])]},
                {"id": "cinematographer", "label": "Cinematographer", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('cinematographer', [])]},
                {"id": "editor", "label": "Editor", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('editor', [])]},
                {"id": "year", "label": "Year", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('year', [])]},
                {"id": "movie", "label": "Movie", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('movie', [])]},
                {"id": "shade", "label": "Shade", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('shade', [])]},
                {"id": "filming_location", "label": "Filming Location", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('filming_location', [])]},
                {"id": "location_type", "label": "Location Type", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('location_type', [])]},
                {"id": "costume_designer", "label": "Costume Designer", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('costume_designer', [])]},
                {"id": "production_designer", "label": "Production Designer", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('production_designer', [])]},
                {"id": "colorist", "label": "Colorist", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('colorist', [])]},
                {"id": "film_stock", "label": "Film Stock", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('film_stock', [])]},
                {"id": "artist", "label": "Artist", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('artist', [])]},
                {"id": "resolution", "label": "Resolution", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('resolution', [])]},
                {"id": "frame_rate", "label": "Frame Rate", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('frame_rate', [])]},
                {"id": "lens_size", "label": "Lens Size", "type": "dropdown", "multiple": False, "options": [{"value": o["value"], "label": o.get("label", o["value"])} for o in filter_options.get('lens_size', [])]},
            ]

            working_filters = []
            empty_filters = []
            for f in shotdeck_filters:
                fid = f['id']
                if fid == 'search' or (fid in filters_data and filters_data[fid]):
                    working_filters.append(fid)
                    f.update(disabled=False, disabled_reason=None)
                else:
                    empty_filters.append(fid)
                    f.update(disabled=True, disabled_reason='No data available for this filter')

            return Response({
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
            })
        except Exception as e:
            logger.error(f"Filter config error: {e}")
            return Response({'success': False, 'error': str(e)}, status=500)

    def _perform_filtered_search(self, search_params, applied_filters, request):
        try:
            queryset = Image.objects.all()
            smart_params = search_params.copy()
            removed = []

            for k, v in search_params.items():
                if k in ['limit', 'offset', 'search'] or not v:
                    continue
                try:
                    test = ImageFilter(data={k: v}, queryset=queryset)
                    if test.is_valid() and test.qs.count() == 0:
                        smart_params.pop(k, None)
                        removed.append(k)
                except:
                    smart_params.pop(k, None)
                    removed.append(k)

            active = [k for k in smart_params if k not in ['limit', 'offset']]
            if not active:
                total = Image.objects.count()
                results = Image.objects.all()[search_params['offset']:search_params['offset'] + search_params['limit']]
                serializer = ImageSerializer(results, many=True, context={'request': request})
                return Response({
                    'success': True, 'count': total, 'results': serializer.data, 'total': total,
                    'filters_applied': {}, 'smart_filtering': {
                        'enabled': True, 'removed_filters': removed, 'active_filters': [],
                        'note': 'All filters removed - showing all images'
                    }, 'message': 'Smart filtering removed all filters', 'source': 'database'
                })

            filterset = ImageFilter(data=smart_params, queryset=queryset)
            if not filterset.is_valid():
                return Response({'success': False, 'errors': filterset.errors}, status=400)

            qs = filterset.qs
            total = qs.count()
            results = qs[search_params['offset']:search_params['offset'] + search_params['limit']]
            serializer = ImageSerializer(results, many=True, context={'request': request})

            return Response({
                'success': True, 'count': total, 'results': serializer.data, 'total': total,
                'filters_applied': {k: smart_params[k] for k in active},
                'smart_filtering': {
                    'enabled': True, 'removed_filters': removed, 'active_filters': active
                },
                'message': f'Smart filtering removed {len(removed)} empty filters',
                'source': 'database'
            })
        except Exception as e:
            logger.error(f"DB search failed: {e}")
            return Response({'success': False, 'error': str(e)}, status=500)
