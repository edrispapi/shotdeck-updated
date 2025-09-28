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

urlpatterns = [
    path('', home_view, name='home'),

    path('admin/', admin.site.urls),
    path('api/', include('apps.images.api.urls')),
    path('api/api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)