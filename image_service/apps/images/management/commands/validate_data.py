from django.core.management.base import BaseCommand
from apps.images.models import Image
from pathlib import Path
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Validate image data integrity'
    
    def handle(self, *args, **options):
        self.stdout.write('=== IMAGE DATA VALIDATION ===\n')
        
        # 1. Basic counts
        total = Image.objects.count()
        self.stdout.write(f'Total images in DB: {total}')
        
        # 2. Check for empty URLs
        missing_urls = Image.objects.filter(image_url='').count()
        self.stdout.write(f'Images without URL: {missing_urls}')
        
        # 3. Check file existence (sample)
        media_root = settings.MEDIA_ROOT
        exists_count = 0
        missing_count = 0
        
        self.stdout.write('\nChecking file existence (first 100)...')
        for img in Image.objects.all()[:100]:
            if img.image_url:
                # Remove /media/ prefix and check if file exists
                file_path = os.path.join(media_root, img.image_url.replace('/media/', ''))
                if os.path.exists(file_path):
                    exists_count += 1
                else:
                    missing_count += 1
                    if missing_count <= 5:
                        self.stdout.write(f'  MISSING: {img.slug} -> {img.image_url}')
        
        self.stdout.write(f'Files exist: {exists_count}/100')
        self.stdout.write(f'Files missing: {missing_count}/100')
        
        # 4. Check slug format consistency
        self.stdout.write('\nSlug-to-ImageID validation (first 10):')
        for img in Image.objects.all()[:10]:
            slug_base = img.slug.split('-')[0].upper()
            self.stdout.write(f'  {img.slug} -> ImageID: {slug_base} | Title: {img.title[:50]}')
        
        # 5. Check for duplicates
        from django.db.models import Count
        duplicates = Image.objects.values('slug').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        self.stdout.write(f'\nDuplicate slugs: {duplicates.count()}')
        
        # 6. URL pattern analysis
        json_prefix = Image.objects.filter(image_url__contains='json_').count()
        self.stdout.write(f'\nURL patterns:')
        self.stdout.write(f'  With json_ prefix: {json_prefix}')
        self.stdout.write(f'  Random names: {total - json_prefix}')
        
        self.stdout.write(self.style.SUCCESS('\n=== VALIDATION COMPLETE ==='))
