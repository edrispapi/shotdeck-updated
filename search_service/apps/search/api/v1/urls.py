# مسیر: /home/mdk/Documents/shotdeck-main/search_service/apps/search/api/v1/urls.py
from django.urls import path
from .views import SearchView, SimilarImagesView

urlpatterns = [
    # URL برای جستجوی اصلی: /api/v1/search/images/
    path('images/', SearchView.as_view(), name='search-images'),
    
    # URL برای پیدا کردن تصاویر مشابه: /api/v1/search/similar/<id>/
    path('similar/<int:pk>/', SimilarImagesView.as_view(), name='similar-images'),
]