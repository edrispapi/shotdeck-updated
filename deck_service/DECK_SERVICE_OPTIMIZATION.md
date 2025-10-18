# 🎬 Deck Service - Performance & Clean Code Optimization Guide

## 🎯 **API Response Speed Optimizations**

### 1. **Add Response Caching & Compression**

```python
# deck_service/core/settings.py - Add performance middleware
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',  # Response compression
    'deck_service.middleware.PerformanceMonitoringMiddleware',
    # ... other middleware ...
]

# Add Redis caching configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    }
}

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
    'PAGE_SIZE': 50,
}
```

### 2. **Optimize Database Queries**

```python
# deck_service/apps/deck/views.py - Add query optimization
from django.db.models import Prefetch, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

class DeckViewSet(viewsets.ModelViewSet):
    queryset = Deck.objects.select_related(
        'user', 'project'
    ).prefetch_related(
        'cards__image',
        'cards__text_elements',
        Prefetch('collaborators', queryset=User.objects.only('id', 'username'))
    )

    @method_decorator(cache_page(300))  # 5 minute cache
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        # Add efficient filtering
        user = self.request.user
        if not user.is_staff:
            queryset = queryset.filter(
                Q(user=user) | Q(collaborators=user) | Q(is_public=True)
            )

        # Optimize ordering for common queries
        ordering = self.request.query_params.get('ordering', '-updated_at')
        if ordering in ['-updated_at', '-created_at', 'title']:
            queryset = queryset.order_by(ordering)

        return queryset
```

### 3. **Implement Fast Serializers**

```python
# deck_service/apps/deck/serializers.py
class FastDeckListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    card_count = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = [
            'id', 'slug', 'title', 'description', 'user_name',
            'card_count', 'thumbnail_url', 'is_public', 'updated_at'
        ]

    def get_card_count(self, obj):
        return obj.cards.count()

    def get_thumbnail_url(self, obj):
        first_card = obj.cards.first()
        return first_card.image.url if first_card and first_card.image else None

class DeckViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return FastDeckListSerializer
        elif self.request.query_params.get('fast') == 'true':
            return FastDeckListSerializer
        return DeckSerializer
```

## 🚀 **Real-time Features Optimization**

### 1. **WebSocket Connection Optimization**

```python
# deck_service/deck_service/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
import json
import asyncio

class OptimizedDeckConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.deck_id = self.scope['url_route']['kwargs']['deck_id']
        self.group_name = f'deck_{self.deck_id}'

        # Add to group with connection limits
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send initial deck state efficiently
        deck_data = await self.get_deck_data()
        await self.send_json({
            'type': 'deck_state',
            'data': deck_data
        })

    @database_sync_to_async
    def get_deck_data(self):
        """Optimized deck data retrieval"""
        return Deck.objects.select_related('user').prefetch_related(
            'cards__image'
        ).filter(id=self.deck_id).values(
            'id', 'title', 'user__username', 'cards__id', 'cards__image__url'
        ).first()

    async def receive_json(self, content):
        """Handle incoming messages with rate limiting"""
        message_type = content.get('type')

        # Rate limiting
        if hasattr(self, '_last_message_time'):
            if time.time() - self._last_message_time < 0.1:  # 100ms rate limit
                return

        self._last_message_time = time.time()

        if message_type == 'move_card':
            await self.handle_card_move(content)
        elif message_type == 'update_text':
            await self.handle_text_update(content)

    async def handle_card_move(self, content):
        """Optimized card movement handling"""
        card_id = content['card_id']
        position = content['position']

        # Update in database
        updated = await self.update_card_position(card_id, position)
        if updated:
            # Broadcast to group (excluding sender)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'card_moved',
                    'card_id': card_id,
                    'position': position,
                    'sender_channel': self.channel_name
                }
            )

    async def card_moved(self, event):
        """Receive card movement broadcasts"""
        if event['sender_channel'] != self.channel_name:
            await self.send_json({
                'type': 'card_moved',
                'card_id': event['card_id'],
                'position': event['position']
            })

    @database_sync_to_async
    def update_card_position(self, card_id, position):
        """Efficient database update"""
        return Card.objects.filter(id=card_id).update(position=position)
```

