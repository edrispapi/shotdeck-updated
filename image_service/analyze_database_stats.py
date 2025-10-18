#!/usr/bin/env python3
"""
Comprehensive database analysis script
Analyzes Images and Movies tables for statistics, null values, and duplicates
"""

import os
import django
from django.db import models
from django.conf import settings
from collections import defaultdict, Counter

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.images.models import Image, Movie, Tag

def get_model_fields(model_class):
    """Get all field names for a Django model"""
    return [field.name for field in model_class._meta.get_fields()]

def analyze_null_values(model_class, model_name):
    """Analyze null/empty values for each field in a model"""
    fields = get_model_fields(model_class)
    total_count = model_class.objects.count()

    analysis = {
        'model': model_name,
        'total_rows': total_count,
        'fields': {},
        'columns': len(fields)
    }

    for field_name in fields:
        # Skip reverse relations and many-to-many fields
        field = model_class._meta.get_field(field_name)
        if field.many_to_one or field.many_to_many or field.one_to_many:
            continue

        # Count null/empty values
        if hasattr(field, 'null') and field.null:
            null_count = model_class.objects.filter(**{f'{field_name}__isnull': True}).count()
        else:
            null_count = 0

        # Count empty strings for CharField/TextField
        if isinstance(field, (models.CharField, models.TextField)):
            empty_count = model_class.objects.filter(**{field_name: ''}).count()
        else:
            empty_count = 0

        total_empty = null_count + empty_count
        fill_rate = ((total_count - total_empty) / total_count * 100) if total_count > 0 else 0

        analysis['fields'][field_name] = {
            'null_count': null_count,
            'empty_count': empty_count,
            'total_empty': total_empty,
            'fill_rate': round(fill_rate, 2),
            'field_type': field.__class__.__name__
        }

    return analysis

def analyze_duplicates(model_class, model_name):
    """Analyze duplicate records"""
    duplicates = {
        'model': model_name,
        'duplicate_groups': 0,
        'total_duplicates': 0
    }

    if model_name == 'Image':
        # Check for duplicate slugs
        slug_duplicates = (Image.objects.values('slug')
                          .annotate(count=models.Count('id'))
                          .filter(count__gt=1))
        duplicates['slug_duplicates'] = list(slug_duplicates)

        # Check for duplicate image_urls
        url_duplicates = (Image.objects.exclude(image_url__isnull=True)
                         .exclude(image_url='')
                         .values('image_url')
                         .annotate(count=models.Count('id'))
                         .filter(count__gt=1))
        duplicates['url_duplicates'] = list(url_duplicates)
        duplicates['duplicate_groups'] = len(url_duplicates)
        duplicates['total_duplicates'] = sum(dup['count'] - 1 for dup in url_duplicates)

    elif model_name == 'Movie':
        # Check for duplicate titles
        title_duplicates = (Movie.objects.values('title')
                           .annotate(count=models.Count('id'))
                           .filter(count__gt=1))
        duplicates['title_duplicates'] = list(title_duplicates)
        duplicates['duplicate_groups'] = len(title_duplicates)
        duplicates['total_duplicates'] = sum(dup['count'] - 1 for dup in title_duplicates)

    return duplicates

def analyze_image_urls():
    """Analyze image URL patterns and references"""
    analysis = {
        'total_images': Image.objects.count(),
        'with_urls': Image.objects.exclude(image_url__isnull=True).exclude(image_url='').count(),
        'without_urls': Image.objects.filter(models.Q(image_url__isnull=True) | models.Q(image_url='')).count(),
        'url_patterns': Counter(),
        'malformed_urls': [],
        'correctly_formatted': 0
    }

    # Analyze URL patterns
    for img in Image.objects.exclude(image_url__isnull=True).exclude(image_url='')[:1000]:  # Sample
        url = img.image_url
        if '/media/images/' in url:
            filename = url.split('/media/images/')[-1]
            expected_filename = f"{img.slug}.jpg"
            if filename == expected_filename:
                analysis['correctly_formatted'] += 1
            else:
                analysis['malformed_urls'].append({
                    'id': img.id,
                    'slug': img.slug,
                    'url': url,
                    'expected': expected_filename,
                    'actual': filename
                })

    analysis['correctly_formatted_rate'] = (analysis['correctly_formatted'] / min(1000, analysis['with_urls']) * 100) if analysis['with_urls'] > 0 else 0

    return analysis

