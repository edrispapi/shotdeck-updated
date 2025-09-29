from django.urls import path
from .views import SimilarImagesView, UserView, ColorSimilaritySearchView, FiltersView

# Main search endpoints for /api/search/
urlpatterns = [
    path('similar/<slug:slug>/', SimilarImagesView.as_view(), name='similar-images'),
    path('color-similarity/', ColorSimilaritySearchView.as_view(), name='color-similarity'),
    path('user/', UserView.as_view(), name='user-info'),
    path('filters/', FiltersView.as_view(), name='filters'),
]
