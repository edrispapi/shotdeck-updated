from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse, HttpResponse, Http404, FileResponse
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.decorators.cache import cache_page
from rest_framework.authtoken.views import obtain_auth_token
from apps.images.models import Image
from django.utils.text import slugify
from apps.images.api.media_utils import ensure_media_local, resolve_media_reference
import os
import mimetypes
from pathlib import Path


def _absolute_url(request, path: str) -> str:
    if request:
        try:
            return request.build_absolute_uri(path)
        except Exception:
            scheme = getattr(request, "scheme", "http") or "http"
            return f"{scheme}://{request.get_host()}{path}"
    public_base = getattr(settings, "PUBLIC_BASE_URL", None)
    if public_base:
        return f"{public_base.rstrip('/')}{path}"
    return path


def _absolute_media_url(request, relative_path: str) -> str:
    return _absolute_url(request, f"/media/{relative_path}")


def home_view(request):
    """Service home endpoint with statistics"""
    from apps.images.models import Image, Movie, Tag
    
    return JsonResponse({
        "service": "Image Service",
        "version": "1.0.0",
        "description": "Image management and metadata service for Shotdeck platform",
        "stats": {
            "total_images": Image.objects.count(),
            "total_movies": Movie.objects.count(),
            "total_tags": Tag.objects.count(),
        },
        "endpoints": {
            "api": "/api/",
            "admin": "/admin/",
            "docs": "/api/schema/swagger-ui/",
            "shots": "/shots/",
            "images": "/api/images/",
            "movies": "/api/movies/",
            "tags": "/api/tags/",
            "token": "/api/api-token-auth/",
            "health": "/api/health/",
        },
        "status": "running",
        "host": request.get_host()
    })


def health_view(request):
    """Health check endpoint"""
    from django.db import connection
    
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return JsonResponse({
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "image_service",
        "database": db_status,
        "host": request.get_host()
    })


def shots_view(request):
    """
    Main shots endpoint - returns paginated list of images
    This is the main endpoint for browsing shots/images
    """
    from apps.images.models import Image
    from django.core.paginator import Paginator
    
    # Get query parameters
    page = max(int(request.GET.get('page', 1) or 1), 1)

    default_page_size = 12
    filtered_max_page_size = 14
    base_max_page_size = 12

    try:
        requested_page_size = int(request.GET.get('page_size', default_page_size))
    except (TypeError, ValueError):
        requested_page_size = default_page_size

    # treat any non-pagination query params as filters
    non_pagination_params = {
        key: value for key, value in request.GET.items()
        if key not in {'page', 'page_size'}
    }
    is_filtered = any(value for value in non_pagination_params.values())
    max_page_size = filtered_max_page_size if is_filtered else base_max_page_size
    page_size = max(1, min(requested_page_size, max_page_size))
    search = request.GET.get('search', '')
    color = request.GET.get('color', '')
    media_type = request.GET.get('media_type', '')
    
    # Build queryset
    # In shots_view:
    queryset = Image.objects.select_related('movie').prefetch_related('tags').all()
    
    # Apply filters
    if search:
        queryset = queryset.filter(title__icontains=search)
    if color:
        queryset = queryset.filter(color__value__iexact=color)
    if media_type:
        queryset = queryset.filter(media_type__value__iexact=media_type)
    
    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    # Build response
    images_data = []
    for image in page_obj:
        normalized_slug = slugify(image.title) if image.title else None
        image_url = image.image_url
        image_available = False
        if image_url:
            relative_path, asset = resolve_media_reference(image_url)
            if relative_path and asset:
                image_available = not asset.is_placeholder
                image_url = _absolute_media_url(request, relative_path)
            elif not image_url.startswith(('http://', 'https://')):
                image_url = _absolute_url(request, f"/{image_url.lstrip('/')}")
        image_data = {
            "uuid": image.id,
            "slug": normalized_slug or image.slug,
            "title": image.title,
            "description": image.description,
            "image_url": image_url if image_url else None,
            "image_available": image_available,
            "movie": { 
                "slug": image.movie.slug,
                "title": image.movie.title,
                "year": image.movie.year,
            } if image.movie else None,
            "tags": [{"slug": tag.slug, "name": tag.name} for tag in image.tags.all()[:10]],
            "color": image.color.value if image.color else None,
            "media_type": image.media_type.value if image.media_type else None,
            "time_of_day": image.time_of_day.value if image.time_of_day else None,
            "interior_exterior": image.interior_exterior.value if image.interior_exterior else None,
        }
        images_data.append(image_data)
    
    return JsonResponse({
        "success": True,
        "count": len(images_data),
        "total": paginator.count,
        "page": page,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "results": images_data,
        "filters_applied": {
            "search": search or None,
            "color": color or None,
            "media_type": media_type or None,
        }
    })


