from rest_framework import viewsets, permissions
from apps.images.models import Image
from .serializers import ImageSerializer

# --- تغییر کلیدی: ایمپورت از پکیج جدید messaging ---
from messaging.producers import send_event

class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all().order_by('-created_at')
    serializer_class = ImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def perform_destroy(self, instance):
        image_id = instance.id
        instance.delete()
        send_event('image_deleted', {'id': image_id})