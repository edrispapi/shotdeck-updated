# ShotDeck Image Service - Complete Guidance

## 📋 System Overview

ShotDeck is a comprehensive image service that manages **28,189 images** linked to **5,375 movies** with advanced filtering and semantic relationships.

### 🎯 Key Features

- REST API with comprehensive filtering
- Django Admin panel for content management
- Automatic placeholder images for missing files
- Semantic movie-image relationships
- Real-time API responses

---

## 🗂️ Dataset Structure & Paths

### 📁 Dataset Location

```
/home/a/Desktop/shotdeck/dataset/
├── shot_images/          # Image files (170,885 files)
│   ├── 0000LRXW.jpg
│   ├── 0002VGOT.jpg
│   └── ...
└── shot_json_data/       # Metadata JSON files (28,189 files)
    ├── 0000LRXW.json
    ├── 0002VGOT.json
    └── ...
```

### 📄 JSON Metadata Structure

Each JSON file contains complete movie and image metadata:

```json
{
  "success": true,
  "data": {
    "imageid": "YI8XF7OD",
    "image_file": "YI8XF7OD.jpg",
    "details": {
      "title": {
        "values": [{ "display_value": "About Dry Grasses" }]
      },
      "full_title": "About Dry Grasses",
      "year": { "values": [{ "display_value": "2023" }] },
      "shot_info": {
        "description": "Shot info",
        "tags": { "values": [{ "display_value": "snow" }] },
        "color": { "values": [{ "display_value": "White" }] },
        "lighting": { "values": [{ "display_value": "Soft light" }] }
      },
      "title_info": {
        "director": { "values": [{ "display_value": "Nuri Bilge Ceylan" }] },
        "genre": { "values": [{ "display_value": "Drama" }] }
      }
    }
  }
}
```

---

## 🌐 API Usage Guide

### 📡 Base URL

```
http://localhost:51009/api/
```

### 🔍 List Images with Filtering

#### Basic Image List

```bash
curl -X GET "http://localhost:51009/api/images/?limit=5" \
  -H "accept: application/json"
```

#### Advanced Filtering

```bash
# Search by movie title
curl -X GET "http://localhost:51009/api/images/?q=Love%20%26%20Mercy&limit=10" \
  -H "accept: application/json"

# Filter by movie slug
curl -X GET "http://localhost:51009/api/images/?movie_slug=love-mercy" \
  -H "accept: application/json"

# Filter by color
curl -X GET "http://localhost:51009/api/images/?color=White&limit=20" \
  -H "accept: application/json"

# Filter by year range
curl -X GET "http://localhost:51009/api/images/?release_year__gte=2020&release_year__lte=2023" \
  -H "accept: application/json"
```

#### Python API Client Example

```python
import requests
import json

class ShotDeckClient:
    def __init__(self, base_url="http://localhost:51009"):
        self.base_url = base_url

    def get_images(self, **filters):
        """Get images with filters"""
        params = {k: v for k, v in filters.items() if v is not None}
        response = requests.get(f"{self.base_url}/api/images/", params=params)
        return response.json()

    def get_movies(self, **filters):
        """Get movies with filters"""
        params = {k: v for k, v in filters.items() if v is not None}
        response = requests.get(f"{self.base_url}/api/movies/", params=params)
        return response.json()

    def get_image_detail(self, slug):
        """Get specific image details"""
        response = requests.get(f"{self.base_url}/api/images/{slug}/")
        return response.json()

# Usage examples
client = ShotDeckClient()

# Get recent images
images = client.get_images(limit=10, ordering="-created_at")
print(f"Found {images['count']} images")

# Search for specific movie
love_mercy_images = client.get_images(q="Love & Mercy")
print(f"Love & Mercy has {love_mercy_images['count']} images")

# Get movies from specific year
movies_2023 = client.get_movies(year=2023, limit=5)
for movie in movies_2023['results']:
    print(f"{movie['title']} ({movie['year']}) - {movie['image_count']} images")
```

### 🎬 Movie API Examples

```bash
# List all movies
curl -X GET "http://localhost:51009/api/movies/?limit=10" \
  -H "accept: application/json"

# Search movies by title
curl -X GET "http://localhost:51009/api/movies/?title=Love" \
  -H "accept: application/json"

# Filter by director
curl -X GET "http://localhost:51009/api/movies/?director=Ceylan" \
  -H "accept: application/json"

# Get movies by year range
curl -X GET "http://localhost:51009/api/movies/?year__gte=2020&year__lte=2023" \
  -H "accept: application/json"
```

