#!/usr/bin/env python3
"""
Add sample gender options to the database
"""

import os
import sys
import django

# Add the Django project to the Python path
sys.path.append('/home/a/shotdeck-main/image_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.images.models import GenderOption

def add_sample_gender_options():
    print("=== ADDING SAMPLE GENDER OPTIONS ===")
    
    # Sample gender options
    gender_options = [
        'Male',
        'Female',
        'Non-binary',
        'Other',
        'Not specified'
    ]
    
    created_count = 0
    
    for gender_value in gender_options:
        gender_option, created = GenderOption.objects.get_or_create(
            value=gender_value,
            defaults={
                'display_order': created_count + 1,
                'metadata': {}
            }
        )
        
        if created:
            print(f"Created gender option: {gender_value}")
            created_count += 1
        else:
            print(f"Gender option already exists: {gender_value}")
    
    print(f"Total gender options created: {created_count}")
    print(f"Total gender options in database: {GenderOption.objects.count()}")

if __name__ == "__main__":
    add_sample_gender_options()