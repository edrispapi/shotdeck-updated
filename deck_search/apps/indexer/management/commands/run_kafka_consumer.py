from django.core.management.base import BaseCommand
from apps.indexer.kafka_consumer import run_kafka_consumer

class Command(BaseCommand):
    help = 'Run Kafka consumer to sync image events from image_service to Elasticsearch.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Kafka consumer for deck_search...'))
        run_kafka_consumer()
