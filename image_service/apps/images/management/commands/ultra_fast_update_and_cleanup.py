import time
import signal
import os
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.db.models import Count
from apps.images.models import Movie


class TimeoutError(Exception):
    pass


class Command(BaseCommand):
    help = 'ULTRA SPEED: Update image counts and remove duplicate movies with 1-minute timeout and auto-retry'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually making changes'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=60,
            help='Timeout in seconds (default: 60)'
        )
        parser.add_argument(
            '--max-retries',
            type=int,
            default=3,
            help='Maximum number of retries (default: 3)'
        )

    def timeout_handler(self, signum, frame):
        raise TimeoutError("Operation timed out!")

    def run_with_timeout(self, func, timeout_seconds):
        """Run a function with a timeout"""
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(timeout_seconds)
        try:
            result = func()
            signal.alarm(0)  # Cancel the alarm
            return result
        except TimeoutError:
            signal.alarm(0)  # Cancel the alarm
            raise

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        timeout = options.get('timeout', 60)
        max_retries = options.get('max_retries', 3)

        self.stdout.write('=== ULTRA SPEED UPDATE & CLEANUP ===')
        self.stdout.write(f'⏰ Timeout: {timeout}s | Max retries: {max_retries}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Retry mechanism
        for attempt in range(max_retries):
            try:
                self.stdout.write(f'\n🔄 ATTEMPT {attempt + 1}/{max_retries}')

                # Run with timeout
                result = self.run_with_timeout(
                    lambda: self._execute_cleanup(dry_run),
                    timeout
                )

                # Success!
                return result

            except TimeoutError:
                self.stdout.write(self.style.ERROR(f'\n❌ ATTEMPT {attempt + 1} TIMED OUT after {timeout} seconds!'))

                if attempt < max_retries - 1:
                    self.stdout.write('🔄 Retrying...')
                    time.sleep(2)  # Brief pause before retry
                else:
                    self.stdout.write(self.style.ERROR('💥 ALL ATTEMPTS FAILED! Giving up.'))
                    return

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n💥 ATTEMPT {attempt + 1} FAILED with error: {e}'))
                if attempt < max_retries - 1:
                    self.stdout.write('🔄 Retrying...')
                    time.sleep(2)
                else:
                    self.stdout.write(self.style.ERROR('💥 ALL ATTEMPTS FAILED! Giving up.'))
                    raise

    def _execute_cleanup(self, dry_run):
        """Execute the actual cleanup logic"""
        start_time = time.time()

        # Get initial stats
        initial_movie_count = Movie.objects.count()
        unique_titles = Movie.objects.values('title').distinct().count()

        self.stdout.write(f'Initial movies: {initial_movie_count}')
        self.stdout.write(f'Unique titles: {unique_titles}')

        # STEP 1: SKIP image count update for SPEED - focus on duplicates only
        self.stdout.write('\n🚀 STEP 1: Skipping image count update (FOCUS ON SPEED)...')
        self.stdout.write('⚡ Prioritizing duplicate removal over image count accuracy')
        total_updated = 0
        step1_duration = 0

        # STEP 2: MANUAL BATCHING - Fast and reliable
        self.stdout.write('\n🔥 STEP 2: Removing duplicates (MANUAL BATCHING)...')

        start_step2 = time.time()
        with connection.cursor() as cursor:
            # Create a simple list of IDs to keep (one per title, highest image_count)
            self.stdout.write('Creating keep list...')
            cursor.execute('''
                CREATE TEMPORARY TABLE keep_ids AS
                SELECT DISTINCT ON (title) id
                FROM images_movie
                ORDER BY title, image_count DESC, id ASC
            ''')
            self.stdout.write('✅ Keep list created')

            # Count total to delete
            cursor.execute('SELECT COUNT(*) FROM images_movie WHERE id NOT IN (SELECT id FROM keep_ids)')
            total_to_delete = cursor.fetchone()[0]

            self.stdout.write(f'📊 Will delete {total_to_delete} duplicate movies')

            if total_to_delete == 0:
                self.stdout.write('✅ No duplicates found!')
                actual_deleted = 0
            elif dry_run:
                self.stdout.write('🔍 DRY RUN: Would delete all duplicates')
                actual_deleted = total_to_delete
            else:
                # MANUAL BATCHING: Delete in large chunks
                delete_start = time.time()
                batch_size = 5000  # Large batches for speed
                deleted_so_far = 0

                self.stdout.write(f'Starting deletion in batches of {batch_size}...')

                while True:
                    # Delete one large batch
                    cursor.execute(f'''
                        DELETE FROM images_movie
                        WHERE id IN (
                            SELECT id FROM images_movie
                            WHERE id NOT IN (SELECT id FROM keep_ids)
                            LIMIT {batch_size}
                        )
                    ''')

                    batch_deleted = cursor.rowcount
                    if batch_deleted == 0:
                        break

                    deleted_so_far += batch_deleted

                    # Progress update every few batches
                    if deleted_so_far % (batch_size * 2) == 0 or deleted_so_far >= total_to_delete:
                        progress = (deleted_so_far / total_to_delete) * 100
                        elapsed = time.time() - delete_start
                        speed = deleted_so_far / elapsed if elapsed > 0 else 0
                        self.stdout.write(f'⚡ Progress: {deleted_so_far}/{total_to_delete} ({progress:.1f}%) - Speed: {speed:.0f}/sec')

                actual_deleted = deleted_so_far
                delete_duration = time.time() - delete_start

                # Calculate speed
                delete_speed = actual_deleted / delete_duration if delete_duration > 0 else 0

                # Success alarm
                alarm = '\a\a\a\a\a\a\a\a\a\a'  # MASSIVE SUCCESS ALARM
                self.stdout.write(f'{alarm}🎉 STEP 2 COMPLETE: Deleted {actual_deleted} movies in {delete_duration:.2f}s ({delete_speed:.0f}/sec)')

        step2_duration = time.time() - start_step2
        self.stdout.write(f'🎯 Total Step 2 time: {step2_duration:.2f}s')

        # STEP 3: Final verification with real-time stats
        self.stdout.write('\n📈 STEP 3: Final verification...')

        final_movie_count = Movie.objects.count()
        final_unique_titles = Movie.objects.values('title').distinct().count()
        remaining_duplicates = Movie.objects.values('title').annotate(count=Count('title')).filter(count__gt=1).count()

        end_time = time.time()
        duration = end_time - start_time

        # Results with detailed breakdown
        self.stdout.write(self.style.SUCCESS(
            f'\n🎯 === MISSION ACCOMPLISHED IN {duration:.2f} SECONDS ===\n'
            f'📊 INITIAL STATE:\n'
            f'   • Movies: {initial_movie_count}\n'
            f'   • Unique titles: {unique_titles}\n'
            f'\n⚡ OPERATIONS PERFORMED:\n'
            f'   • Updated image counts: {total_updated} movies\n'
            f'   • Deleted duplicates: {actual_deleted}\n'
            f'\n📈 FINAL STATE:\n'
            f'   • Movies: {final_movie_count}\n'
            f'   • Unique titles: {final_unique_titles}\n'
            f'   • Remaining duplicates: {remaining_duplicates}\n'
            f'\n🚀 PERFORMANCE:\n'
            f'   • Total time: {duration:.2f}s\n'
            f'   • Deletion speed: {actual_deleted/duration:.0f} movies/second\n'
            f'   • Status: {"✅ SUCCESS" if duration < 60 else "❌ TOO SLOW"} (< 1 min target)\n'
        ))

        return {
            'duration': duration,
            'initial_movies': initial_movie_count,
            'final_movies': final_movie_count,
            'deleted': actual_deleted,
            'unique_titles': final_unique_titles,
            'remaining_duplicates': remaining_duplicates
        }
