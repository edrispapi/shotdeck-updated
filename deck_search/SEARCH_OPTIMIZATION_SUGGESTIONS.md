# 🔍 Deck Search Service - Search & Performance Optimization Guide

## 🎯 **Search Performance Optimizations**

### 1. **Elasticsearch Query Optimization**

```python
# deck_search_utils/search/search_service.py
from elasticsearch_dsl import Q, Search
from elasticsearch.helpers import bulk
from django.core.cache import cache

class OptimizedSearchService:
    def __init__(self):
        self.es_client = Elasticsearch()
        self.cache_timeout = 300  # 5 minutes

    def search_with_caching(self, query: str, filters: Dict = None, page: int = 1, size: int = 20):
        """Search with multi-level caching"""
        cache_key = self._generate_cache_key(query, filters, page, size)

        # Check Redis cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        # Perform Elasticsearch search
        result = self._perform_es_search(query, filters, page, size)

        # Cache the result
        cache.set(cache_key, result, self.cache_timeout)

        return result

    def _perform_es_search(self, query: str, filters: Dict = None, page: int = 1, size: int = 20):
        """Optimized Elasticsearch query"""
        search = Search(using=self.es_client, index='images')

        # Build query with filters
        must_queries = [Q('multi_match', query=query, fields=['title^3', 'description^2', 'tags'])]
        filter_queries = []

        if filters:
            for field, values in filters.items():
                if isinstance(values, list):
                    filter_queries.append(Q('terms', **{field: values}))
                else:
                    filter_queries.append(Q('term', **{field: values}))

        # Combine queries
        search = search.query(Q('bool', must=must_queries, filter=filter_queries))

        # Add aggregations for facets
        search.aggs.bucket('genres', 'terms', field='genre.keyword', size=50)
        search.aggs.bucket('colors', 'terms', field='color.keyword', size=20)

        # Pagination with cursor-based approach for better performance
        search = search[(page-1)*size:page*size]

        # Execute search
        response = search.execute()

        return self._format_search_response(response)

    def _generate_cache_key(self, query: str, filters: Dict, page: int, size: int) -> str:
        """Generate consistent cache key"""
        key_parts = [query, str(sorted(filters.items())), str(page), str(size)]
        return f"search:{hash(''.join(key_parts))}"
```

### 2. **Search Result Caching Strategy**

```python
# deck_search/apps/search/caching.py
from django.core.cache import cache
from django.conf import settings

class SearchCacheManager:
    def __init__(self):
        self.search_timeout = 600  # 10 minutes for search results
        self.facets_timeout = 3600  # 1 hour for facets

    def get_search_cache(self, query_hash: str):
        """Get cached search results"""
        return cache.get(f"search_result:{query_hash}")

    def set_search_cache(self, query_hash: str, results: Dict):
        """Cache search results"""
        cache.set(f"search_result:{query_hash}", results, self.search_timeout)

    def get_facets_cache(self, filter_hash: str):
        """Get cached facet data"""
        return cache.get(f"search_facets:{filter_hash}")

    def set_facets_cache(self, filter_hash: str, facets: Dict):
        """Cache facet data"""
        cache.set(f"search_facets:{filter_hash}", facets, self.facets_timeout)

    def invalidate_search_cache(self, pattern: str = "*"):
        """Invalidate search cache patterns"""
        cache.delete_pattern(f"search_result:{pattern}")
        cache.delete_pattern(f"search_facets:{pattern}")
```

### 3. **Database Query Optimization for Search**

```python
# deck_search/apps/search/models.py
class SearchQuery(models.Model):
    query = models.CharField(max_length=500)
    filters = models.JSONField()
    results_count = models.IntegerField()
    search_time = models.FloatField()
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['query'], name='search_query_idx'),
            models.Index(fields=['created_at'], name='search_created_idx'),
            models.Index(fields=['user', 'created_at'], name='search_user_created_idx'),
        ]

# Add performance indexes
class ImageDocument:
    class Meta:
        # Elasticsearch mappings optimization
        mappings = {
            'properties': {
                'title': {'type': 'text', 'analyzer': 'standard', 'boost': 3.0},
                'description': {'type': 'text', 'analyzer': 'standard', 'boost': 2.0},
                'tags': {'type': 'keyword', 'normalizer': 'lowercase'},
                'genre': {'type': 'keyword'},
                'color': {'type': 'keyword'},
                'created_at': {'type': 'date'},
            }
        }
```

## 🚀 **API Response Speed Optimizations**

### 1. **Fast Search Endpoints**

