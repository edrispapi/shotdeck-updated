from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from .views import (
    ImageViewSet, MovieViewSet, TagViewSet, FiltersView,
    # Option ViewSets
    GenreOptionViewSet, ColorOptionViewSet, MediaTypeOptionViewSet,
    AspectRatioOptionViewSet, OpticalFormatOptionViewSet, FormatOptionViewSet,
    InteriorExteriorOptionViewSet, TimeOfDayOptionViewSet, NumberOfPeopleOptionViewSet,
    GenderOptionViewSet, AgeOptionViewSet, EthnicityOptionViewSet,
    FrameSizeOptionViewSet, ShotTypeOptionViewSet, CompositionOptionViewSet,
    LensSizeOptionViewSet, LensTypeOptionViewSet, LightingOptionViewSet,
    LightingTypeOptionViewSet, CameraTypeOptionViewSet, ResolutionOptionViewSet,
    FrameRateOptionViewSet, MovieOptionViewSet, ActorOptionViewSet, CameraOptionViewSet,
    LensOptionViewSet, LocationOptionViewSet, SettingOptionViewSet,
    FilmStockOptionViewSet, ShotTimeOptionViewSet,
    DescriptionOptionViewSet, VfxBackingOptionViewSet
)

# Create router for option endpoints
router = DefaultRouter()
router.register(r'options/genre', GenreOptionViewSet, basename='genre-option')
router.register(r'options/color', ColorOptionViewSet, basename='color-option')
router.register(r'options/media-type', MediaTypeOptionViewSet, basename='media-type-option')
router.register(r'options/aspect-ratio', AspectRatioOptionViewSet, basename='aspect-ratio-option')
router.register(r'options/optical-format', OpticalFormatOptionViewSet, basename='optical-format-option')
router.register(r'options/film-format', FormatOptionViewSet, basename='format-option')
router.register(r'options/interior-exterior', InteriorExteriorOptionViewSet, basename='interior-exterior-option')
router.register(r'options/time-of-day', TimeOfDayOptionViewSet, basename='time-of-day-option')
router.register(r'options/number-of-people', NumberOfPeopleOptionViewSet, basename='number-of-people-option')
router.register(r'options/gender', GenderOptionViewSet, basename='gender-option')
router.register(r'options/age', AgeOptionViewSet, basename='age-option')
router.register(r'options/ethnicity', EthnicityOptionViewSet, basename='ethnicity-option')
router.register(r'options/frame-size', FrameSizeOptionViewSet, basename='frame-size-option')
router.register(r'options/shot-type', ShotTypeOptionViewSet, basename='shot-type-option')
router.register(r'options/composition', CompositionOptionViewSet, basename='composition-option')
router.register(r'options/lens-size', LensSizeOptionViewSet, basename='lens-size-option')
router.register(r'options/lens-type', LensTypeOptionViewSet, basename='lens-type-option')
router.register(r'options/lighting', LightingOptionViewSet, basename='lighting-option')
router.register(r'options/lighting-type', LightingTypeOptionViewSet, basename='lighting-type-option')
router.register(r'options/camera-type', CameraTypeOptionViewSet, basename='camera-type-option')
router.register(r'options/resolution', ResolutionOptionViewSet, basename='resolution-option')
router.register(r'options/frame-rate', FrameRateOptionViewSet, basename='frame-rate-option')
router.register(r'options/movie', MovieOptionViewSet, basename='movie-option')
router.register(r'options/actor', ActorOptionViewSet, basename='actor-option')
router.register(r'options/camera', CameraOptionViewSet, basename='camera-option')
router.register(r'options/lens', LensOptionViewSet, basename='lens-option')
router.register(r'options/location', LocationOptionViewSet, basename='location-option')
router.register(r'options/setting', SettingOptionViewSet, basename='setting-option')
router.register(r'options/film-stock', FilmStockOptionViewSet, basename='film-stock-option')
router.register(r'options/shot-time', ShotTimeOptionViewSet, basename='shot-time-option')
router.register(r'options/description', DescriptionOptionViewSet, basename='description-option')
router.register(r'options/vfx-backing', VfxBackingOptionViewSet, basename='vfx-backing-option')

def tags_not_allowed(request):
    """Return 404 for tags list endpoint"""
    return JsonResponse({"error": "Tags list endpoint is not available"}, status=404)

urlpatterns = [
    # Include router URLs for options
    path('', include(router.urls)),

    # Images
    path('images/', ImageViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='image-list'),
    # Filters endpoint (must come before image detail to avoid slug conflict)
    path('images/filters/', FiltersView.as_view(), name='image-filters'),
    path('image/<slug:slug>/', ImageViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='image-detail'),
    path('image/<slug:slug>/dataset/', ImageViewSet.as_view({
        'get': 'get_dataset'
    }), name='image-dataset'),


    # Movie endpoints
    path('movie/<slug:slug>/', MovieViewSet.as_view({
        'get': 'retrieve'
    }), name='image-movie'),
    path('movie/<slug:slug>/images/', MovieViewSet.as_view({
        'get': 'get_movie_images'
    }), name='movie-images'),

    # Tags - Only detail endpoint (list completely removed)
    path('tags/<slug:slug>/', TagViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='tag-detail'),

]