from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from apps.decks.models import Deck
from .serializers import DeckSerializer
from drf_spectacular.utils import extend_schema

class IsOwner(permissions.BasePermission):
    """
    Custom permission to ensure only the owner of an object can edit it.
    """
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class DeckAPIRootView(APIView):
    """
    API root for Deck Service
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "decks": "/api/decks/",
            "service": "Deck Service API",
            "version": "1.0.0",
            "description": "API for managing image decks and collections"
        })

@extend_schema(tags=['Deck CRUD Operations'])
class DeckViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing, creating, updating, and deleting Decks.
    Only the owner of a deck can edit or delete it.
    GET requests are allowed without authentication for testing.
    """
    serializer_class = DeckSerializer

    def get_permissions(self):
        """
        Allow GET requests without authentication, but require auth for other methods
        """
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsOwner()]

    def get_queryset(self):
        """
        This view should only return Decks related to the logged-in user.
        For GET requests without authentication, it returns all decks.
        """
        if self.request.method == 'GET' and not self.request.user.is_authenticated:
            return Deck.objects.all()
        return Deck.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """
        When creating a new Deck, sets the current user as its owner.
        """
        serializer.save(owner=self.request.user)
