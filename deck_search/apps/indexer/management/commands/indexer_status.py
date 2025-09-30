from django.core.management.base import BaseCommand
from apps.indexer.indexer import image_indexer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check the status and statistics of the image indexer'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Image Indexer Status'))
        self.stdout.write('=' * 50)

        try:
            stats = image_indexer.get_index_stats()

            self.stdout.write(f'Elasticsearch Index:')
            self.stdout.write(f'  Total documents: {stats.get("total_documents", "N/A")}')

            self.stdout.write(f'\nImage Service:')
            self.stdout.write(f'  Health: {"✓ Healthy" if stats.get("image_service_health") else "✗ Unhealthy"}')
            self.stdout.write(f'  Total images: {stats.get("image_service_count", "N/A")}')

            # Calculate sync status
            es_count = stats.get("total_documents", 0)
            service_count = stats.get("image_service_count", 0)

            if service_count > 0:
                sync_percentage = (es_count / service_count) * 100
                self.stdout.write(f'\nSync Status:')
                self.stdout.write(f'  Sync percentage: {sync_percentage:.1f}%')
                self.stdout.write(f'  Images to sync: {service_count - es_count}')

                if sync_percentage >= 95:
                    self.stdout.write(self.style.SUCCESS('  Status: ✓ Well synchronized'))
                elif sync_percentage >= 80:
                    self.stdout.write(self.style.WARNING('  Status: ⚠ Partially synchronized'))
                else:
                    self.stdout.write(self.style.ERROR('  Status: ✗ Needs synchronization'))
            else:
                self.stdout.write(self.style.ERROR('\nUnable to determine sync status - image service unavailable'))

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Failed to get indexer status: {e}')
            )
            logger.error(f'Status command failed: {e}')
