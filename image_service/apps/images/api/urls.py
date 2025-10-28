from django.urls import path, include, re_path
from django.http import JsonResponse
# Router removed - using direct URL patterns
from .views import (
    ImageViewSet, MovieViewSet, TagViewSet, FiltersView, HealthCheckView
)

# OPTIONS endpoints removed - keeping only essential endpoints

def tags_not_allowed(request):
    """Return 404 for tags list endpoint"""
    return JsonResponse({"error": "Tags list endpoint is not available"}, status=404)

urlpatterns = [
    # Health check endpoint
    path('health/', HealthCheckView.as_view(), name='health-check'),

    # Filters endpoints (must come before generic image slug pattern)
    path('images/filters/', FiltersView.as_view(), name='image-filters'),

    # Individual image endpoints (must come after specific patterns)
    # Use re_path to allow special characters in slugs (parentheses, quotes, etc.)
    re_path(r'^images/(?P<slug>[^/]+)/$', ImageViewSet.as_view({
        'get': 'retrieve'
    }), name='image-detail'),
    # Singular legacy route removed to avoid duplicate paths in the OpenAPI schema.
    # Keep only the plural '/images/{slug}/' endpoint above.

    # Images list endpoint
    path('images/', ImageViewSet.as_view({
        'get': 'list'
    }), name='image-list'),

    # Movie endpoints
    path('movies/', MovieViewSet.as_view({
        'get': 'list'
    }), name='movie-list'),
    path('movie/<slug:slug>/', MovieViewSet.as_view({
        'get': 'retrieve'
    }), name='image-movie'),

    # Tags endpoints
    path('tags/<slug:slug>/', TagViewSet.as_view({
        'get': 'retrieve'
    }), name='tag-detail'),

]