### 📋 Filter Options

#### Get Available Filters

```bash
curl -X GET "http://localhost:51009/api/images/filters/" \
  -H "accept: application/json"
```

#### Python Filter Discovery

```python
import requests

def get_available_filters():
    """Get all available filter options"""
    response = requests.get("http://localhost:51009/api/images/filters/")
    data = response.json()

    print("Available Filters:")
    for filter_name, options in data['data'].items():
        if options:  # Only show filters with values
            print(f"\n{filter_name.upper()}:")
            for option in options[:5]:  # Show first 5 options
                print(f"  - {option['value']}")

get_available_filters()
```

---

## 🔧 Django Admin Panel

### 📍 Access Admin Panel

```
URL: http://localhost:51009/admin/
Username: admin
Password: admin123
```

### 🎬 Movie Management

```python
# Django shell example for movie operations
from apps.images.models import Movie, Image

# Get movie with most images
top_movie = Movie.objects.annotate(
    image_count=models.Count('images')
).order_by('-image_count').first()

print(f"Top movie: {top_movie.title} ({top_movie.image_count} images)")

# Find movies without images
orphan_movies = Movie.objects.annotate(
    image_count=models.Count('images')
).filter(image_count=0)

print(f"Movies without images: {orphan_movies.count()}")
```

### 🖼️ Image Management

#### Bulk Update Image Tags

```python
from apps.images.models import Image, Tag

# Add "cinematic" tag to all images from 2023
cinematic_tag, created = Tag.objects.get_or_create(name="cinematic")

images_2023 = Image.objects.filter(release_year=2023)
for image in images_2023:
    image.tags.add(cinematic_tag)

print(f"Added cinematic tag to {images_2023.count()} images")
```

#### Find Images by Color Analysis

```python
# Find images with warm color temperature
warm_images = Image.objects.filter(color__value__icontains="warm")
print(f"Warm images: {warm_images.count()}")

# Find high contrast images
contrast_images = Image.objects.filter(
    color__value__icontains="high contrast"
)
print(f"High contrast images: {contrast_images.count()}")
```

---

## ⚙️ Management Commands

### 🔄 Database Operations

#### Quick Rebuild (Recommended)

```bash
cd /home/a/shotdeck-main/image_service
docker-compose exec image_service python manage.py quick_rebuild_from_json
```

#### Complete Rebuild (Advanced)

```bash
docker-compose exec image_service python manage.py complete_rebuild_from_json
```

#### Fix Image Relationships

```bash
# Update image counts for all movies
docker-compose exec image_service python manage.py shell -c "
from apps.images.models import Movie, Image
movies = Movie.objects.all()
for movie in movies:
    movie.image_count = Image.objects.filter(movie=movie).count()
    movie.save()
print('Updated image counts for all movies')
"
```

### 🧹 Data Cleanup

#### Remove Duplicates

```bash
# Remove duplicate movies
docker-compose exec image_service python manage.py deduplicate_movies

# Remove duplicate images
docker-compose exec image_service python manage.py deduplicate_images
```

#### Link Images to Movies

```bash
# Bulk link images to movies by title matching
docker-compose exec image_service python manage.py bulk_link_images_to_movies

# Link specific images
docker-compose exec image_service python manage.py link_images_to_movies
```

### 🔍 Data Analysis

#### Check Image Availability

```bash
docker-compose exec image_service python manage.py fix_image_availability
```

#### Analyze Dataset Matches

```bash
# Dry run to see potential matches
docker-compose exec image_service python manage.py match_image_files --dry-run

# Apply matches
docker-compose exec image_service python manage.py match_image_files
```

---

## 📊 Data Statistics

### Current Database Status

