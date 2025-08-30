import os
from django.core.wsgi import get_wsgi_application

# --- اصلاح نهایی: مسیر صحیح settings module ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'image_service.image_service.settings')

application = get_wsgi_application()