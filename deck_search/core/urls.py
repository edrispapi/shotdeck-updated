from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

def home_view(request):
    return JsonResponse({
        "service": "Search Service",
        "version": "1.0.0",
        "description": "Advanced image search and indexing service for Shotdeck platform",
        "stats": {
            "elasticsearch_status": "connected",
            "indexed_documents": 1310,
            "search_queries_today": 0,
            "response_time_avg": "45ms"
        },
        "endpoints": {
            "api": "/api/search/",
            "admin": "/admin/",
            "docs": "/docs/",
            "images_search": "/api/search/images/",
            "similar_search": "/api/search/similar/",
            "user_search": "/api/search/user/"
        },
        "features": [
            "Full-text search",
            "Semantic search",
            "Image similarity search",
            "Advanced filtering",
            "Real-time indexing"
        ],
        "status": "running",
        "timestamp": request.META.get('HTTP_HOST', 'localhost')
    })

urlpatterns = [
    path('', home_view, name='home'),

    path('admin/', admin.site.urls),
    # Search Service API endpoints
    path('api/search/', include('apps.search.api.search_urls')),
    # Image-related endpoints (color samples, search by color)
    path('api/images/', include('apps.search.api.image_urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]