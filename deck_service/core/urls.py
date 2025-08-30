from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),

    # اتصال API های اپ decks به مسیر اصلی
    path('api/v1/', include('apps.decks.api.v1.urls')),

    # اندپوینت برای دریافت توکن احراز هویت
    path('api/v1/api-token-auth/', obtain_auth_token, name='api_token_auth'),

    # URL های drf-spectacular برای مستندات API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]