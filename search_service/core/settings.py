# مسیر: /home/mdk/Documents/shotdeck-main/search_service/core/settings.py
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',
    'drf_spectacular',
    'django_elasticsearch_dsl',
    'django_elasticsearch_dsl_drf',
    
    'apps.search',
    'apps.common',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- تغییر کلیدی: اضافه کردن پروتکل http:// به آدرس هاست ---
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': f"http://{config('ELASTICSEARCH_HOST', default='elasticsearch')}:{config('ELASTICSEARCH_PORT', default=9200, cast=int)}"
    },
    'signals': {
        'auto_discover': False,
    },
}

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Shotdeck Search Service API',
    'DESCRIPTION': 'API قدرتمند برای جستجوی پیشرفته تصاویر با استفاده از Elasticsearch',
    'VERSION': '1.0.0',
}

KAFKA_BOOTSTRAP_SERVERS = [config('KAFKA_BROKER', default='kafka:9092')]
KAFKA_CONSUMER_GROUP = 'search_service_group'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I8N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'