def generate_report():
    """Generate comprehensive database analysis report"""
    print("🔍 DATABASE ANALYSIS REPORT")
    print("=" * 80)

    # Analyze Images
    print("\n📸 IMAGES TABLE ANALYSIS")
    print("-" * 40)
    image_analysis = analyze_null_values(Image, 'Image')
    image_duplicates = analyze_duplicates(Image, 'Image')

    print(f"Total Rows: {image_analysis['total_rows']:,}")
    print(f"Columns: {image_analysis['columns']}")
    print(f"Duplicate Groups: {image_duplicates['duplicate_groups']:,}")
    print(f"Duplicate Images: {image_duplicates['total_duplicates']:,}")
    print(f"Unique Images: {image_analysis['total_rows'] - image_duplicates['total_duplicates']:,}")

    print("\n📊 FIELD ANALYSIS (Images):")
    print("Field".ljust(20) + "Type".ljust(15) + "Null".ljust(8) + "Empty".ljust(8) + "Fill Rate")
    print("-" * 70)
    for field_name, stats in sorted(image_analysis['fields'].items()):
        print(f"{field_name:<20} {stats['field_type']:<15} {stats['null_count']:<8} {stats['empty_count']:<8} {stats['fill_rate']:.1f}%")

    # Analyze Movies
    print("\n🎬 MOVIES TABLE ANALYSIS")
    print("-" * 40)
    movie_analysis = analyze_null_values(Movie, 'Movie')
    movie_duplicates = analyze_duplicates(Movie, 'Movie')

    print(f"Total Rows: {movie_analysis['total_rows']:,}")
    print(f"Columns: {movie_analysis['columns']}")
    print(f"Duplicate Groups: {movie_duplicates['duplicate_groups']:,}")
    print(f"Duplicate Movies: {movie_duplicates['total_duplicates']:,}")
    print(f"Unique Movies: {movie_analysis['total_rows'] - movie_duplicates['total_duplicates']:,}")

    print("\n📊 FIELD ANALYSIS (Movies):")
    print("Field".ljust(20) + "Type".ljust(15) + "Null".ljust(8) + "Empty".ljust(8) + "Fill Rate")
    print("-" * 70)
    for field_name, stats in sorted(movie_analysis['fields'].items()):
        print(f"{field_name:<20} {stats['field_type']:<15} {stats['null_count']:<8} {stats['empty_count']:<8} {stats['fill_rate']:.1f}%")

    # Analyze Image URLs
    print("\n🔗 IMAGE URL ANALYSIS")
    print("-" * 40)
    url_analysis = analyze_image_urls()

    print(f"Images with URLs: {url_analysis['with_urls']:,} ({url_analysis['with_urls']/url_analysis['total_images']*100:.1f}%)")
    print(f"Images without URLs: {url_analysis['without_urls']:,} ({url_analysis['without_urls']/url_analysis['total_images']*100:.1f}%)")
    print(f"Correctly formatted URLs: {url_analysis['correctly_formatted']:,} ({url_analysis['correctly_formatted_rate']:.1f}%)")
    print(f"Malformed URLs: {len(url_analysis['malformed_urls'])}")

    if url_analysis['malformed_urls']:
        print("\n⚠️  MALFORMED URL SAMPLES:")
        for malformed in url_analysis['malformed_urls'][:5]:
            print(f"  ID {malformed['id']}: Expected '{malformed['expected']}', got '{malformed['actual']}'")

    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)

    total_fill_rate_images = sum(stats['fill_rate'] for stats in image_analysis['fields'].values()) / len(image_analysis['fields'])
    total_fill_rate_movies = sum(stats['fill_rate'] for stats in movie_analysis['fields'].values()) / len(movie_analysis['fields'])

    print(f"🖼️  Images: {image_analysis['total_rows'] - image_duplicates['total_duplicates']:,} unique records")
    print(f"🎬 Movies: {movie_analysis['total_rows'] - movie_duplicates['total_duplicates']:,} unique records")
    print(f"📊 Average field fill rate (Images): {total_fill_rate_images:.1f}%")
    print(f"📊 Average field fill rate (Movies): {total_fill_rate_movies:.1f}%")
    print(f"🗑️  Total duplicates removed: {image_duplicates['total_duplicates'] + movie_duplicates['total_duplicates']:,}")
    print(f"🔗 Image URLs available: {url_analysis['with_urls']:,} ({url_analysis['with_urls']/url_analysis['total_images']*100:.1f}%)")

    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    generate_report()
