# 🚀 Image Service - API Optimization & Clean Code Suggestions

## 🎯 **API Response Speed Optimizations**

### 1. **Add Redis Response Caching**

```python
# apps/images/api/views.py - Add to ImageViewSet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.conf import settings

class ImageViewSet(viewsets.ModelViewSet):
    # ... existing code ...

    @method_decorator(cache_page(300))  # Cache for 5 minutes
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(600))  # Cache for 10 minutes
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        # Add query result caching
        cache_key = f"images_queryset_{hash(str(self.request.query_params))}"
        queryset = cache.get(cache_key)
        if queryset is None:
            queryset = super().get_queryset()
            cache.set(cache_key, queryset, 300)  # Cache for 5 minutes
        return queryset
```

### 2. **Optimize Pagination for Speed**

```python
# settings.py - Add pagination optimization
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
    'PAGE_SIZE': 50,  # Increase from default 20
    'MAX_PAGE_SIZE': 200,
}

# For large datasets, use cursor pagination instead of page numbers
```

### 3. **Add Database Query Optimization**

```python
# apps/images/api/views.py - Optimize ImageViewSet queryset
class ImageViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = Image.objects.select_related(
            'movie', 'color', 'shot_type', 'media_type'
        ).prefetch_related(
            'tags', 'genre'
        ).defer(  # Don't load heavy fields unless needed
            'dominant_colors', 'color_palette', 'color_histogram'
        )

        # Add query hints for better performance
        return queryset.extra(
            select={'has_tags': 'EXISTS(SELECT 1 FROM images_image_tags WHERE image_id = images_image.id)'},
            where=['has_tags = %s'],
            params=[True]
        )
```

### 4. **Implement Response Compression**

```python
# settings.py - Add response compression
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',  # Add this first
    # ... other middleware ...
]

# For API responses
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}
```

### 5. **Add Fast Serializers**

```python
# apps/images/api/serializers.py - Create lightweight serializers
class FastImageListSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    color_name = serializers.CharField(source='color.value', read_only=True)

    class Meta:
        model = Image
        fields = [
            'id', 'slug', 'title', 'image_url', 'movie_title',
            'color_name', 'created_at'
        ]

# Use different serializers based on endpoint
class ImageViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return FastImageListSerializer
        elif self.request.query_params.get('fast') == 'true':
            return FastImageListSerializer
        return ImageSerializer
```

## 🧹 **Clean Code Improvements**

### 1. **Extract Common Query Logic**

```python
# apps/images/api/queries.py - Create query utilities
class ImageQueryOptimizer:
    @staticmethod
    def get_optimized_queryset(base_filters=None):
        queryset = Image.objects.select_related(
            'movie', 'color', 'shot_type'
        ).prefetch_related('tags', 'genre')

        if base_filters:
            queryset = queryset.filter(**base_filters)

        return queryset

    @staticmethod
    def apply_common_filters(queryset, request):
        # Extract common filtering logic
        if request.query_params.get('recent'):
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=7))
        return queryset
```

### 2. **Create Service Layer**

```python
# apps/images/services/image_service.py
class ImageService:
    @staticmethod
    def get_images_with_metadata(filters=None, limit=100):
        queryset = Image.objects.select_related('movie', 'color')
        if filters:
            queryset = queryset.filter(**filters)
        return queryset[:limit]

    @staticmethod
    def bulk_update_image_metadata(image_ids, metadata):
        # Bulk update logic
        pass
```

### 3. **Add Type Hints and Documentation**

```python
# apps/images/api/views.py
from typing import Optional, Dict, Any, List
from django.http import HttpRequest
from rest_framework.request import Request
from rest_framework.response import Response

class ImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing images.

    Provides CRUD operations with advanced filtering and caching.
    """

    def list(self, request: Request, *args, **kwargs) -> Response:
        """List images with optimized performance."""
        # Implementation
        pass
```

### 4. **Implement Repository Pattern**

```python
# apps/images/repositories/image_repository.py
class ImageRepository:
    def __init__(self):
        self.model = Image

    def get_by_filters(self, filters: Dict[str, Any], limit: int = 100) -> QuerySet:
        return self.model.objects.filter(**filters)[:limit]

    def get_with_relations(self, image_id: int) -> Optional[Image]:
        return self.model.objects.select_related('movie').get(id=image_id)
```

## ⚡ **Performance Monitoring**

### 1. **Add Response Time Logging**

```python
# apps/images/middleware/performance_middleware.py
class PerformanceMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        if duration > 1.0:  # Log slow requests
            logger.warning(f"Slow request: {request.path} took {duration:.2f}s")

        response['X-Response-Time'] = str(duration)
        return response
```

### 2. **Database Query Monitoring**

```python
# settings.py
LOGGING = {
    'handlers': {
        'db_handler': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'db_queries.log',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['db_handler'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

## 🔄 **API Versioning & Deprecation**

```python
# apps/images/api/urls.py
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'images', views.ImageViewSet, basename='image')

# Versioned URLs
urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('api/v2/', include(router.urls)),  # Future version
]
```

## 📊 **Caching Strategy**

### 1. **Multi-Level Caching**

```python
# apps/images/cache.py
from django.core.cache import cache

class ImageCache:
    @staticmethod
    def get_image_list_cache_key(filters):
        return f"image_list:{hash(str(filters))}"

    @staticmethod
    def get_cached_image_list(filters, timeout=300):
        cache_key = ImageCache.get_image_list_cache_key(filters)
        return cache.get(cache_key)

    @staticmethod
    def set_cached_image_list(filters, data, timeout=300):
        cache_key = ImageCache.get_image_list_cache_key(filters)
        cache.set(cache_key, data, timeout)
```

### 2. **Cache Invalidation**

```python
# apps/images/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver([post_save, post_delete], sender=Image)
def invalidate_image_cache(sender, instance, **kwargs):
    # Invalidate related caches
    cache.delete_pattern("image_list:*")
    cache.delete(f"image_detail:{instance.id}")
```

## 🧪 **Testing Optimizations**

```python
# apps/images/tests/test_api_performance.py
import time
from django.test import TestCase
from rest_framework.test import APITestCase

class APIPerformanceTest(APITestCase):
    def test_image_list_performance(self):
        start_time = time.time()
        response = self.client.get('/api/images/')
        duration = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 1.0, "API response too slow")

    def test_cached_response_performance(self):
        # First request
        self.client.get('/api/images/')

        # Second request should be faster due to caching
        start_time = time.time()
        response = self.client.get('/api/images/')
        duration = time.time() - start_time

        self.assertLess(duration, 0.1, "Cached response too slow")
```
