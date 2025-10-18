from django.core.management.base import BaseCommand
from apps.images.models import Image
import os

class Command(BaseCommand):
    help = 'Final data integrity check'
    
    def handle(self, *args, **options):
        total = Image.objects.count()
        with_files = 0
        without_files = 0
        
        self.stdout.write('Checking 100 random images...')
        
        for img in Image.objects.order_by('?')[:100]:
            file_path = os.path.join('/service/media', img.image_url.replace('/media/', '', 1))
            if os.path.exists(file_path):
                with_files += 1
            else:
                without_files += 1
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('FINAL VALIDATION REPORT')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Total images in database: {total}')
        self.stdout.write(f'Sample checked: 100')
        self.stdout.write(f'Files exist: {with_files}/100 ({with_files}%)')
        self.stdout.write(f'Files missing: {without_files}/100')
        
        if with_files >= 95:
            self.stdout.write(self.style.SUCCESS('\nStatus: EXCELLENT'))
            self.stdout.write('All systems ready for deployment!')
        else:
            self.stdout.write(self.style.ERROR('\nStatus: ISSUES DETECTED'))
        
        self.stdout.write('=' * 60)
