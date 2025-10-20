#!/usr/bin/env python3
import sys
import os
sys.path.append('/service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.images.models import Image
from apps.images.api.serializers import ImageListSerializer
from django.test import RequestFactory

# Test the serializer directly
img = Image.objects.select_related('camera', 'lens', 'film_stock').filter(slug='70x0grj3-27ce7e4f9424').first()
if img:
    print(f'Direct database query:')
    print(f'  Camera: {img.camera.value if img.camera else None}')
    print(f'  Lens: {img.lens.value if img.lens else None}')
    print(f'  Film stock: {img.film_stock.value if img.film_stock else None}')
    
    # Test serializer
    factory = RequestFactory()
    request = factory.get('/api/images/')
    serializer = ImageListSerializer(img, context={'request': request})
    data = serializer.data
    
    print(f'\nSerializer output:')
    print(f'  Camera: {data.get("camera")}')
    print(f'  Camera value: {data.get("camera_value")}')
    print(f'  Lens: {data.get("lens")}')
    print(f'  Lens value: {data.get("lens_value")}')
    print(f'  Film stock: {data.get("film_stock")}')
    print(f'  Film stock value: {data.get("film_stock_value")}')
    
    # Check if the issue is with the API view
    print(f'\nChecking API view query:')
    api_images = Image.objects.all()[:1]
    for api_img in api_images:
        print(f'  API image camera: {api_img.camera.value if api_img.camera else None}')
        print(f'  API image lens: {api_img.lens.value if api_img.lens else None}')
        print(f'  API image film_stock: {api_img.film_stock.value if api_img.film_stock else None}')