```python
from apps.images.models import Movie, Image, Tag

print("=== DATABASE STATISTICS ===")
print(f"Total Movies: {Movie.objects.count()}")
print(f"Total Images: {Image.objects.count()}")
print(f"Total Tags: {Tag.objects.count()}")

# Movies by year
from django.db.models import Count
movies_by_year = Movie.objects.values('year').annotate(count=Count('id')).order_by('-year')
print("\nMovies by Year:")
for item in movies_by_year[:10]:
    print(f"  {item['year'] or 'Unknown'}: {item['count']}")

# Image availability
available_images = Image.objects.filter(image_url__isnull=False)
print(f"\nImages with URLs: {available_images.count()}")

# Top genres
from apps.images.models import GenreOption
top_genres = GenreOption.objects.annotate(
    usage=Count('image')
).order_by('-usage')[:5]
print("\nTop Genres:")
for genre in top_genres:
    print(f"  {genre.value}: {genre.usage} images")
```

### Image File Analysis

```bash
# Check dataset file count
ls /home/a/Desktop/shotdeck/dataset/shot_images/*.jpg | wc -l

# Check JSON metadata count
ls /home/a/Desktop/shotdeck/dataset/shot_json_data/*.json | wc -l

# Find largest image files
find /home/a/Desktop/shotdeck/dataset/shot_images -name "*.jpg" -exec ls -lh {} \; | sort -k5 -hr | head -10
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. 404 on Image URLs

**Problem**: Getting 404 errors when accessing image URLs
**Solution**: The system now returns placeholder images instead of 404s

```bash
curl -I "http://localhost:51009/media/images/missing-image.jpg"
# Should return 200 OK with PNG content
```

#### 2. No Search Results

**Problem**: API returns empty results
**Check**:

```bash
# Verify data exists
curl "http://localhost:51009/api/movies/?limit=1"
curl "http://localhost:51009/api/images/?limit=1"

# Check filters
curl "http://localhost:51009/api/images/filters/"
```

#### 3. Admin Panel Slow

**Problem**: Admin interface loads slowly
**Solutions**:

- Use raw_id_fields for large datasets
- Add database indexes
- Use pagination (already implemented)

#### 4. Memory Issues During Import

**Problem**: Large imports consume too much memory
**Solution**: Use batch processing

```bash
# Use batch size parameter
docker-compose exec image_service python manage.py quick_rebuild_from_json --batch-size=500
```

### Performance Optimization

#### Database Indexes

```python
# Add this to models.py for better performance
class Meta:
    indexes = [
        models.Index(fields=['movie', 'created_at']),
        models.Index(fields=['color', 'release_year']),
        models.Index(fields=['media_type', 'time_period']),
    ]
```

#### API Caching

```python
# API responses are cached for 5 minutes
# Adjust in settings.py:
CACHE_MIDDLEWARE_SECONDS = 300  # 5 minutes
```

---

## 🚀 Best Practices

### API Usage

1. **Use pagination** for large result sets
2. **Combine filters** efficiently
3. **Cache results** when possible
4. **Use specific endpoints** over general searches

### Data Management

1. **Run deduplication** regularly
2. **Monitor image availability** stats
3. **Backup before major operations**
4. **Test imports** with `--dry-run` first

### Performance

1. **Use raw_id_fields** in admin for large FKs
2. **Implement caching** for expensive queries
3. **Use select_related/prefetch_related** in queries
4. **Monitor database query performance**

### File Organization

```
/home/a/Desktop/shotdeck/dataset/
├── shot_images/     # Source images (170K+ files)
├── shot_json_data/  # Metadata (28K+ files)
└── backups/         # Database backups
```

---

## 📞 Support & Monitoring

### Health Check

```bash
curl "http://localhost:51009/api/health/"
```

### Database Monitoring

```bash
# Check table sizes
docker-compose exec image_db_17 psql -U postgres -d image_db -c "
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;
"
```

### Log Monitoring

```bash
# View application logs
docker-compose logs -f image_service

# View database logs
docker-compose logs -f image_db_17
```

---

## 🎯 Quick Start Commands

```bash
# 1. Start the system
cd /home/a/shotdeck-main/image_service
docker-compose up -d

# 2. Check health
curl "http://localhost:51009/api/health/"

# 3. View admin panel
# Open: http://localhost:51009/admin/
# Login: admin / admin123

# 4. Test API
curl "http://localhost:51009/api/images/?limit=5"

# 5. Check dataset
ls /home/a/Desktop/shotdeck/dataset/shot_images/ | wc -l
ls /home/a/Desktop/shotdeck/dataset/shot_json_data/ | wc -l
```

This comprehensive guide covers all aspects of the ShotDeck Image Service. Use the coding samples and dataset paths provided to interact with the system effectively! 🎉
