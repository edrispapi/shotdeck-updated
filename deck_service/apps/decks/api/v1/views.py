from rest_framework import viewsets, permissions
from apps.decks.models import Deck
from .serializers import DeckSerializer
from drf_spectacular.utils import extend_schema

class IsOwner(permissions.BasePermission):
    """
    دسترسی سفارشی برای اینکه فقط مالک یک آبجکت بتواند آن را ویرایش کند.
    """
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

@extend_schema(tags=['Deck CRUD Operations'])
class DeckViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing, creating, updating, and deleting Decks.
    Only the owner of a deck can edit or delete it.
    """
    serializer_class = DeckSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        """
        این view فقط باید Deck های مربوط به کاربر لاگین کرده را برگرداند.
        """
        return Deck.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """
        هنگام ایجاد یک Deck جدید، مالک آن را کاربر فعلی قرار می‌دهد.
        """
        serializer.save(owner=self.request.user)