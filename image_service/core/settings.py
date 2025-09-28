from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-a_very_secret_key_for_the_image_service_default')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',  # WhiteNoise for static files
    'corsheaders',  # CORS headers
    'rest_framework', 'rest_framework.authtoken', 'django_filters', 'drf_spectacular', 'drf_spectacular_sidecar',
    'apps.images', 'apps.common',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS middleware
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add WhiteNoise for static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
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

# PostgreSQL database for data storage
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='shotdeck_db'),
        'USER': config('DB_USER', default='shotdeck_user'),
        'PASSWORD': config('DB_PASSWORD', default='shotdeck_password'),
        'HOST': config('DB_HOST', default='postgres'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.TokenAuthentication', 'rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ]
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Shotdeck Image Service API',
    'DESCRIPTION': 'API for managing images and their metadata.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'SCHEMA_PATH_PREFIX': '/api',
    'SERVE_URLCONF': None,
    'SCHEMA_PATH_PREFIX_TRIM': False,
    'DEFAULT_SCHEMA_RENDERER': 'drf_spectacular.renderers.OpenApiJsonRenderer',
    'SWAGGER_UI_SETTINGS': {
        'urls': {
            'swaggerUi': '/static/drf_spectacular_sidecar/swagger-ui-dist/',
        },
        'url': '/api/schema/?format=json',
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'docExpansion': 'list',
        'filter': True,
    },
    'SECURITY': [{"tokenAuth": {"type": "apiKey", "in": "header", "name": "Authorization", "description": "Enter token like this: Token <YOUR_TOKEN>"}}],
    'SERVE_PUBLIC': True,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'POSTPROCESSING_HOOKS': ['image_service.utils.postprocess_schema'],
    'SORT_OPERATIONS': False,
    # Exclude all options endpoints from Swagger documentation
    'EXCLUDE_PATH_PATTERNS': [
        r'/api/options/.*',  # Exclude all /api/options/ endpoints
    ],
}

# Kafka configuration - disabled for development
KAFKA_BOOTSTRAP_SERVERS = config('KAFKA_BOOTSTRAP_SERVERS', default='localhost:9092')
KAFKA_ENABLED = config('KAFKA_ENABLED', default=False, cast=bool)


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
    'search_service': config('SEARCH_SERVICE_BUCKET', default='shotdeck-search-service'),
    'deck_service': config('DECK_SERVICE_BUCKET', default='shotdeck-deck-service'),
}

# Media files configuration for serving images
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Ensure media directory exists
import os
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, 'images'), exist_ok=True)

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