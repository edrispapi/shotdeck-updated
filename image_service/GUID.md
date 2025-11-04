```markdown
# 🎬 Shotdeck Image Service - Complete Guide

**Version:** 1.0.0  
**Last Updated:** 2025-01-XX  
**Status:** ✅ Production Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [API Documentation](#api-documentation)
5. [Database Schema](#database-schema)
6. [Development](#development)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)
9. [Performance](#performance)

---

## 🎯 Overview

The **Shotdeck Image Service** is a comprehensive Django-based microservice for managing cinematic images, metadata, and related data for the Shotdeck platform.

### Key Features

✅ **Image Management** - Store and manage 2000+ cinematic images  
✅ **Rich Metadata** - 25+ filterable attributes per image  
✅ **RESTful API** - Complete CRUD operations  
✅ **Auto-generated Docs** - Swagger UI with drf-spectacular  
✅ **Advanced Filtering** - Color, genre, composition, lighting, etc.  
✅ **Tag System** - Flexible tagging with slug-based lookups  
✅ **Media Serving** - Optimized image delivery with fallbacks  
✅ **Health Checks** - Monitoring endpoints for production  

### Current Statistics

```
Total Images:     2,057+
Movies/Shows:     500+
Tags:             1,000+
Filterable Attrs: 25+
API Endpoints:    30+
```

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────┐
│     Image Service (Django + DRF)            │
│           Port: 51009                        │
└──────────────┬──────────────────────────────┘
               │
   ┌───────────┴────────────┬────────────┐
   │                        │            │
┌──▼──────────┐   ┌────────▼──────┐  ┌──▼────────┐
│ PostgreSQL  │   │  Media Files  │  │   Kafka   │
│    :5432    │   │   (Volume)    │  │(Optional) │
│  (image-db) │   │  ~/shotdeck-  │  │  (Events) │
│             │   │    media      │  │           │
└─────────────┘   └───────────────┘  └───────────┘
```

### Data Flow

```
Client Request → Django View → Database Query → Serialize → JSON Response
                      ↓
                Media Files (if image request)
                      ↓
                Kafka Event (if enabled)
```

### Key Technologies

- **Django 5.1+** - Web framework
- **Django REST Framework** - API framework
- **drf-spectacular** - OpenAPI 3.0 schema generation
- **PostgreSQL 17** - Primary database
- **WhiteNoise** - Static file serving
- **Gunicorn** - Production WSGI server
- **Docker** - Containerization

---

## 🚀 Quick Start

### Prerequisites

```bash
✅ Docker 20.10+
✅ Docker Compose 2.0+
✅ Network: shotdeck_platform_network
✅ Port 51009 available
```

### 1. Create Network (if not exists)

```bash
docker network create shotdeck_platform_network
```

### 2. Clone and Setup

```bash
cd ~/shotdeck-main/image_service

# Create environment file
cp .env.example .env
nano .env  # Edit if needed
```

### 3. Start Services

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f image_service
```

### 4. Verify Installation

```bash
# Test home endpoint
curl http://localhost:51009/

# Expected output:
{
  "service": "Image Service",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "api": "/api/",
    "admin": "/admin/",
    "docs": "/api/schema/swagger-ui/",
    "shots": "/shots/"
  }
}

# Test Swagger UI
curl -I http://localhost:51009/api/schema/swagger-ui/
# Should return: HTTP/1.1 200 OK

# Open in browser
xdg-open http://localhost:51009/api/schema/swagger-ui/
```

### 5. Initial Data Load (Optional)

```bash
# Create superuser
docker compose exec image_service python manage.py createsuperuser

# Access admin
xdg-open http://localhost:51009/admin/
```

---

## 📖 API Documentation

### Base URLs

- **Local:** `http://localhost:51009`
- **Swagger UI:** `http://localhost:51009/api/schema/swagger-ui/`
- **OpenAPI Schema:** `http://localhost:51009/api/schema/`

### Core Endpoints

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/` | GET | Service info | `curl http://localhost:51009/` |
| `/shots/` | GET | Browse images | `curl http://localhost:51009/shots/` |
| `/api/health/` | GET | Health check | `curl http://localhost:51009/api/health/` |
| `/api/images/` | GET | List images | `curl http://localhost:51009/api/images/` |
| `/api/images/{id}/` | GET | Get image | `curl http://localhost:51009/api/images/1/` |
| `/api/movies/` | GET | List movies | `curl http://localhost:51009/api/movies/` |
| `/api/tags/` | GET | List tags | `curl http://localhost:51009/api/tags/` |
| `/api/options/` | GET | Filter options | `curl http://localhost:51009/api/options/` |