```python
# deck_search/apps/search/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache

class SearchViewSet(viewsets.ViewSet):
    """Optimized search API endpoints"""

    @method_decorator(cache_page(300))  # Cache for 5 minutes
    def search(self, request):
        """Fast search endpoint with caching"""
        query = request.query_params.get('q', '')
        filters = self._extract_filters(request)

        # Check cache first
        cache_key = f"search:{hash(query + str(filters))}"
        cached_result = cache.get(cache_key)

        if cached_result:
            return Response(cached_result)

        # Perform search
        search_service = OptimizedSearchService()
        results = search_service.search(query, filters)

        # Cache results
        cache.set(cache_key, results, 300)

        return Response(results)

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(600))  # Cache facets longer
    def facets(self, request):
        """Fast facets endpoint"""
        filters = self._extract_filters(request)

        # Get facets with caching
        facet_service = FacetService()
        facets = facet_service.get_facets(filters)

        return Response(facets)

    def _extract_filters(self, request) -> Dict:
        """Extract filters from request"""
        return {
            'genre': request.query_params.getlist('genre'),
            'color': request.query_params.getlist('color'),
            'year': request.query_params.getlist('year'),
        }
```

### 2. **Streaming Responses for Large Results**

```python
# deck_search/apps/search/views.py
from rest_framework.response import StreamingHttpResponse
import json

class StreamingSearchViewSet(viewsets.ViewSet):
    def search_stream(self, request):
        """Stream search results for large datasets"""
        def generate_results():
            search_service = OptimizedSearchService()
            results = search_service.search_with_pagination(
                request.query_params.get('q', ''),
                page_size=100
            )

            for page in results:
                yield json.dumps(page) + '\n'

        return StreamingHttpResponse(
            generate_results(),
            content_type='application/json'
        )
```

### 3. **Autocomplete Optimization**

```python
# deck_search/apps/search/autocomplete.py
from elasticsearch_dsl import Completion
from django.core.cache import cache

class AutocompleteService:
    def __init__(self):
        self.cache_timeout = 1800  # 30 minutes

    def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Fast autocomplete suggestions"""
        cache_key = f"autocomplete:{query[:50]}"  # Limit key length

        # Check cache
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Elasticsearch completion suggester
        search = Search(using=Elasticsearch(), index='images')
        search = search.suggest(
            'title_suggest',
            query,
            completion={
                'field': 'title.suggest',
                'size': limit,
                'skip_duplicates': True
            }
        )

        response = search.execute()
        suggestions = [
            option.text
            for suggestion in response.suggest.title_suggest
            for option in suggestion.options
        ]

        # Cache results
        cache.set(cache_key, suggestions, self.cache_timeout)

        return suggestions
```

## 🧹 **Clean Code Improvements**

### 1. **Service Layer Architecture**

```python
# deck_search/apps/search/services/__init__.py
from .search_service import SearchService
from .facet_service import FacetService
from .autocomplete_service import AutocompleteService

# deck_search/apps/search/services/search_service.py
class SearchService:
    def __init__(self, es_client=None):
        self.es_client = es_client or Elasticsearch()

    def search(self, query: str, filters: Dict = None) -> Dict:
        """Clean search interface"""
        # Implementation
        pass

    def advanced_search(self, query_dsl: Dict) -> Dict:
        """Advanced search with custom DSL"""
        # Implementation
        pass
```

### 2. **Repository Pattern for Data Access**

```python
# deck_search/apps/search/repositories/search_repository.py
class SearchRepository:
    def __init__(self):
        self.es_client = Elasticsearch()

    def save_document(self, document: Dict, index: str, doc_id: str):
        """Save document to Elasticsearch"""
        return self.es_client.index(index=index, id=doc_id, body=document)

    def bulk_save_documents(self, documents: List[Dict], index: str):
        """Bulk save documents"""
        actions = [
            {
                '_index': index,
                '_id': doc.get('id'),
                '_source': doc
            }
            for doc in documents
        ]
        return bulk(self.es_client, actions)

    def search_documents(self, query: Dict, index: str) -> Dict:
        """Search documents"""
        return self.es_client.search(index=index, body=query)
```

### 3. **Configuration Management**

```python
# deck_search/config/search_config.py
class SearchConfig:
    # Elasticsearch settings
    ES_HOSTS = ['localhost:9200']
    ES_INDEX_PREFIX = 'shotdeck'
    ES_TIMEOUT = 30

    # Cache settings
    CACHE_TIMEOUT_SEARCH = 300
    CACHE_TIMEOUT_FACETS = 3600
    CACHE_TIMEOUT_AUTOCOMPLETE = 1800

    # Search settings
    MAX_RESULTS_PER_PAGE = 100
    DEFAULT_PAGE_SIZE = 20
    MAX_SEARCH_DEPTH = 10000

    # Facet settings
    MAX_FACET_SIZE = 50
    FACET_CACHE_TIMEOUT = 3600
```

