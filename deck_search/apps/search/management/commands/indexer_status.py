from django.core.management.base import BaseCommand
from apps.indexer.indexer import get_image_indexer  # ← تغییر import


class Command(BaseCommand):
    help = 'Show indexer status and statistics'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Image Indexer Status'))
        self.stdout.write('=' * 50)

        try:
            # Get indexer instance
            indexer = get_image_indexer()
            
            # Get stats
            stats = indexer.get_index_stats()
            
            self.stdout.write('\nElasticsearch Index:')
            self.stdout.write(f"  Total documents: {stats.get('total_documents', 'N/A')}")
            
            self.stdout.write('\nImage Service:')
            self.stdout.write(f"  Health: {'✓ Healthy' if stats.get('image_service_health') else '✗ Unhealthy'}")
            self.stdout.write(f"  Total images: {stats.get('image_service_count', 'N/A')}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))