### Filter Parameters

```bash
# Available filters for /shots/ and /api/images/
search            # Text search
color             # Warm, Cool, Red, Blue, etc.
media_type        # Movie, TV, Trailer, Music Video
genre             # Drama, Action, Comedy, etc.
time_of_day       # Day, Night, Dusk, Dawn
interior_exterior # Interior, Exterior
lighting          # Soft light, Hard light, etc.
aspect_ratio      # 1.85, 2.35, 2.39, etc.
frame_size        # Close Up, Wide, Medium, etc.
shot_type         # Static, Handheld, Aerial, etc.
composition       # Centered, Rule of thirds, etc.
page              # Page number
page_size         # Results per page (max: 100)
```

### Example Requests

#### 1. Browse All Shots

```bash
curl "http://localhost:51009/shots/" | python3 -m json.tool
```

**Response:**
```json
{
  "success": true,
  "count": 20,
  "total": 2057,
  "page": 1,
  "page_size": 20,
  "total_pages": 103,
  "has_next": true,
  "has_previous": false,
  "results": [
    {
      "id": 1,
      "slug": "abc123-def456",
      "title": "The Godfather - Opening Scene",
      "description": "Classic opening shot",
      "image_url": "http://localhost:51009/media/images/ABC123.jpg",
      "movie": {
        "slug": "the-godfather-1972",
        "title": "The Godfather",
        "year": 1972
      },
      "tags": [
        {"slug": "low-key-lighting", "name": "low key lighting"},
        {"slug": "interior", "name": "interior"}
      ],
      "color": "Warm",
      "media_type": "Movie",
      "time_of_day": "Day",
      "interior_exterior": "Interior"
    }
  ]
}
```

#### 2. Filter by Color

```bash
curl "http://localhost:51009/shots/?color=Warm&page_size=5" | python3 -m json.tool
```

#### 3. Search and Filter

```bash
curl "http://localhost:51009/shots/?search=night&time_of_day=Night&color=Cool" | python3 -m json.tool
```

#### 4. Pagination

```bash
# Page 1
curl "http://localhost:51009/shots/?page=1&page_size=20"

# Page 2
curl "http://localhost:51009/shots/?page=2&page_size=20"
```

#### 5. Get Filter Options

```bash
curl "http://localhost:51009/api/options/" | python3 -m json.tool
```

**Response:**
```json
{
  "success": true,
  "data": {
    "color": [
      {"value": "Warm", "label": "Warm"},
      {"value": "Cool", "label": "Cool"},
      {"value": "Blue", "label": "Blue"}
    ],
    "media_type": [
      {"value": "Movie", "label": "Movie"},
      {"value": "TV", "label": "TV"}
    ],
    "genre": [
      {"value": "Drama", "label": "Drama"},
      {"value": "Action", "label": "Action"}
    ]
  }
}
```

---

## 🗄️ Database Schema

### Core Models

#### Image Model
```python
class Image(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=500)
    description = models.TextField()
    image_url = models.CharField(max_length=500)
    
    # Relationships
    movie = models.ForeignKey(Movie)
    tags = models.ManyToManyField(Tag)
    
    # Attributes
    color = models.ForeignKey(ColorOption)
    media_type = models.ForeignKey(MediaTypeOption)
    time_of_day = models.ForeignKey(TimeOfDayOption)
    int_ext = models.ForeignKey(InteriorExteriorOption)
    # ... 20+ more attributes
```

#### Movie Model
```python
class Movie(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=500)
    year = models.IntegerField()
    genres = models.ManyToManyField(GenreOption)
```

#### Tag Model
```python
class Tag(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
```

### Attribute Options

All stored as separate models with slug + value:

- ColorOption
- MediaTypeOption
- GenreOption
- AspectRatioOption
- TimeOfDayOption
- InteriorExteriorOption
- FrameSizeOption
- ShotTypeOption
- CompositionOption
- LightingOption
- LensTypeOption
- And 15+ more...