### 2. **Background Task Optimization**

```python
# deck_service/deck_service/tasks.py
from celery import shared_task
from django.core.cache import cache
from .services.deck_service import DeckService

@shared_task(bind=True, max_retries=3)
def export_deck_task(self, deck_id, format_type, user_id):
    """Optimized deck export task"""
    try:
        service = DeckService()

        # Check cache first
        cache_key = f"deck_export:{deck_id}:{format_type}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        # Generate export
        result = service.export_deck(deck_id, format_type, user_id)

        # Cache result for 1 hour
        cache.set(cache_key, result, 3600)

        return result

    except Exception as e:
        logger.error(f"Deck export failed: {e}")
        raise self.retry(countdown=60)

@shared_task
def cleanup_expired_decks():
    """Clean up old temporary decks"""
    from django.utils import timezone
    from datetime import timedelta

    expiry_date = timezone.now() - timedelta(days=30)
    expired_decks = Deck.objects.filter(
        is_temporary=True,
        created_at__lt=expiry_date
    )

    count = expired_decks.delete()[0]
    logger.info(f"Cleaned up {count} expired temporary decks")
```

## 🧹 **Clean Code Architecture**

### 1. **Service Layer Pattern**

```python
# deck_service/apps/deck/services/deck_service.py
from typing import Dict, List, Optional
from django.db import transaction
from ..models import Deck, Card, TextElement

class DeckService:
    """Business logic service for deck operations"""

    @staticmethod
    def create_deck_with_cards(user, title: str, card_data: List[Dict]) -> Deck:
        """Create deck with cards in single transaction"""
        with transaction.atomic():
            deck = Deck.objects.create(user=user, title=title)

            cards = []
            for card_info in card_data:
                card = Card(
                    deck=deck,
                    image_id=card_info.get('image_id'),
                    position=card_info.get('position', 0)
                )
                cards.append(card)

            Card.objects.bulk_create(cards)
            return deck

    @staticmethod
    def duplicate_deck(deck_id: int, user) -> Optional[Deck]:
        """Efficient deck duplication"""
        try:
            original_deck = Deck.objects.select_related('user').get(id=deck_id)

            # Duplicate deck
            new_deck = Deck.objects.create(
                user=user,
                title=f"{original_deck.title} (Copy)",
                description=original_deck.description
            )

            # Bulk duplicate cards
            original_cards = list(original_deck.cards.all())
            new_cards = []
            for card in original_cards:
                new_cards.append(Card(
                    deck=new_deck,
                    image=card.image,
                    position=card.position
                ))

            Card.objects.bulk_create(new_cards)
            return new_deck

        except Deck.DoesNotExist:
            return None

    @staticmethod
    def get_deck_with_optimized_queries(deck_id: int) -> Optional[Deck]:
        """Get deck with optimized queries"""
        return Deck.objects.select_related('user').prefetch_related(
            'cards__image',
            'cards__text_elements'
        ).get(id=deck_id)
```

### 2. **Repository Pattern**

```python
# deck_service/apps/deck/repositories/deck_repository.py
from typing import List, Dict, Optional
from django.db.models import Q, Count
from ..models import Deck, Card

class DeckRepository:
    """Data access layer for decks"""

    def get_user_decks(self, user, include_public: bool = True) -> List[Deck]:
        """Get user's decks with optimized query"""
        queryset = Deck.objects.select_related('user')

        if include_public:
            queryset = queryset.filter(Q(user=user) | Q(is_public=True))
        else:
            queryset = queryset.filter(user=user)

        return queryset.order_by('-updated_at')

    def get_deck_with_stats(self, deck_id: int) -> Optional[Dict]:
        """Get deck with computed statistics"""
        deck = Deck.objects.select_related('user').annotate(
            card_count=Count('cards'),
            collaborator_count=Count('collaborators')
        ).filter(id=deck_id).first()

        if deck:
            return {
                'deck': deck,
                'card_count': deck.card_count,
                'collaborator_count': deck.collaborator_count
            }
        return None

    def bulk_update_card_positions(self, position_updates: Dict[int, int]) -> int:
        """Bulk update card positions efficiently"""
        cards_to_update = []
        for card_id, position in position_updates.items():
            cards_to_update.append(Card(id=card_id, position=position))

        return Card.objects.bulk_update(cards_to_update, ['position'])
```

