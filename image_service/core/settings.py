from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-a_very_secret_key_for_the_image_service_default')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', '0.0.0.0', 'image_service', 'image_service:8000']

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',  # WhiteNoise for static files
    'corsheaders',  # CORS headers
    'rest_framework', 'rest_framework.authtoken', 'django_filters',
    'apps.images', 'apps.common',
]

# Ultra-fast middleware - minimal but functional
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS middleware
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add WhiteNoise for static files
    'django.contrib.sessions.middleware.SessionMiddleware',  # Required for admin
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Required for admin
    'django.contrib.messages.middleware.MessageMiddleware',  # Required for admin
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'image_service' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug', 'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Database configuration - Use DATABASE_URL if provided, otherwise PostgreSQL or SQLite
DATABASE_URL = config('DATABASE_URL', default=None)

# Ultra-fast database configuration
if DATABASE_URL:
    print(f"Using DATABASE_URL: {DATABASE_URL}")
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=300, conn_health_checks=True)
    }
else:
    # Default to PostgreSQL for Docker environment - SQLite removed
    print("Using PostgreSQL database - ULTRA OPTIMIZED FOR PRODUCTION")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='postgres'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 300,  # Keep connections alive longer
            'CONN_HEALTH_CHECKS': True,  # Health checks for connection pooling
            'OPTIONS': {
                'connect_timeout': 10,
                'options': (
                    '-c statement_timeout=30000ms '  # 30 second query timeout
                    '-c work_mem=64MB '  # Increase working memory for complex queries
                    '-c maintenance_work_mem=256MB '  # More memory for maintenance operations
                    '-c shared_preload_libraries=pg_stat_statements '  # Enable query statistics
                    '-c random_page_cost=1.1 '  # Optimize for SSD storage
                    '-c effective_cache_size=2GB '  # Assume 2GB cache
                    '-c checkpoint_completion_target=0.9 '  # Faster checkpoints
                    '-c wal_buffers=16MB '  # Larger WAL buffers
                    '-c default_statistics_target=100 '  # Better statistics
                ),
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
                'application_name': 'shotdeck_image_service',  # Identify connections
            },
            'ATOMIC_REQUESTS': False,  # Disable for performance
            'AUTOCOMMIT': True,  # Enable autocommit for better performance
            'DISABLE_SERVER_SIDE_CURSORS': True,  # Better for small result sets
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.TokenAuthentication', 'rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],  # Ultra-fast: Allow all access
    # Use project custom pagination which sets default page size to 20 and
    # enforces a maximum page_size of 20 when clients pass `page_size`.
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.CustomPageNumberPagination',
    'PAGE_SIZE': 20,  # Default page size and max enforced by the pagination class
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],  # Removed BrowsableAPIRenderer for speed
    'DEFAULT_THROTTLE_CLASSES': [],  # Disable throttling for maximum speed
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'NUM_PROXIES': None,  # Performance optimization
    'USE_X_FORWARDED_HOST': True,  # Respect proxy headers for correct host in URLs
    'UNICODE_JSON': False,  # Faster JSON encoding
}

# Ultra-fast caching configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'OPTIONS': {
            'MAX_ENTRIES': 10000,  # Large cache for API responses
        }
    }
}

# Cache API responses for 5 minutes
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'shotdeck'

# Performance optimizations
USE_TZ = False  # Disable timezone handling for speed
USE_I18N = False  # Disable internationalization for speed
USE_L10N = False  # Disable localization for speed

# Database query optimizations
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging - minimal for performance
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',  # Only show warnings and errors
        },
        'apps': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
}

# Security optimizations for performance
SECRET_KEY = config('SECRET_KEY', default='ultra-fast-secret-key-for-performance')
DEBUG = config('DEBUG', default=False, cast=bool)  # Disable debug for production speed
# Honor proxy SSL/header settings when behind a load balancer/reverse proxy
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_PORT = True

# Increase limit for admin filters with many options
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100000  # Allow very large admin filter/query payloads

# Whitenoise optimizations
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG

# CORS optimizations
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins for speed
CORS_ALLOW_CREDENTIALS = False  # Disable credentials for speed


# Kafka configuration for integration with deck_search
KAFKA_BOOTSTRAP_SERVERS = config('KAFKA_BOOTSTRAP_SERVERS', default='kafka-1:29092,kafka-2:29092,kafka-3:29092')
KAFKA_ENABLED = config('KAFKA_ENABLED', default=True, cast=bool)
KAFKA_IMAGE_CREATED_TOPIC = config('KAFKA_IMAGE_CREATED_TOPIC', default='image_created')
KAFKA_IMAGE_UPDATED_TOPIC = config('KAFKA_IMAGE_UPDATED_TOPIC', default='image_updated')
KAFKA_IMAGE_DELETED_TOPIC = config('KAFKA_IMAGE_DELETED_TOPIC', default='image_deleted')


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I8N = True
USE_TZ = True

# Static files configuration only (no media files)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# S3 Storage Configuration
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='shotdeck-image-service')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# Service-specific S3 buckets
S3_BUCKETS = {
    'image_service': config('IMAGE_SERVICE_BUCKET', default='shotdeck-image-service'),
    'deck_search': config('DECK_SEARCH_BUCKET', default='shotdeck-deck-search'),
    'deck_service': config('DECK_SERVICE_BUCKET', default='shotdeck-deck-service'),
}

# Media files configuration for serving images
MEDIA_URL = '/media/'
MEDIA_ROOT = Path('/service/media')

# Public base URL used when request is unavailable (e.g., background tasks)
# Example: https://image.example.com
PUBLIC_BASE_URL = config('PUBLIC_BASE_URL', default='')

# Ensure media directory exists
import os
try:
    os.makedirs(MEDIA_ROOT, exist_ok=True)
except PermissionError:
    # Fallback to project-local media directory if root path is not writable
    MEDIA_ROOT = BASE_DIR / 'media'
    os.makedirs(MEDIA_ROOT, exist_ok=True)

images_dir = os.path.join(MEDIA_ROOT, 'images')
if not (os.path.exists(images_dir) or os.path.islink(images_dir)):
    os.makedirs(images_dir, exist_ok=True)

# Static files configuration (keeping WhiteNoise for static)

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins for development
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]