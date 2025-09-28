from django.urls import path
from .views import AuthView, UserProfileView

urlpatterns = [
    path('auth/', AuthView.as_view(), name='auth'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]