### 3. **Event-Driven Architecture**

```python
# deck_service/apps/deck/events.py
from typing import Dict, Any
from django.dispatch import Signal

# Define signals
deck_created = Signal()
deck_updated = Signal()
card_moved = Signal()
collaborator_added = Signal()

class DeckEventHandler:
    """Handle deck-related events"""

    @staticmethod
    def on_deck_created(sender, deck, **kwargs):
        """Handle deck creation events"""
        # Invalidate caches
        cache.delete_pattern(f"deck_list:{deck.user.id}:*")

        # Send notifications
        NotificationService.notify_collaborators(deck, 'deck_created')

        # Update search index
        SearchService.index_deck(deck)

    @staticmethod
    def on_card_moved(sender, card, old_position, new_position, **kwargs):
        """Handle card movement events"""
        # Update deck timestamp
        card.deck.save(update_fields=['updated_at'])

        # Broadcast via WebSocket
        WebSocketService.broadcast_card_move(card.deck.id, card.id, new_position)

# Connect signal handlers
deck_created.connect(DeckEventHandler.on_deck_created)
card_moved.connect(DeckEventHandler.on_card_moved)
```

## ⚡ **Performance Monitoring**

### 1. **Request Performance Middleware**

```python
# deck_service/deck_service/middleware/performance_middleware.py
import time
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class PerformanceMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        duration = time.time() - start_time

        # Log slow requests
        if duration > 1.0:
            logger.warning(
                f'Slow request: {request.method} {request.path} '
                f'took {duration:.2f}s from {request.META.get("REMOTE_ADDR")}'
            )

        # Add performance headers
        response['X-Response-Time'] = str(duration)
        response['X-Server-Timing'] = f'total;dur={duration*1000}'

        return response
```

### 2. **Database Query Monitoring**

```python
# deck_service/deck_service/middleware/query_middleware.py
from django.db import connection
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class QueryMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Reset queries
        connection.queries_log.clear()

        response = self.get_response(request)

        # Log slow queries
        total_time = 0
        slow_queries = []

        for query in connection.queries:
            query_time = float(query['time'])
            total_time += query_time

            if query_time > 0.1:  # Log queries taking > 100ms
                slow_queries.append(query)

        if slow_queries:
            logger.warning(
                f'Slow queries in {request.path}: {len(slow_queries)} queries '
                f'taking {total_time:.2f}s total'
            )

            for query in slow_queries[:5]:  # Log first 5 slow queries
                logger.warning(f'  {query["time"]}s: {query["sql"][:200]}...')

        # Add query count header
        response['X-Query-Count'] = str(len(connection.queries))
        response['X-Query-Time'] = str(total_time)

        return response
```

## 🔄 **Caching Strategy**

### 1. **Multi-Level Caching**

```python
# deck_service/apps/deck/cache.py
from django.core.cache import cache
import hashlib

class DeckCacheManager:
    @staticmethod
    def get_deck_cache_key(deck_id: int, user_id: int = None) -> str:
        """Generate cache key for deck data"""
        if user_id:
            return f"deck:{deck_id}:user:{user_id}"
        return f"deck:{deck_id}"

    @staticmethod
    def get_deck_list_cache_key(user_id: int, page: int = 1) -> str:
        """Generate cache key for deck list"""
        return f"deck_list:{user_id}:page:{page}"

    @staticmethod
    def get_cached_deck(deck_id: int, user_id: int = None, timeout: int = 600):
        """Get cached deck data"""
        cache_key = DeckCacheManager.get_deck_cache_key(deck_id, user_id)
        return cache.get(cache_key)

    @staticmethod
    def set_cached_deck(deck_id: int, data: Dict, user_id: int = None, timeout: int = 600):
        """Cache deck data"""
        cache_key = DeckCacheManager.get_deck_cache_key(deck_id, user_id)
        cache.set(cache_key, data, timeout)

    @staticmethod
    def invalidate_deck_cache(deck_id: int):
        """Invalidate all cache entries for a deck"""
        cache.delete_pattern(f"deck:{deck_id}:*")
        cache.delete_pattern(f"deck_list:*:deck:{deck_id}")
```