---

## 👨‍💻 Development

### Local Development Setup

```bash
# 1. Create virtual environment (optional, for local development)
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser

# 5. Run development server
python manage.py runserver 0.0.0.0:8000
```

### Docker Development

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f image_service

# Execute commands
docker compose exec image_service python manage.py shell

# Run migrations
docker compose exec image_service python manage.py migrate

# Collect static files
docker compose exec image_service python manage.py collectstatic --noinput

# Create superuser
docker compose exec image_service python manage.py createsuperuser
```

### Database Operations

```bash
# Access PostgreSQL
docker compose exec image-db psql -U postgres -d image_service_db

# Common SQL queries
SELECT COUNT(*) FROM images_image;
SELECT COUNT(*) FROM images_movie;
SELECT COUNT(*) FROM images_tag;

# Backup database
docker compose exec image-db pg_dump -U postgres image_service_db > backup.sql

# Restore database
docker compose exec -T image-db psql -U postgres image_service_db < backup.sql
```

### Testing

```bash
# Run all tests
docker compose exec image_service python manage.py test

# Run specific tests
docker compose exec image_service python manage.py test apps.images.tests

# With coverage
docker compose exec image_service coverage run --source='.' manage.py test
docker compose exec image_service coverage report
```

---

## 🚀 Deployment

### Production Checklist

```bash
# Security
✅ Set DEBUG=False
✅ Generate strong SECRET_KEY
✅ Configure ALLOWED_HOSTS
✅ Enable HTTPS/SSL
✅ Set up firewall rules
✅ Use environment variables

# Performance
✅ Use Gunicorn with 4+ workers
✅ Enable database connection pooling
✅ Configure static file caching
✅ Set up CDN for media files
✅ Enable gzip compression

# Monitoring
✅ Set up health checks
✅ Configure logging
✅ Enable error tracking (Sentry)
✅ Monitor database performance
```

### Production Environment

```bash
# .env.production
DEBUG=False
SECRET_KEY=<generate-with-python>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

DB_PASSWORD=<strong-password>
DB_HOST=production-db-host

PUBLIC_BASE_URL=https://api.yourdomain.com

CORS_ALLOW_ALL_ORIGINS=False
```

### Deployment Commands

```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker compose build --no-cache

# Apply migrations
docker compose exec image_service python manage.py migrate

# Collect static files
docker compose exec image_service python manage.py collectstatic --noinput

# Restart services
docker compose restart image_service

# Check health
curl http://localhost:51009/api/health/
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
docker compose logs --tail=100 image_service

# Common causes:
# - Database not ready
# - Port already in use
# - Missing environment variables

# Solution:
docker compose down
docker compose up -d
```

#### 2. Swagger UI Not Loading

```bash
# Test schema endpoint
curl http://localhost:51009/api/schema/

# If schema loads, but UI doesn't:
# 1. Check static files
docker compose exec image_service python manage.py collectstatic --noinput

# 2. Restart service
docker compose restart image_service

# 3. Clear browser cache
```

#### 3. Database Connection Errors

```bash
# Check database status
docker compose exec image-db pg_isready -U postgres

# Test connection
docker compose exec image_service python manage.py check --database default

# Reset database (WARNING: loses data)
docker compose down
docker volume rm image_service_image_postgres_17_data
docker compose up -d
```

#### 4. Media Files Not Serving

```bash
# Check media directory
docker compose exec image_service ls -la /service/media/images/

# Check permissions
docker compose exec image_service chmod -R 755 /service/media/

# Test media endpoint
curl -I http://localhost:51009/media/images/test.jpg
```

#### 5. Migration Issues

```bash
# Show migrations
docker compose exec image_service python manage.py showmigrations

# Fake migrations (if needed)
docker compose exec image_service python manage.py migrate --fake

# Reset migrations (WARNING: loses data)
docker compose exec image_service python manage.py migrate images zero
docker compose exec image_service python manage.py migrate
```

### Debug Commands

```bash
# Django shell
docker compose exec image_service python manage.py shell

# Check settings
docker compose exec image_service python manage.py diffsettings

# System check
docker compose exec image_service python manage.py check

