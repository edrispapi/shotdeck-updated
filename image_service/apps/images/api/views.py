# Path: /image_service/apps/images/api/views.py
from apps.images.filters import ImageFilter
import logging
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
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
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption
)
from .serializers import (
    ImageSerializer, MovieSerializer, TagSerializer,
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
    DescriptionOptionSerializer, VfxBackingOptionSerializer
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


@extend_schema(tags=['Image Search & Filtering'])
class ImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing images using database queries with filtering.
    """
    queryset = Image.objects.all().order_by('-created_at')
    serializer_class = ImageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ImageFilter
    lookup_field = 'slug'

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    @extend_schema(
        summary="Create new image",
        description="Create a new image with associated metadata and tags",
        request=ImageSerializer,
        responses={
            201: ImageSerializer,
            400: Error401Serializer,
            401: Error401Serializer,
            403: Error403Serializer,
        }
    )
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

    @extend_schema(
        summary="Update image",
        description="Update an existing image",
        request=ImageSerializer,
        responses={
            200: ImageSerializer,
            400: Error401Serializer,
            401: Error401Serializer,
            403: Error403Serializer,
            404: Error404Serializer,
        }
    )
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # Invalidate cache after update
        filter_type = self.get_filter_type()
        invalidate_filter_cache(filter_type)
        return response

    @extend_schema(exclude=True)  # Hide from Swagger documentation
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Get full dataset for image",
        description="Retrieve complete dataset information for a specific image from the source JSON files",
        responses={200: OpenApiTypes.OBJECT},
        tags=['Image Search & Filtering']
    )
    @action(detail=True, methods=['get'], url_path='dataset')
    def get_dataset(self, request, slug=None):
        """
        Get the complete dataset information for a specific image from the JSON source files.
        Ultra-fast lookup using direct filename matching.
        """
        import json
        from pathlib import Path

        try:
            # Get the image object
            image = self.get_object()

            # Ultra-fast approach: Extract ID from slug and try direct file access
            dataset_dir = Path('/host_data/')

            if not dataset_dir.exists():
                return Response({
                    'success': False,
                    'message': 'Dataset directory not found',
                    'image_id': image.id
                }, status=404)

            # Extract potential ID from slug (last part after last dash)
            slug_parts = image.slug.split('-') if image.slug else []
            potential_id = slug_parts[-1].upper() if slug_parts and len(slug_parts[-1]) > 4 else None

            json_filename = None
            match_type = None

            # Strategy 1: Direct filename match (fastest)
            if potential_id:
                direct_file = dataset_dir / f"{potential_id}.json"
                if direct_file.exists():
                    json_filename = f"{potential_id}.json"
                    match_type = 'direct_filename'

            # Strategy 2: Fast limited search (much faster than full cache)
            if not json_filename:
                # Search only first 100 files for speed (most recent/popular movies)
                search_limit = 100
                files_checked = 0

                for json_file in sorted(dataset_dir.glob('*.json'), reverse=True):  # Start with newest files
                    if files_checked >= search_limit:
                        break

                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        files_checked += 1

                        if 'data' in data and 'details' in data['data']:
                            details = data['data']['details']
                            json_title = details.get('full_title', '').strip()

                            # Exact title match
                            if json_title and image.title and json_title.lower() == image.title.lower():
                                json_filename = json_file.name
                                match_type = 'limited_title_match'
                                break

                    except (json.JSONDecodeError, KeyError):
                        continue

            # If we found a match, return the data
            if json_filename:
                json_file_path = dataset_dir / json_filename
                try:
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    return Response({
                        'success': True,
                        'image_id': image.id,
                        'json_filename': json_filename,
                        'match_type': match_type,
                        'data': data
                    })

                except (json.JSONDecodeError, KeyError) as e:
                    return Response({
                        'success': False,
                        'message': f'Error reading JSON file: {str(e)}',
                        'image_id': image.id
                    }, status=500)

            # No match found
            return Response({
                'success': False,
                'message': f'No matching dataset file found for image {image.id} (title: {image.title}, slug: {image.slug})',
                'image_id': image.id,
                'tried_filename': potential_id
            }, status=404)

        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error retrieving dataset: {str(e)}'
            }, status=500)

    def _build_json_file_index(self):
        """
        Build an index of JSON files for fast lookups.
        Maps titles to filenames.
        """
        from pathlib import Path
        import json

        dataset_dir = Path('/home/a/Desktop/shotdeck/shot_json_data/')
        index = {
            'by_title': {},
            'by_filename': {},
            'last_updated': None
        }

        if not dataset_dir.exists():
            return index

        print("Building JSON file index for fast dataset lookups...")

        for json_file in dataset_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'data' in data and 'details' in data['data']:
                    details = data['data']['details']
                    title = details.get('full_title', '').strip()

                    if title:
                        # Store multiple variations for better matching
                        index['by_title'][title.lower()] = json_file.name

                        # Also index by filename (without extension)
                        filename_key = json_file.stem.lower()
                        index['by_filename'][filename_key] = json_file.name

            except (json.JSONDecodeError, KeyError):
                continue

        print(f"Index built: {len(index['by_title'])} titles indexed")
        return index

    @extend_schema(exclude=True)  # Hide from Swagger documentation
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
            # Use the parent class filtering (built into DRF with filterset_class)
            response = super().list(request, *args, **kwargs)

            # Modify the response to match our custom format
            data = response.data

            # Extract pagination info
            results = data['results']
            count = len(results)

            # Get total count from pagination
            total = getattr(response, 'total_count', count)

            # Get applied filters (non-empty values from request)
            applied_filters = {}
            for key, value in request.query_params.items():
                if key not in ['limit', 'offset', 'page'] and value and value != ['']:
                    applied_filters[key] = value[0] if isinstance(value, list) else value

            custom_response = {
                'count': count,
                'total': total,
                'results': results,
                'filters_applied': applied_filters,
                'message': 'Images retrieved from database',
                'source': 'database'
            }

            return Response(custom_response)

        except Exception as e:
            return Response({
                'error': f'Database query failed: {str(e)}',
                'message': 'Using database queries'
            }, status=500)


@extend_schema(tags=['Movie Operations'])
class MovieViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing movies.
    """
    queryset = Movie.objects.all().order_by('-year')
    serializer_class = MovieSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'])
    def get_movie_images(self, request, slug=None):
        """
        Get all images associated with a specific movie.
        """
        movie = self.get_object()
        images = movie.images.all()
        serializer = ImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema(tags=['Tag Operations'])
class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing tags.
    """
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    lookup_field = 'slug'

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

    @extend_schema(exclude=True)  # Hide from Swagger documentation
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # Invalidate cache after update
        filter_type = self.get_filter_type()
        invalidate_filter_cache(filter_type)
        return response

    @extend_schema(exclude=True)  # Hide from Swagger documentation
    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        # Invalidate cache after partial update
        filter_type = self.get_filter_type()
        invalidate_filter_cache(filter_type)
        return response


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

    @extend_schema(
        tags=['Image Search & Filtering'],
        summary="Get available image filters or search images by filters",
        description="Returns all available filter options for image search, or search images based on selected filter parameters",
        parameters=[
            # Single-select dropdown parameters with pre-existing options only (no checkboxes)
            OpenApiParameter(
                'search',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Text search in titles and descriptions"
            ),
            OpenApiParameter(
                'media_type',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Movie", "TV", "Trailer", "Music Video", "Commercial"],
                description="Media type selection from dropdown"
            ),
            OpenApiParameter(
                'genre',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery", "Romance", "Science Fiction", "Thriller", "War", "Western"],
                description="Genre selection from dropdown"
            ),
            OpenApiParameter(
                'color',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Warm", "Cool", "Mixed", "Saturated", "Desaturated", "Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Purple", "Magenta", "Pink", "White", "Sepia", "Black and White"],
                description="Color selection from dropdown"
            ),
            OpenApiParameter(
                'aspect_ratio',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["1 - square", "1.20", "1.33", "1.37", "1.43", "1.66", "1.78", "1.85", "1.90", "2.00", "2.20", "2.35", "2.39", "2.55", "2.67", "2.76+", "3.55"],
                description="Aspect ratio selection from dropdown"
            ),
            OpenApiParameter(
                'optical_format',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Anamorphic", "Spherical", "Super 35", "3 perf", "2 perf", "Open Gate", "3D"],
                description="Optical format selection from dropdown"
            ),
            OpenApiParameter(
                'format',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Film - 35mm", "Film - 16mm", "Film - Super 8mm", "Film - 65mm / 70mm", "Film - IMAX", "Tape", "Digital", "Digital - Large Format", "Animation"],
                description="Format selection from dropdown"
            ),
            OpenApiParameter(
                'time_period',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Future", "2020s", "2010s", "2000s", "1990s", "1980s", "1970s", "1960s", "1950s", "1940s", "1930s", "1920s", "1910s", "1900s", "1800s", "1700s", "Renaissance: 1400-1700", "Medieval: 500-1400", "Ancient: 2000BC-500AD", "Stone Age: pre-2000BC"],
                description="Time period selection from dropdown"
            ),
            OpenApiParameter(
                'interior_exterior',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Interior", "Exterior"],
                description="Interior/Exterior selection from dropdown"
            ),
            OpenApiParameter(
                'time_of_day',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Dawn", "Day", "Dusk", "Night", "Sunrise", "Sunset"],
                description="Time of day selection from dropdown"
            ),
            OpenApiParameter(
                'lighting',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Backlight", "Edge light", "Hard light", "High contrast", "Low contrast", "Side light", "Silhouette", "Soft light", "Top light", "Underlight"],
                description="Lighting selection from dropdown"
            ),
            OpenApiParameter(
                'shot_type',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Aerial", "Overhead", "High angle", "Low angle", "Dutch angle", "Establishing shot", "Over the shoulder", "Clean single", "2 shot", "3 shot", "Group shot", "Insert"],
                description="Shot type selection from dropdown"
            ),
            OpenApiParameter(
                'composition',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Balanced", "Center", "Left heavy", "Right heavy", "Short side", "Symmetrical"],
                description="Composition selection from dropdown"
            ),
            OpenApiParameter(
                'lens_type',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Ultra Wide / Fisheye", "Wide", "Medium", "Long Lens", "Telephoto"],
                description="Lens size selection from dropdown"
            ),
            OpenApiParameter(
                'camera_type',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Digital Cinema", "Film Camera", "Video Camera", "DSLR", "Mirrorless", "Other"],
                description="Camera type selection from dropdown"
            ),
            OpenApiParameter(
                'gender',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Male", "Female", "Other"],
                description="Gender selection from dropdown"
            ),
            OpenApiParameter(
                'age',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Baby", "Toddler", "Child", "Teenager", "Young Adult", "Mid-adult", "Middle age", "Senior"],
                description="Age selection from dropdown"
            ),
            OpenApiParameter(
                'ethnicity',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Black", "White", "Latinx", "Middle Eastern", "South-East Asian", "East Asian", "South Asian", "Indigenous Peoples", "Mixed-race"],
                description="Ethnicity selection from dropdown"
            ),
            OpenApiParameter(
                'frame_size',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Extreme Wide", "Wide", "Medium Wide", "Medium", "Medium Close Up", "Close Up", "Extreme Close Up"],
                description="Frame size selection from dropdown"
            ),
            OpenApiParameter(
                'number_of_people',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["None", "1", "2", "3", "4", "5", "6+"],
                description="Number of people selection from dropdown"
            ),
            OpenApiParameter(
                'actor',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Actor name search (type to search)"
            ),
            OpenApiParameter(
                'camera',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Arri Alexa", "Red Dragon", "Sony F55", "Panavision", "Canon C300", "Blackmagic", "Other"],
                description="Camera selection from dropdown"
            ),
            OpenApiParameter(
                'lens',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Canon", "Zeiss", "Angenieux", "Panavision", "Arri", "Cooke", "Leica", "Other"],
                description="Lens selection from dropdown"
            ),
            OpenApiParameter(
                'location',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["Urban", "Rural", "Indoor", "Outdoor", "Studio", "Location", "Other"],
                description="Location selection from dropdown"
            ),
            OpenApiParameter(
                'setting',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["House", "Office", "Street", "Nature", "Vehicle", "Public Space", "Custom"],
                description="Setting selection from dropdown"
            ),
            OpenApiParameter(
                'year',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["2020s", "2010s", "2000s", "1990s", "1980s", "1970s", "Pre-1970"],
                description="Year selection from dropdown"
            ),
            OpenApiParameter(
                'limit',
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Number of results (default: 20)"
            ),
            OpenApiParameter(
                'offset',
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Offset for pagination (default: 0)"
            ),
        ],
        responses={
            200: {
                'oneOf': [
                    {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'},
                            'data': {
                                'type': 'object',
                                'properties': {
                                    'filters': {'type': 'array'}
                                }
                            }
                        },
                        'description': 'Filter configuration when no search parameters provided'
                    },
                    {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'count': {'type': 'integer'},
                            'results': {'type': 'array'},
                            'total': {'type': 'integer'},
                            'filters_applied': {'type': 'object'}
                        },
                        'description': 'Search results when filter parameters provided'
                    }
                ]
            }
        }
    )
    def get(self, request):
        """
        Return all available filter options for image search, or search images by filters
        """
        try:
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"FiltersView GET request with query_params: {dict(request.query_params)}")

            # Check if any search/filter parameters are provided
            search_params = {
                'search': request.query_params.get('search'),
                'tags': request.query_params.get('tags'),
                'movie': request.query_params.get('movie'),
                'actors': request.query_params.get('actors'),
                'camera': request.query_params.get('camera'),
                'lens': request.query_params.get('lens'),
                'location': request.query_params.get('location'),
                'setting': request.query_params.get('setting'),
                'film_stock': request.query_params.get('film_stock'),
                'shot_time': request.query_params.get('shot_time'),
                'description': request.query_params.get('description'),
                'vfx_backing': request.query_params.get('vfx_backing'),
                'media_type': request.query_params.get('media_type'),
                'genre': request.query_params.get('genre'),
                'time_period': request.query_params.get('time_period'),
                'color': request.query_params.get('color'),
                'shade': request.query_params.get('shade'),
                'aspect_ratio': request.query_params.get('aspect_ratio'),
                'optical_format': request.query_params.get('optical_format'),
                'lab_process': request.query_params.get('lab_process'),
                'film_format': request.query_params.get('film_format'),
                'int_ext': request.query_params.get('int_ext'),
                'time_of_day': request.query_params.get('time_of_day'),
                'numpeople': request.query_params.get('numpeople'),
                'gender': request.query_params.get('gender'),
                'subject_age': request.query_params.get('subject_age'),
                'subject_ethnicity': request.query_params.get('subject_ethnicity'),
                'frame_size': request.query_params.get('frame_size'),
                'shot_type': request.query_params.get('shot_type'),
                'composition': request.query_params.get('composition'),
                'lens_type': request.query_params.get('lens_type'),
                'lighting': request.query_params.get('lighting'),
                'lighting_type': request.query_params.get('lighting_type'),
                'limit': int(request.query_params.get('limit', 20)),
                'offset': int(request.query_params.get('offset', 0))
            }

            # Remove None values and check if any filters are applied
            applied_filters = {k: v for k, v in search_params.items() if v is not None and k not in ['limit', 'offset']}
            has_filters = len(applied_filters) > 0

            if not has_filters:
                # Return the filter configuration (no search parameters provided)
                filters_data = self._get_filter_configuration()
                response_data = {
                    "success": True,
                    "message": "Filters",
                    "data": filters_data
                }
                return Response(response_data, status=status.HTTP_200_OK)

            # Perform search with filters
            return self._perform_filtered_search(search_params, applied_filters, request)

        except Exception as e:
            logger.error(f"Error in filters/search operation: {e}")
            return Response({
                'success': False,
                'message': 'Error processing request',
                'error': str(e)
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
                        "name": "Search",
                    "type": "text",
                    "placeholder": "Search titles and descriptions...",
                    "options": []
                },
                {
                    "id": "media_type",
                    "name": "Media Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('media_type', [])]
                },
                {
                    "id": "genre",
                        "name": "Genre",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('genre', [])]
                },
                {
                    "id": "color",
                    "name": "Color",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('color', [])]
                },
                {
                    "id": "aspect_ratio",
                    "name": "Aspect Ratio",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('aspect_ratio', [])]
                },
                {
                    "id": "optical_format",
                    "name": "Optical Format",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('optical_format', [])]
                },
                {
                    "id": "format",
                    "name": "Film Format",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('format', [])]
                },
                {
                    "id": "time_period",
                    "name": "Time Period",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('time_period', [])]
                },
                {
                    "id": "interior_exterior",
                    "name": "Interior/Exterior",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('interior_exterior', [])]
                },
                {
                    "id": "time_of_day",
                    "name": "Time of Day",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('time_of_day', [])]
                },
                {
                    "id": "lighting",
                        "name": "Lighting",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lighting', [])]
                },
                {
                    "id": "shot_type",
                    "name": "Shot Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('shot_type', [])]
                },
                {
                    "id": "composition",
                    "name": "Composition",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('composition', [])]
                },
                {
                    "id": "lens_type",
                    "name": "Lens Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lens_type', [])]
                },
                {
                    "id": "camera_type",
                    "name": "Camera Type",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('camera_type', [])]
                },
                {
                    "id": "gender",
                    "name": "Gender",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('gender', [])]
                },
                {
                    "id": "age",
                    "name": "Age",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('age', [])]
                },
                {
                    "id": "ethnicity",
                    "name": "Ethnicity",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('ethnicity', [])]
                },
                {
                    "id": "frame_size",
                    "name": "Frame Size",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('frame_size', [])]
                },
                {
                    "id": "number_of_people",
                    "name": "Number of People",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('number_of_people', [])]
                },
                {
                    "id": "actor",
                    "name": "Actor",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('actor', [])]
                },
                {
                    "id": "camera",
                    "name": "Camera",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('camera', [])]
                },
                {
                    "id": "lens",
                    "name": "Lens",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('lens', [])]
                },
                {
                    "id": "location",
                    "name": "Location",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('location', [])]
                },
                {
                    "id": "setting",
                    "name": "Setting",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": opt["value"], "label": opt["value"]} for opt in filter_options.get('setting', [])]
                },
                {
                    "id": "year",
                    "name": "Year",
                    "type": "dropdown",
                    "multiple": False,
                    "options": [{"value": str(y), "label": str(y)} for y in sorted(filter_options.get('years', []))]
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
                        "name": "Search",
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
        """
        try:
            from apps.images.filters import ImageFilter

            # Build queryset using ImageFilter
            queryset = Image.objects.all()

            # Create a filter instance
            filterset = ImageFilter(data=search_params, queryset=queryset)

            # Check if filters are valid
            if not filterset.is_valid():
                return Response({
                    'success': False,
                    'message': 'Invalid filter parameters',
                    'errors': filterset.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # Apply filters
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

            return Response({
                'success': True,
                'count': len(serializer.data),
                'results': serializer.data,
                'total': total_count,
                'filters_applied': applied_filters,
                'message': 'Image search completed from database',
                'source': 'database'
            })

        except Exception as e:
            logger.error(f"Error performing database search: {e}")
            return Response({
                'success': False,
                'message': 'Error performing search',
                'error': str(e),
                'source': 'database-error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