## ⚡ **Performance Monitoring & Analytics**

### 1. **Search Performance Tracking**

```python
# deck_search/apps/search/analytics.py
import time
from django.db import models

class SearchAnalytics(models.Model):
    query = models.CharField(max_length=500)
    filters = models.JSONField()
    result_count = models.IntegerField()
    search_time = models.FloatField()
    es_query_time = models.FloatField()
    user_agent = models.TextField()
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_at'], name='analytics_created_idx'),
            models.Index(fields=['query'], name='analytics_query_idx'),
            models.Index(fields=['search_time'], name='analytics_time_idx'),
        ]

class SearchPerformanceMonitor:
    def __init__(self):
        self.metrics = {}

    def track_search(self, query: str, filters: Dict, result_count: int, search_time: float):
        """Track search performance"""
        # Store in database for analysis
        SearchAnalytics.objects.create(
            query=query,
            filters=filters,
            result_count=result_count,
            search_time=search_time,
            es_query_time=search_time  # Could be more granular
        )

        # Update real-time metrics
        self._update_metrics(search_time, result_count)

    def _update_metrics(self, search_time: float, result_count: int):
        """Update performance metrics"""
        if 'avg_search_time' not in self.metrics:
            self.metrics['avg_search_time'] = search_time
            self.metrics['total_searches'] = 1
        else:
            self.metrics['avg_search_time'] = (
                self.metrics['avg_search_time'] * self.metrics['total_searches'] + search_time
            ) / (self.metrics['total_searches'] + 1)
            self.metrics['total_searches'] += 1
```

### 2. **Elasticsearch Performance Monitoring**

```python
# deck_search/apps/search/monitoring.py
from elasticsearch.client import ClusterClient

class ElasticsearchMonitor:
    def __init__(self):
        self.es_client = Elasticsearch()
        self.cluster_client = ClusterClient(self.es_client)

    def get_cluster_health(self) -> Dict:
        """Get Elasticsearch cluster health"""
        return self.cluster_client.health()

    def get_index_stats(self, index: str) -> Dict:
        """Get index performance statistics"""
        return self.es_client.indices.stats(index=index)

    def get_search_performance(self) -> Dict:
        """Get search performance metrics"""
        stats = self.es_client.search(
            index='_all',
            body={
                'size': 0,
                'aggs': {
                    'avg_query_time': {'avg': {'field': 'took'}}
                }
            }
        )
        return stats
```

## 🔄 **Real-time Features**

### 1. **WebSocket Search Updates**

```python
# deck_search/apps/search/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class SearchConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('search_updates', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('search_updates', self.channel_name)

    async def receive_json(self, content):
        """Handle search requests via WebSocket"""
        query = content.get('query', '')
        filters = content.get('filters', {})

        # Perform search asynchronously
        search_service = OptimizedSearchService()
        results = await search_service.search_async(query, filters)

        # Send results back
        await self.send_json({
            'type': 'search_results',
            'results': results
        })
```

### 2. **Background Search Indexing**

```python
# deck_search/apps/search/tasks.py
from celery import shared_task
from .services.index_service import IndexService

@shared_task
def update_search_index(image_ids: List[int]):
    """Background task to update search index"""
    index_service = IndexService()
    index_service.bulk_update_images(image_ids)

@shared_task
def optimize_search_index():
    """Periodic index optimization"""
    index_service = IndexService()
    index_service.optimize_index()
```

## 📊 **Testing & Quality Assurance**

### 1. **Performance Testing**

```python
# deck_search/apps/search/tests/test_performance.py
import time
from django.test import TestCase
from rest_framework.test import APITestCase

class SearchPerformanceTest(APITestCase):
    def test_search_response_time(self):
        """Test search response time"""
        start_time = time.time()
        response = self.client.get('/api/search/?q=test')
        duration = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 0.5, "Search too slow")

    def test_cached_search_performance(self):
        """Test cached search performance"""
        # First request
        self.client.get('/api/search/?q=test')

        # Second request should be much faster
        start_time = time.time()
        response = self.client.get('/api/search/?q=test')
        duration = time.time() - start_time

        self.assertLess(duration, 0.1, "Cached search too slow")

    def test_autocomplete_performance(self):
        """Test autocomplete response time"""
        start_time = time.time()
        response = self.client.get('/api/search/autocomplete/?q=test')
        duration = time.time() - start_time

        self.assertLess(duration, 0.2, "Autocomplete too slow")
```

This comprehensive optimization guide provides the foundation for a high-performance, scalable search service with clean, maintainable code architecture.
