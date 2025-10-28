from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-a_very_secret_key_for_the_deck_service_default')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['*']

# AUTH_USER_MODEL = 'apps_auth.User'  # Commented out to avoid migration issues

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',  # WhiteNoise for static files
    'rest_framework', 'rest_framework.authtoken', 'drf_spectacular', 'drf_spectacular_sidecar',
    'apps.auth', 'apps.decks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

# PostgreSQL configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='deck_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres123'),
        'HOST': config('DB_HOST', default='deck_db'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'client_encoding': 'UTF8',
        },
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
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated']
}

# Pagination defaults: default page size 20 and maximum page size 20
REST_FRAMEWORK.setdefault('DEFAULT_PAGINATION_CLASS', 'core.pagination.CustomPageNumberPagination')
REST_FRAMEWORK.setdefault('PAGE_SIZE', 20)

SPECTACULAR_SETTINGS = {
    'TITLE': 'Shotdeck Deck Service API',
    'DESCRIPTION': 'API for managing image decks and collections',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_DIST': 'SIDECAR',  # Use SIDECAR with drf-spectacular-sidecar
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'docExpansion': 'list',
        'filter': True
    },
    'SECURITY': [{"tokenAuth": {"type": "apiKey", "in": "header", "name": "Authorization", "description": "Enter token as: Token <YOUR_TOKEN>"}}],
    'SERVE_PUBLIC': True,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'POSTPROCESSING_HOOKS': ['deck_service.utils.postprocess_schema'],
    'SORT_OPERATIONS': False,
}

# Kafka configuration - disabled for development
KAFKA_ENABLED = config('KAFKA_ENABLED', default=False, cast=bool)
KAFKA_BOOTSTRAP_SERVERS = config('KAFKA_BOOTSTRAP_SERVERS', default='localhost:9092')
KAFKA_CONSUMER_GROUP = 'deck_service_group'
KAFKA_TOPICS_TO_CONSUME = ['user_created', 'user_vip_activated', 'user_access_check', 'image_deleted']


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