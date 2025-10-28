from django.core.management.base import BaseCommand
from django.db import connection, transaction
from apps.images.models import Image, Movie, Tag
import time

class Command(BaseCommand):
    help = 'Clean up empty data from database with real-time logging'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to delete per batch (default: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS('=== DATABASE CLEANUP STARTED ===')
        )
        
        # Get initial counts
        total_images = Image.objects.count()
        total_movies = Movie.objects.count()
        total_tags = Tag.objects.count()
        
        self.stdout.write(f'Initial state:')
        self.stdout.write(f'  Images: {total_images:,}')
        self.stdout.write(f'  Movies: {total_movies:,}')
        self.stdout.write(f'  Tags: {total_tags:,}')
        
        # Count empty images
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT COUNT(*) FROM images_image 
                WHERE title IS NULL OR title = '' 
                OR description IS NULL OR description = ''
                OR movie_id IS NULL
            ''')
            empty_count = cursor.fetchone()[0]
        
        self.stdout.write(f'\nEmpty images to delete: {empty_count:,}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No data will be deleted'))
            return
        
        if empty_count == 0:
            self.stdout.write(self.style.SUCCESS('No empty data found!'))
            return
        
        # Start deletion with real-time progress
        start_time = time.time()
        total_deleted = 0
        
        self.stdout.write(f'\nStarting deletion in batches of {batch_size:,}...')
        
        while True:
            batch_start = time.time()
            
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Delete a batch using raw SQL for speed
                    cursor.execute('''
                        DELETE FROM images_image 
                        WHERE id IN (
                            SELECT id FROM images_image 
                            WHERE (title IS NULL OR title = '' 
                            OR description IS NULL OR description = ''
                            OR movie_id IS NULL)
                            LIMIT %s
                        )
                    ''', [batch_size])
                    
                    batch_deleted = cursor.rowcount
                    
            if batch_deleted == 0:
                break
                
            total_deleted += batch_deleted
            batch_time = time.time() - batch_start
            elapsed_time = time.time() - start_time
            
            # Calculate progress and speed
            progress = (total_deleted / empty_count) * 100
            speed = total_deleted / elapsed_time if elapsed_time > 0 else 0
            eta = (empty_count - total_deleted) / speed if speed > 0 else 0
            
            self.stdout.write(
                f'✓ Deleted {batch_deleted:,} images | '
                f'Total: {total_deleted:,}/{empty_count:,} ({progress:.1f}%) | '
                f'Speed: {speed:.0f} records/sec | '
                f'ETA: {eta/60:.1f} min | '
                f'Batch time: {batch_time:.2f}s'
            )
            
            # Small delay to prevent overwhelming the database
            time.sleep(0.1)
        
        # Final cleanup - remove orphaned movies and tags
        self.stdout.write('\n=== CLEANING ORPHANED DATA ===')
        
        # Remove movies with no images
        with connection.cursor() as cursor:
            cursor.execute('''
                DELETE FROM images_movie 
                WHERE id NOT IN (SELECT DISTINCT movie_id FROM images_image WHERE movie_id IS NOT NULL)
            ''')
            orphaned_movies = cursor.rowcount
            self.stdout.write(f'Deleted {orphaned_movies:,} orphaned movies')
        
        # Remove tags with no images
        with connection.cursor() as cursor:
            cursor.execute('''
                DELETE FROM images_tag 
                WHERE id NOT IN (
                    SELECT DISTINCT tag_id FROM images_image_tags 
                    WHERE tag_id IS NOT NULL
                )
            ''')
            orphaned_tags = cursor.rowcount
            self.stdout.write(f'Deleted {orphaned_tags:,} orphaned tags')
        
        # Final counts
        final_images = Image.objects.count()
        final_movies = Movie.objects.count()
        final_tags = Tag.objects.count()
        
        total_time = time.time() - start_time
        
        self.stdout.write(f'\n=== CLEANUP COMPLETE ===')
        self.stdout.write(f'Deleted {total_deleted:,} empty images')
        self.stdout.write(f'Deleted {orphaned_movies:,} orphaned movies')
        self.stdout.write(f'Deleted {orphaned_tags:,} orphaned tags')
        self.stdout.write(f'Total time: {total_time/60:.1f} minutes')
        self.stdout.write(f'Average speed: {total_deleted/total_time:.0f} records/sec')
        
        self.stdout.write(f'\nFinal state:')
        self.stdout.write(f'  Images: {final_images:,} (was {total_images:,})')
        self.stdout.write(f'  Movies: {final_movies:,} (was {total_movies:,})')
        self.stdout.write(f'  Tags: {final_tags:,} (was {total_tags:,})')
        
        self.stdout.write(
            self.style.SUCCESS('✅ Database cleanup completed successfully!')
        )
