# مسیر: /home/mdk/Documents/shotdeck-main/search_service/apps/search/management/commands/run_kafka_consumer.py
from django.core.management.base import BaseCommand
from messaging.consumers import run_kafka_consumer
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the Kafka consumer for the search service as a persistent background process.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Kafka consumer...'))
        try:
            run_kafka_consumer()
        except KeyboardInterrupt:
            # این بخش زمانی اجرا می‌شود که شما با Ctrl+C فرآیند را متوقف کنید.
            self.stdout.write(self.style.WARNING('Kafka consumer stopped by user.'))
        except Exception as e:
            logger.error(f"Kafka consumer faced an unexpected error: {e}")
            self.stderr.write(self.style.ERROR('Kafka consumer stopped due to a critical error.'))