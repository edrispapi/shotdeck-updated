from django.contrib import admin
from django.urls import path, include
from django. http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

def home_view(request):
    return JsonResponse({
        "service": "Deck Service",
        "version": "1.0.0",
        "description": "deck service Shotdeck",
        "endpoints": {
            "api": "/api/",
            "admin": "/admin/",
            "docs": "/api/schema/swagger-ui/",
            "auth": "/api/auth/",
            "token": "/api/api-token-auth/"
        },
        "status": "running",
        "timestamp": request.META.get('HTTP_HOST', 'localhost')
    })

urlpatterns = [
    path('', home_view, name='home'),

    path('admin/', admin.site.urls),

    # Connect decks app APIs to main path
    path('api/', include('apps.decks.api.urls')),

    # Connect authentication APIs
    path('api/auth/', include('apps.auth.api.urls')),

    # Endpoint for obtaining authentication token
    path('api/api-token-auth/', obtain_auth_token, name='api_token_auth'),

    # drf-spectacular URLs for API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]