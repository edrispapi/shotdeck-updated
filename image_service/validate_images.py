import os
import json
import hashlib
from pathlib import Path
from apps.images.models import Image
from django.conf import settings

def validate_image_data():
    print('=== IMAGE DATA VALIDATION ===\n')
    
    # 1. Count images
    total_db = Image.objects.count()
    print(f'Total images in database: {total_db}')
    
    # 2. Check for missing image_urls
    missing_urls = Image.objects.filter(image_url='').count()
    print(f'Images without URL: {missing_urls}')
    
    # 3. Check file existence
    media_path = Path(settings.MEDIA_ROOT)
    images_with_files = 0
    images_without_files = 0
    
    print('\nChecking file existence (sample)...')
    for img in Image.objects.all()[:100]:
        if img.image_url:
            file_path = media_path / img.image_url.lstrip('/media/')
            if file_path.exists():
                images_with_files += 1
            else:
                images_without_files += 1
                print(f'  MISSING: {img.slug} -> {img.image_url}')
    
    print(f'\nSample check: {images_with_files}/100 files exist')
    
    # 4. Check slug-to-imageid mapping
    print('\nValidating slug format...')
    for img in Image.objects.all()[:10]:
        slug_base = img.slug.split('-')[0].upper()
        print(f'  {img.slug} -> expected ID: {slug_base}')
    
    # 5. Check for duplicates
    from django.db.models import Count
    duplicates = Image.objects.values('slug').annotate(count=Count('id')).filter(count__gt=1)
    print(f'\nDuplicate slugs: {duplicates.count()}')
    
    return {
        'total': total_db,
        'missing_urls': missing_urls,
        'files_exist_rate': images_with_files
    }

if __name__ == '__main__':
    import django
    django.setup()
    validate_image_data()
