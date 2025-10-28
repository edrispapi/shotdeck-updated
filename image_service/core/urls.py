# مسیر: image_service/core/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse, HttpResponse, Http404
import base64
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve
# drf-spectacular views for auto-generated OpenAPI schema and Swagger UI
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.decorators.cache import cache_page
from rest_framework.authtoken.views import obtain_auth_token
import os

def home_view(request):
    return JsonResponse({
        "service": "Image Service",
        "version": "1.0.0",
        "description": "مدیریت تصاویر و داده‌های بصری در پلتفرم Shotdeck",
        "stats": {
            "total_images": 1000,
            "indexed_images": 1310,
            "tags_count": 30,
            "movies_count": 20
        },
        "endpoints": {
            "api": "/api/",
            "admin": "/admin/",
            "docs": "/api/schema/swagger-ui/",
            "images": "/api/images/",
            "token": "/api/api-token-auth/"
        },
        "status": "running",
        "timestamp": request.META.get('HTTP_HOST', 'localhost')
    })

def health_view(request):
    """Health check endpoint"""
    return JsonResponse({
        "status": "healthy",
        "service": "image_service",
        "timestamp": request.META.get('HTTP_HOST', 'localhost')
    })
# Static OpenAPI schema removed. drf-spectacular is the canonical schema provider.
# Use the `/api/schema/` SpectacularAPIView endpoint to get the generated schema.

# The previous custom Swagger UI HTML fallback has been removed in favor of
# drf-spectacular's `SpectacularSwaggerView`, which serves the Swagger UI and
# loads the dynamically generated schema.

def test_schema_view(request):
    """Test view to verify schema loading works"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Schema Loading</title>
</head>
<body>
    <h1>Testing Schema Load</h1>
    <div id="result"></div>

    <script>
        fetch('/api/schema/?format=json')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                document.getElementById('result').innerHTML =
                    '<h2 style="color: green;">SUCCESS!</h2>' +
                    '<p>OpenAPI version: ' + data.openapi + '</p>' +
                    '<p>Title: ' + data.info.title + '</p>';
            })
            .catch(error => {
                document.getElementById('result').innerHTML =
                    '<h2 style="color: red;">ERROR!</h2>' +
                    '<p>' + error.message + '</p>';
            });
    </script>
</body>
</html>
    """
    return HttpResponse(html_content, content_type='text/html')


def serve_media_with_fallback(request, path):
    """
    Serve media files with fallback for missing images.
    Returns a placeholder image for missing image files.
    """
    # Check if the requested file exists
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(full_path):
        return serve(request, path, document_root=settings.MEDIA_ROOT)

    # Check if it's an image file (jpg, png, etc.)
    if path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
        # Prefer serving a branded placeholder from MEDIA_ROOT if present
        placeholder_candidates = [
            os.path.join(settings.MEDIA_ROOT, 'images', 'placeholder.png'),
            os.path.join(settings.MEDIA_ROOT, 'placeholder.png'),
        ]

        image_data = None
        for candidate in placeholder_candidates:
            if os.path.exists(candidate):
                with open(candidate, 'rb') as f:
                    image_data = f.read()
                break

        # If no file placeholder, return a visible SVG placeholder (renders clearly in browsers)
        if image_data is None:
            svg = (
                "<?xml version='1.0' encoding='UTF-8'?>"
                "<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'>"
                "<defs><style>@media(prefers-color-scheme:dark){.bg{fill:#1e1e1e}.fg{fill:#ddd}}@media(prefers-color-scheme:light){.bg{fill:#f3f3f3}.fg{fill:#333}}</style></defs>"
                "<rect class='bg' x='0' y='0' width='400' height='300'/>"
                "<g fill='none' stroke='#bbb' stroke-width='2'>"
                "<rect x='60' y='40' width='280' height='200' rx='8' ry='8'/>"
                "<path d='M90 210 L160 140 L210 190 L270 120 L330 210'/>"
                "<circle cx='230' cy='110' r='18'/></g>"
                "<text class='fg' x='200' y='270' text-anchor='middle' font-family='Arial, sans-serif' font-size='16'>Image not available</text>"
                "</svg>"
            )
            response = HttpResponse(svg, content_type='image/svg+xml; charset=utf-8')
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Content-Disposition'] = 'inline; filename="placeholder.svg"'
            return response

        # Otherwise serve the found placeholder file bytes (PNG)
        response = HttpResponse(image_data, content_type='image/png')
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Content-Disposition'] = 'inline; filename="placeholder.png"'
        return response

    # For non-image files, return 404
    raise Http404(f"Media file '{path}' not found.")

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

    # Get options from each ViewSet
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

urlpatterns = [
    path('', home_view, name='home'),
    path('api/health/', health_view, name='health'),
    path('api/options/', options_view, name='options'),

    path('admin/', admin.site.urls),
    path('api/', include('apps.images.api.urls')),
    path('api/api-token-auth/', obtain_auth_token, name='api_token_auth'),
    # Serve schema and Swagger UI using drf-spectacular (required)
    # Cache the generated OpenAPI JSON for 1 hour to avoid regenerating the
    # schema on every request; the schema is fairly static and this speeds up
    # the Swagger UI which requests the schema JSON on load.
    path('api/schema/', cache_page(60 * 60)(SpectacularAPIView.as_view()), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('test-schema/', test_schema_view, name='test-schema'),
] + [
    re_path(r'^media/(?P<path>.*)$', serve_media_with_fallback, name='media'),
]