def options_view(request):
    """Filter options endpoint - aggregate all options"""
    from apps.images.api.views import (
        GenreOptionViewSet, ColorOptionViewSet, MediaTypeOptionViewSet,
        AspectRatioOptionViewSet, OpticalFormatOptionViewSet, FormatOptionViewSet,
        InteriorExteriorOptionViewSet, TimeOfDayOptionViewSet, NumberOfPeopleOptionViewSet,
        GenderOptionViewSet, AgeOptionViewSet, EthnicityOptionViewSet,
        FrameSizeOptionViewSet, ShotTypeOptionViewSet, CompositionOptionViewSet,
        LensSizeOptionViewSet, LensTypeOptionViewSet, LightingOptionViewSet,
        LightingTypeOptionViewSet
    )

    options_data = {}

    viewsets = [
        ('genre', GenreOptionViewSet),
        ('color', ColorOptionViewSet),
        ('media_type', MediaTypeOptionViewSet),
        ('aspect_ratio', AspectRatioOptionViewSet),
        ('optical_format', OpticalFormatOptionViewSet),
        ('format', FormatOptionViewSet),
        ('int_ext', InteriorExteriorOptionViewSet),
        ('time_of_day', TimeOfDayOptionViewSet),
        ('numpeople', NumberOfPeopleOptionViewSet),
        ('gender', GenderOptionViewSet),
        ('subject_age', AgeOptionViewSet),
        ('subject_ethnicity', EthnicityOptionViewSet),
        ('frame_size', FrameSizeOptionViewSet),
        ('shot_type', ShotTypeOptionViewSet),
        ('composition', CompositionOptionViewSet),
        ('lens_size', LensSizeOptionViewSet),
        ('lens_type', LensTypeOptionViewSet),
        ('lighting', LightingOptionViewSet),
        ('lighting_type', LightingTypeOptionViewSet),
    ]

    for key, viewset_class in viewsets:
        try:
            queryset = viewset_class.queryset
            if queryset:
                options = list(queryset.values_list('value', flat=True).distinct().order_by('value'))
                options_data[key] = [{"value": opt, "label": opt} for opt in options]
        except Exception as e:
            options_data[key] = []

    return JsonResponse({
        "success": True,
        "data": options_data
    })


def serve_media_with_fallback(request, path):
    """
    Serve media files with fallback for missing images.
    Returns a placeholder image when the asset cannot be located anywhere.
    """
    normalized = path.lstrip('/')
    asset = ensure_media_local(normalized)

    if asset and asset.path.exists():
        try:
            relative = asset.path.relative_to(Path(settings.MEDIA_ROOT))
            return serve(request, str(relative), document_root=settings.MEDIA_ROOT)
        except ValueError:
            content_type, _ = mimetypes.guess_type(asset.path.name)
            return FileResponse(open(asset.path, 'rb'), content_type or 'application/octet-stream')

    # Return placeholder for missing image files
    if path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
        placeholder_candidates = [
            Path(settings.MEDIA_ROOT) / 'images' / 'placeholder.png',
            Path(settings.MEDIA_ROOT) / 'placeholder.png',
        ]

        for candidate in placeholder_candidates:
            if candidate.exists():
                with candidate.open('rb') as fh:
                    image_data = fh.read()
                response = HttpResponse(image_data, content_type='image/png')
                response['Cache-Control'] = 'no-store'
                return response

        # SVG placeholder
        svg = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'>"
            "<rect fill='#f3f3f3' width='400' height='300'/>"
            "<g fill='none' stroke='#bbb' stroke-width='2'>"
            "<rect x='60' y='40' width='280' height='200' rx='8'/>"
            "<path d='M90 210 L160 140 L210 190 L270 120 L330 210'/>"
            "<circle cx='230' cy='110' r='18'/></g>"
            "<text x='200' y='270' text-anchor='middle' font-family='Arial' font-size='16' fill='#333'>"
            "Image not available</text>"
            "</svg>"
        )
        response = HttpResponse(svg, content_type='image/svg+xml')
        response['Cache-Control'] = 'no-store'
        return response

    raise Http404(f"Media file '{path}' not found.")


urlpatterns = [
    # Main endpoints
    path('', home_view, name='home'),
    path('shots/', shots_view, name='shots'),
    
    # API endpoints
    path('api/', include('apps.images.api.urls')),
    path('api/health/', health_view, name='health'),
    path('api/options/', options_view, name='options'),
    path('api/api-token-auth/', obtain_auth_token, name='api_token_auth'),
    
    # Schema and documentation
    path('api/schema/', cache_page(60 * 60)(SpectacularAPIView.as_view()), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Media files
    re_path(r'^media/(?P<path>.*)$', serve_media_with_fallback, name='media'),
]

# Add static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
