from django.contrib import admin
from django.contrib.admin import ModelAdmin, TabularInline
from .models import (
    Movie, Image, Tag,
    DirectorOption, CinematographerOption, EditorOption,
    ActorOption, GenreOption, ColorOption, MediaTypeOption,
    AspectRatioOption, OpticalFormatOption, FormatOption,
    TimePeriodOption, LabProcessOption, InteriorExteriorOption,
    TimeOfDayOption, NumberOfPeopleOption, GenderOption,
    AgeOption, EthnicityOption, FrameSizeOption, ShotTypeOption,
    CompositionOption, LensSizeOption, LensTypeOption,
    LightingOption, LightingTypeOption, CameraTypeOption,
    ResolutionOption, FrameRateOption, MovieOption,
    CameraOption, LensOption, LocationOption, SettingOption,
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption
)


# Inline classes for related objects
class ImageInline(admin.TabularInline):
    model = Image
    extra = 0
    fields = ('title', 'image_url', 'created_at')
    readonly_fields = ('created_at',)
    show_change_link = True
    max_num = 10  # Limit to avoid performance issues


class MovieInline(admin.TabularInline):
    model = Movie
    extra = 0
    fields = ('title', 'year', 'created_at')
    readonly_fields = ('created_at',)
    show_change_link = True
    max_num = 5


# Base admin class for option models
class BaseOptionAdmin(ModelAdmin):
    list_display = ('value', 'display_order', 'created_at', 'updated_at')
    list_editable = ('display_order',)
    search_fields = ('value',)
    ordering = ('display_order', 'value')
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


# Movie admin
@admin.register(Movie)
class MovieAdmin(ModelAdmin):
    list_display = ('title', 'year', 'genre', 'director', 'cinematographer', 'editor', 'image_count')
    list_filter = ('year', 'director', 'cinematographer', 'editor', 'country', 'language')
    search_fields = ('title', 'genre', 'director__value', 'cinematographer__value', 'editor__value', 'cast')
    ordering = ('-year', 'title')
    readonly_fields = ('slug', 'image_count')
    list_per_page = 25
    inlines = [ImageInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'year', 'genre', 'description', 'duration', 'country', 'language')
        }),
        ('Crew', {
            'fields': ('director', 'cinematographer', 'editor', 'colorist', 'production_designer', 'costume_designer', 'cast')
        }),
        ('Metadata', {
            'fields': ('image_count',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'director', 'cinematographer', 'editor'
        ).prefetch_related('images')


# Image admin
@admin.register(Image)
class ImageAdmin(ModelAdmin):
    list_display = ('title', 'movie', 'media_type', 'color', 'created_at')
    list_filter = (
        'media_type', 'color', 'time_period', 'interior_exterior', 'created_at'
    )
    search_fields = ('title', 'description', 'movie__title')
    ordering = ('-created_at',)
    readonly_fields = ('slug', 'created_at', 'updated_at')
    list_per_page = 50
    raw_id_fields = ('movie',)  # Use raw ID field for better performance with large datasets

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'image_url', 'movie')
        }),
        ('Technical Details', {
            'fields': (
                'media_type', 'aspect_ratio', 'time_period', 'interior_exterior',
                'shot_type', 'lighting', 'color'
            ),
            'classes': ('collapse',)
        }),
        ('People & Objects', {
            'fields': (
                'actor', 'director', 'cinematographer', 'location'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('tags', 'release_year', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'movie', 'media_type', 'color', 'aspect_ratio',
            'actor', 'camera', 'lens', 'location'
        ).prefetch_related('genre')


# Tag admin
@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    ordering = ('name',)
    readonly_fields = ('slug',)
    list_per_page = 100


# Register all option models with the base admin
option_models = [
    DirectorOption, CinematographerOption, EditorOption,
    ActorOption, GenreOption, ColorOption, MediaTypeOption,
    AspectRatioOption, OpticalFormatOption, FormatOption,
    TimePeriodOption, LabProcessOption, InteriorExteriorOption,
    TimeOfDayOption, NumberOfPeopleOption, GenderOption,
    AgeOption, EthnicityOption, FrameSizeOption, ShotTypeOption,
    CompositionOption, LensSizeOption, LensTypeOption,
    LightingOption, LightingTypeOption, CameraTypeOption,
    ResolutionOption, FrameRateOption, MovieOption,
    CameraOption, LensOption, LocationOption, SettingOption,
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption
]

for model in option_models:
    admin.site.register(model, BaseOptionAdmin)


# Admin site customization
admin.site.site_header = "ShotDeck Admin"
admin.site.site_title = "ShotDeck Admin Portal"
admin.site.index_title = "Welcome to ShotDeck Administration"