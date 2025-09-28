from django.urls import path
from .views import ImageColorSamplesView, ImageColorSearchView

# Image-related endpoints for /api/images/
urlpatterns = [
    path('<slug:slug>/color_samples/', ImageColorSamplesView.as_view(), name='image-color-samples'),
    path('search_by_color/', ImageColorSearchView.as_view(), name='image-color-search'),
]
