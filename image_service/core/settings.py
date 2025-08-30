from pathlib import Path
from decouple import config

# BASE_DIR به ریشه پوشه image_service اشاره می‌کند.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- تنظیمات اصلی و امنیتی ---
SECRET_KEY = config('SECRET_KEY', default='django-insecure-a_very_secret_key_for_the_image_service_default')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['*']

# --- تعریف اپلیکیشن‌های نصب شده ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'drf_spectacular',

    # Local apps for this service
    'apps.images',
]

# --- میان‌افزارها (Middleware) ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- مسیردهی اصلی ---
ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'

# --- پیکربندی Template Engine (مورد نیاز برای پنل ادمین) ---
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

# --- پیکربندی دیتابیس اختصاصی ---
# مقادیر از فایل .env خوانده می‌شوند.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='image_db'),
        'USER': config('DB_USER', default='image_user'),
        'PASSWORD': config('DB_PASSWORD', default='image_password'),
        'HOST': config('DB_HOST', default='image_db'), # <-- اصلاح کلیدی
        'PORT': config('DB_PORT', default=5432, cast=int)
    }
}

# --- تنظیمات Django REST Framework ---
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ]
}

# --- تنظیمات drf-spectacular برای مستندات API ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'Shotdeck Image Service API',
    'DESCRIPTION': 'API برای مدیریت (CRUD) تصاویر و متادیتای آنها. این سرویس منبع اصلی حقیقت برای داده‌های تصاویر است.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# --- تنظیمات Kafka ---
KAFKA_BOOTSTRAP_SERVERS = [config('KAFKA_BROKER', default='kafka:9092')]

# --- تنظیمات احراز هویت ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}
]

# --- تنظیمات بین‌المللی‌سازی ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- تنظیمات فایل‌های استاتیک ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- نوع کلید اصلی پیش‌فرض برای مدل‌ها ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'