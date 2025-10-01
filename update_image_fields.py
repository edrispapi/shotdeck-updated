#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.images.models import Image, GenreOption, CameraTypeOption, Movie

def update_image_genres_optimized():
    """Optimized version: Update existing images with genre data using bulk operations"""
    print("🚀 OPTIMIZED: Updating image genres from movie data...")

    # First, create all needed GenreOption objects in bulk
    from django.db.models import Count

    # Get all unique genre strings from movies that have genres
    movies_with_genres = Movie.objects.filter(genre__isnull=False).exclude(genre='').values_list('genre', flat=True).distinct()

    # Create a set of all genre names we need
    all_genre_names = set()
    for movie_genres in movies_with_genres:
        genre_names = [g.strip() for g in movie_genres.split(',') if g.strip()]
        all_genre_names.update(genre_names)

    print(f"📝 Found {len(all_genre_names)} unique genre types to create")

    # Bulk create genre options
    existing_genres = set(GenreOption.objects.values_list('value', flat=True))
    genres_to_create = []
    for genre_name in all_genre_names:
        if genre_name not in existing_genres:
            genres_to_create.append(GenreOption(value=genre_name, display_order=0))

    if genres_to_create:
        GenreOption.objects.bulk_create(genres_to_create)
        print(f"✨ Created {len(genres_to_create)} new genre options")

    # Create mapping of genre names to objects
    genre_map = {g.value: g for g in GenreOption.objects.all()}

    # Now process images in batches
    batch_size = 1000
    offset = 0
    total_updated = 0

    while True:
        # Get batch of images without genres
        images_batch = list(Image.objects.filter(genre__isnull=True)
                           .exclude(movie__isnull=True)
                           .select_related('movie')[offset:offset+batch_size])

        if not images_batch:
            break

        print(f"📦 Processing batch {offset//batch_size + 1}: {len(images_batch)} images")

        # Prepare bulk operations
        image_genre_mappings = []

        for image in images_batch:
            movie = image.movie
            if movie and movie.genre:
                genre_names = [g.strip() for g in movie.genre.split(',') if g.strip()]
                if genre_names:
                    genre_objects = [genre_map[name] for name in genre_names if name in genre_map]
                    if genre_objects:
                        image_genre_mappings.append((image, genre_objects))

        # Bulk set many-to-many relationships
        for image, genre_objects in image_genre_mappings:
            image.genre.set(genre_objects)

        total_updated += len(image_genre_mappings)
        offset += batch_size

        if offset % 10000 == 0:
            print(f"📊 Progress: {offset} images processed, {total_updated} updated")

    print(f"✅ OPTIMIZED: Genre update complete! Updated {total_updated} images with genre data from movies.")

def update_image_genres_ultra_fast():
    """Ultra-fast version using raw SQL for maximum speed"""
    from django.db import connection

    print("⚡ ULTRA-FAST: Updating image genres using raw SQL...")

    # First ensure all genre options exist
    with connection.cursor() as cursor:
        # Get all unique genres from movies
        cursor.execute("""
            SELECT DISTINCT TRIM(UNNEST(STRING_TO_ARRAY(genre, ','))) as genre_name
            FROM images_movie
            WHERE genre IS NOT NULL AND genre != ''
        """)

        genre_names = [row[0] for row in cursor.fetchall() if row[0]]

        # Insert missing genre options
        if genre_names:
            from django.utils import timezone
            now = timezone.now()
            values_list = [(name, 0, now, now) for name in genre_names]
            cursor.executemany("""
                INSERT INTO genre_options (value, display_order, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (value) DO NOTHING
            """, values_list)
            print(f"✨ Ensured {len(genre_names)} genre options exist")

        # Create temporary table for bulk genre assignments
        cursor.execute("""
            CREATE TEMP TABLE temp_image_genres AS
            SELECT
                i.id as image_id,
                g.id as genre_id
            FROM images_image i
            JOIN images_movie m ON i.movie_id = m.id
            JOIN genre_options g ON g.value = ANY(
                SELECT TRIM(UNNEST(STRING_TO_ARRAY(m.genre, ',')))
            )
            WHERE i.id NOT IN (
                SELECT image_id FROM images_image_genre
            )
            AND m.genre IS NOT NULL AND m.genre != ''
        """)

        # Bulk insert into many-to-many table
        cursor.execute("""
            INSERT INTO images_image_genre (image_id, genreoption_id)
            SELECT image_id, genre_id FROM temp_image_genres
        """)

        updated_count = cursor.rowcount
        print(f"🚀 Bulk inserted {updated_count} genre relationships")

        # Clean up
        cursor.execute("DROP TABLE temp_image_genres")

    print(f"✅ ULTRA-FAST: Genre update complete! Updated {updated_count} image-genre relationships.")

def update_image_camera_types():
    """Placeholder for camera_type updates - would need JSON data lookup"""
    print("⚠️ Camera type update not implemented - would require JSON file scanning")
    print("   Camera types should be populated during import from image metadata")

if __name__ == '__main__':
    # Use the optimized version for reliability
    update_image_genres_optimized()
    update_image_camera_types()
