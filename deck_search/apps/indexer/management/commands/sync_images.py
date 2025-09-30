from django.core.management.base import BaseCommand
from apps.indexer.indexer import image_indexer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync images from image_service to deck_search Elasticsearch index'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync of all images (default: incremental sync)'
        )
        parser.add_argument(
            '--hours-back',
            type=int,
            default=24,
            help='For incremental sync: sync images updated in last N hours (default: 24)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for fetching images from image_service (default: 100)'
        )
        parser.add_argument(
            '--index-batch-size',
            type=int,
            default=50,
            help='Batch size for indexing into Elasticsearch (default: 50)'
        )

    def handle(self, *args, **options):
        full_sync = options['full']
        hours_back = options['hours_back']
        batch_size = options['batch_size']
        index_batch_size = options['index_batch_size']

        self.stdout.write(
            self.style.SUCCESS(f'Starting {"full" if full_sync else "incremental"} image sync...')
        )

        try:
            if full_sync:
                total_indexed = image_indexer.sync_all_images(batch_size=batch_size)
                self.stdout.write(
                    self.style.SUCCESS(f'Full sync completed: {total_indexed} images indexed')
                )
            else:
                total_indexed = image_indexer.sync_recent_images(
                    hours_back=hours_back,
                    batch_size=batch_size
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Incremental sync completed: {total_indexed} images indexed')
                )

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Sync failed: {e}')
            )
            logger.error(f'Sync command failed: {e}')
            return

        # Show stats
        try:
            stats = image_indexer.get_index_stats()
            self.stdout.write(self.style.SUCCESS('Index Statistics:'))
            self.stdout.write(f'  Total documents: {stats.get("total_documents", "N/A")}')
            self.stdout.write(f'  Image service healthy: {stats.get("image_service_health", "N/A")}')
            self.stdout.write(f'  Image service count: {stats.get("image_service_count", "N/A")}')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not retrieve stats: {e}')
            )
