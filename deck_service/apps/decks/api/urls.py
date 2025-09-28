from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeckViewSet, DeckAPIRootView

router = DefaultRouter()
router.register(r'decks', DeckViewSet, basename='deck')

urlpatterns = [
    path('', DeckAPIRootView.as_view(), name='api-root'),
    path('', include(router.urls)),
]