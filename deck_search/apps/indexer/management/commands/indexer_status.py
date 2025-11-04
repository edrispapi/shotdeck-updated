from django.core.management.base import BaseCommand
from apps.indexer.indexer import get_image_indexer


class Command(BaseCommand):
    help = 'Show indexer status'

    def handle(self, *args, **options):
        self.stdout.write('Indexer Status')
        self.stdout.write('=' * 50)

        try:
            indexer = get_image_indexer()
            stats = indexer.get_index_stats()
            
            self.stdout.write(f"\nElasticsearch:")
            self.stdout.write(f"  Documents: {stats.get('total_documents', 0)}")
            
            self.stdout.write(f"\nImage Service:")
            self.stdout.write(f"  Health: {stats.get('image_service_health', False)}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
