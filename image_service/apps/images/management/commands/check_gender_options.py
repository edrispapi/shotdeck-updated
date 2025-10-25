#!/usr/bin/env python3
"""
Check gender options in the database
"""

import os
import sys
import django

# Add the Django project to the Python path
sys.path.append('/workspace/image_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.images.models import GenderOption, Image

def check_gender_options():
    print("=== GENDER OPTIONS CHECK ===")
    
    # Check if GenderOption model has any data
    gender_count = GenderOption.objects.count()
    print(f"Gender options count: {gender_count}")
    
    if gender_count > 0:
        print("Gender options found:")
        for gender in GenderOption.objects.all()[:10]:  # Show first 10
            print(f"  - {gender.id}: {gender.value}")
    else:
        print("No gender options found in database")
    
    # Check if any images have gender data
    images_with_gender = Image.objects.filter(gender__isnull=False).count()
    print(f"Images with gender data: {images_with_gender}")
    
    if images_with_gender > 0:
        print("Sample images with gender:")
        for img in Image.objects.filter(gender__isnull=False)[:5]:
            print(f"  - {img.slug}: {img.gender.value if img.gender else 'None'}")

if __name__ == "__main__":
    check_gender_options()