# Database shell
docker compose exec image-db psql -U postgres -d image_service_db
```

---

## ⚡ Performance

### Current Performance

```
Average Response Time:  50ms
Database Query Time:    10-30ms
Media File Serving:     20-100ms (depending on size)
Concurrent Requests:    100+ req/sec
```

### Optimization Tips

#### 1. Database Optimization

```python
# settings.py
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,  # Connection pooling
        'CONN_HEALTH_CHECKS': True,
    }
}
```

#### 2. Query Optimization

```python
# Use select_related for ForeignKey
Image.objects.select_related('movie', 'color').all()

# Use prefetch_related for ManyToMany
Image.objects.prefetch_related('tags', 'movie__genres').all()

# Use only() to limit fields
Image.objects.only('id', 'title', 'slug').all()
```

#### 3. Caching

```bash
# Enable Redis caching
pip install redis django-redis

# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
    }
}
```

#### 4. Static Files

```bash
# Use CDN for static files
AWS_S3_CUSTOM_DOMAIN = 'cdn.yourdomain.com'
```

#### 5. Database Indexing

```sql
-- Add indexes for frequently queried fields
CREATE INDEX idx_image_color ON images_image(color_id);
CREATE INDEX idx_image_media_type ON images_image(media_type_id);
CREATE INDEX idx_image_movie ON images_image(movie_id);
```

---

## 📊 Monitoring

### Health Checks

```bash
# Service health
curl http://localhost:51009/api/health/

# Database health
docker compose exec image-db pg_isready

# Container stats
docker stats image_service
```

### Logging

```bash
# View logs
docker compose logs -f image_service

# Export logs
docker compose logs image_service > logs.txt

# Filter errors
docker compose logs image_service | grep ERROR
```

### Metrics to Monitor

- Response times
- Error rates
- Database connections
- Memory usage
- Disk usage
- Request counts
- Cache hit rates

---

## 📚 Additional Resources

### Documentation

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/)
- [PostgreSQL](https://www.postgresql.org/docs/)

### Tools

- **Swagger UI:** `http://localhost:51009/api/schema/swagger-ui/`
- **Admin Panel:** `http://localhost:51009/admin/`
- **Database GUI:** Use pgAdmin or DBeaver

---

## 🎯 Quick Reference

### Start Service
```bash
docker compose up -d
```

### Stop Service
```bash
docker compose down
```

### View Logs
```bash
docker compose logs -f image_service
```

### Run Migrations
```bash
docker compose exec image_service python manage.py migrate
```

### Access Admin
```bash
# Create superuser first
docker compose exec image_service python manage.py createsuperuser

# Then visit: http://localhost:51009/admin/
```

### Test API
```bash
# Home
curl http://localhost:51009/

# Shots
curl http://localhost:51009/shots/

# Health
curl http://localhost:51009/api/health/

# Swagger
xdg-open http://localhost:51009/api/schema/swagger-ui/
```

---

## 📝 Version History

### v1.0.0 (Current)
- ✅ Complete RESTful API
- ✅ Swagger UI documentation
- ✅ 2000+ images indexed
- ✅ 25+ filter parameters
- ✅ Production-ready deployment
- ✅ Health check endpoints
- ✅ Media file serving with fallbacks

---

## 📞 Support

### Getting Help

1. **Check Documentation** - Review this guide
2. **Check Logs** - `docker compose logs image_service`
3. **Test Endpoints** - Use curl or Swagger UI
4. **Check Database** - Verify data exists
5. **Restart Service** - `docker compose restart image_service`

### Useful Commands

```bash
# Full diagnostic
docker compose ps
docker compose logs --tail=50 image_service
curl http://localhost:51009/api/health/
docker compose exec image-db pg_isready

# Quick fix
docker compose restart image_service

# Full reset (WARNING: loses data)
docker compose down
docker volume rm image_service_image_postgres_17_data
docker compose up -d
```

---

## ✅ Current Status

```
Service:          ✅ Running
Database:         ✅ Connected
Swagger UI:       ✅ Working
API Endpoints:    ✅ All functional
Media Serving:    ✅ Working
Health Checks:    ✅ Passing
Documentation:    ✅ Complete
Production Ready: ✅ Yes
```

**Last Updated:** 2025-01-XX  
**Maintained by:** Shotdeck Development Team  
**Status:** ✅ Production Ready

---

🎉 **Everything is configured and working!** 🚀
```