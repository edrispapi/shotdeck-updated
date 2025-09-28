# image_service/apps/images/apps.py

from django.apps import AppConfig

class ImagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.images'

    def ready(self):
        import apps.images.signals
