# مسیر: image_service/core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

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
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)