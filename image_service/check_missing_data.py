#!/usr/bin/env python3
import sys
import os
sys.path.append('/service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.images.models import Image
import json

# Check a few different images to see if any have more complete data
sample_images = Image.objects.all()[:3]

for img in sample_images:
    imageid = img.slug.split('-')[0].upper()
    json_file = f'/host_data/dataset/shot_json_data/{imageid}.json'
    
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        details = data.get('data', {}).get('details', {})
        shot_info = details.get('shot_info', {})
        
        print(f'\nImage {img.slug}:')
        print(f'  Camera: {shot_info.get("camera", {}).get("values", [])}')
        print(f'  Lens: {shot_info.get("lens", {}).get("values", [])}')
        print(f'  Film stock: {shot_info.get("film_stock", {}).get("values", [])}')
        print(f'  VFX backing: {shot_info.get("vfx_backing", {}).get("values", [])}')
        print(f'  Artist: {shot_info.get("artist", {}).get("values", [])}')
        print(f'  Number of people: {shot_info.get("number_of_people", {}).get("values", [])}')
        print(f'  Gender: {shot_info.get("gender", {}).get("values", [])}')
        print(f'  Age: {shot_info.get("age", {}).get("values", [])}')
        print(f'  Ethnicity: {shot_info.get("ethnicity", {}).get("values", [])}')
        print(f'  Camera type: {shot_info.get("camera_type", {}).get("values", [])}')
        print(f'  Resolution: {shot_info.get("resolution", {}).get("values", [])}')
        print(f'  Frame rate: {shot_info.get("frame_rate", {}).get("values", [])}')
