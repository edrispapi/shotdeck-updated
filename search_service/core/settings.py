from pathlib import Path
import os
from decouple import config
import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-dev-key-change-in-production'

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',  # WhiteNoise for static files
    'corsheaders',  # CORS headers
    'rest_framework', 'drf_spectacular', 'drf_spectacular_sidecar', 'django_elasticsearch_dsl', 'apps.common'

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
        'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug', 'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# SQLite configuration (temporary fix for PostgreSQL issues)
DATABASES = {
    'default': dj_database_url.config(default=config('DATABASE_URL'))
}

ELASTICSEARCH_DSL = {
    'default': {
        'hosts': f"http://{config('ELASTICSEARCH_HOST', 'localhost')}:{int(config('ELASTICSEARCH_PORT', default=9200))}"
    },
    'signals': { 'auto_discover': False },
}

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Shotdeck Search Service API',
    'DESCRIPTION': 'Powerful API for advanced image search using Elasticsearch with Redis caching.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'SECURITY': [{"tokenAuth": {"type": "apiKey", "in": "header", "name": "Authorization", "description": "Enter token like this: Token <YOUR_TOKEN>"}}],
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'docExpansion': 'list',
        'filter': True
    },
    'SERVE_PUBLIC': True,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'POSTPROCESSING_HOOKS': ['search_service.utils.postprocess_schema'],
    'SORT_OPERATIONS': False,
}

# Redis Cache Configuration - Temporarily disabled
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': f"redis://{config('REDIS_HOST', default='redis')}:{config('REDIS_PORT', default='6379')}/1",
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }

# User Management API Configuration
USER_MANAGEMENT_API_URL = 'http://127.0.0.1:12700/api/v1'
USER_API_TIMEOUT = 10

KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_CONSUMER_GROUP = 'search_service_group'

# Elasticsearch configuration - disabled for development
ELASTICSEARCH_ENABLED = config('ELASTICSEARCH_ENABLED', default=False, cast=bool)

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I8N = True
USE_TZ = True
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