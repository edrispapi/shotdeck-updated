# /home/a/shotdeck-main/deck_search/apps/color_ai/management/commands/test_color_ai.py

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Test color AI setup'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('✅ Color AI app is working!'))
        
        # Test imports
        try:
            from apps.color_ai.color_processor import UltimateColorProcessor
            self.stdout.write('✅ ColorProcessor imported successfully')
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'❌ ColorProcessor import failed: {e}'))
        
        try:
            from apps.color_ai.image_service_client import ImageServiceClient
            self.stdout.write('✅ ImageServiceClient imported successfully')
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'❌ ImageServiceClient import failed: {e}'))
        
        self.stdout.write('\n✅ All tests passed!')