### 2. **Cache Invalidation Signals**

```python
# deck_service/apps/deck/signals.py
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Deck, Card

@receiver([post_save, post_delete], sender=Deck)
def invalidate_deck_cache(sender, instance, **kwargs):
    """Invalidate deck-related caches"""
    cache.delete_pattern(f"deck:{instance.id}:*")
    cache.delete_pattern(f"deck_list:{instance.user.id}:*")

@receiver([post_save, post_delete], sender=Card)
def invalidate_card_cache(sender, instance, **kwargs):
    """Invalidate card-related caches"""
    cache.delete_pattern(f"deck:{instance.deck.id}:*")

@receiver(m2m_changed, sender=Deck.collaborators.through)
def invalidate_collaborator_cache(sender, instance, **kwargs):
    """Invalidate collaborator-related caches"""
    cache.delete_pattern(f"deck:{instance.id}:*")
    cache.delete_pattern("deck_list:*")
```

## 🧪 **Testing Optimizations**

### 1. **Performance Testing Suite**

```python
# deck_service/apps/deck/tests/test_performance.py
import time
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from django.core.cache import cache

class DeckPerformanceTest(APITestCase):
    def setUp(self):
        # Clear cache before each test
        cache.clear()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

    def test_deck_list_performance(self):
        """Test deck list API performance"""
        # Create test data
        for i in range(100):
            Deck.objects.create(user=self.user, title=f"Test Deck {i}")

        start_time = time.time()
        response = self.client.get('/api/decks/')
        duration = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 0.5, "Deck list API too slow")

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_cached_deck_performance(self):
        """Test cached deck retrieval performance"""
        deck = Deck.objects.create(user=self.user, title="Test Deck")

        # First request (uncached)
        self.client.get(f'/api/decks/{deck.id}/')

        # Second request (cached)
        start_time = time.time()
        response = self.client.get(f'/api/decks/{deck.id}/')
        duration = time.time() - start_time

        self.assertLess(duration, 0.05, "Cached deck retrieval too slow")

    def test_bulk_card_update_performance(self):
        """Test bulk card update performance"""
        deck = Deck.objects.create(user=self.user, title="Test Deck")

        # Create cards
        cards = []
        for i in range(50):
            cards.append(Card.objects.create(deck=deck, position=i))

        # Update positions
        position_updates = {card.id: i + 10 for i, card in enumerate(cards)}

        start_time = time.time()
        from ..repositories.deck_repository import DeckRepository
        repo = DeckRepository()
        updated_count = repo.bulk_update_card_positions(position_updates)
        duration = time.time() - start_time

        self.assertEqual(updated_count, 50)
        self.assertLess(duration, 0.1, "Bulk update too slow")
```

### 2. **Load Testing**

```python
# deck_service/load_tests/test_concurrent_users.py
import concurrent.futures
import requests
import time
import statistics

def test_concurrent_deck_access():
    """Test concurrent deck access performance"""
    base_url = "http://localhost:8000/api/decks/"
    auth_headers = {"Authorization": "Bearer test_token"}

    def single_request(session_id):
        start_time = time.time()
        response = requests.get(f"{base_url}?page={session_id}", headers=auth_headers)
        end_time = time.time()

        return {
            'status_code': response.status_code,
            'response_time': end_time - start_time,
            'session_id': session_id
        }

    # Test with 50 concurrent users
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(single_request, i) for i in range(50)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    # Analyze results
    response_times = [r['response_time'] for r in results]
    success_count = sum(1 for r in results if r['status_code'] == 200)

    print(f"Concurrent users: 50")
    print(f"Success rate: {success_count/50*100:.1f}%")
    print(f"Average response time: {statistics.mean(response_times):.3f}s")
    print(f"95th percentile: {statistics.quantiles(response_times, n=20)[18]:.3f}s")

    assert success_count >= 45, "Too many failed requests"
    assert statistics.mean(response_times) < 2.0, "Average response time too slow"
```

This comprehensive optimization guide provides the foundation for a high-performance, scalable deck service with real-time features, clean architecture, and efficient caching strategies.
