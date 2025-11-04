# -*- coding: utf-8 -*-
"""
All serializers for the Image Service.
Primary key for Image model is now UUID → every field list uses `uuid`.
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, OpenApiTypes
from django.conf import settings
from django.utils._os import safe_join
from apps.images.models import (
    Image, Movie, Tag,
    # Base option models
    BaseOption, GenreOption, ColorOption, MediaTypeOption, AspectRatioOption,
    OpticalFormatOption, FormatOption, InteriorExteriorOption, TimeOfDayOption,
    NumberOfPeopleOption, GenderOption, AgeOption, EthnicityOption,
    FrameSizeOption, ShotTypeOption, CompositionOption, LensSizeOption,
    LensTypeOption, LightingOption, LightingTypeOption, CameraTypeOption,
    ResolutionOption, FrameRateOption, MovieOption, ActorOption, CameraOption,
    LensOption, LocationOption, SettingOption,
    FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption,
    DirectorOption, CinematographerOption, EditorOption,
    ColoristOption, CostumeDesignerOption, ProductionDesignerOption,
    # New models
    ShadeOption, ArtistOption, FilmingLocationOption, LocationTypeOption, YearOption
)
from messaging.producers import send_event


# --------------------------------------------------------------------------- #
#  BASIC / OPTION SERIALIZERS (must be defined first)
# --------------------------------------------------------------------------- #
class BaseOptionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'value', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        model = None  # Sub-classes will set the concrete model


# --------------------------------------------------------------------------- #
#  Concrete option serializers (order matters – OptionSerializer is used later)
# --------------------------------------------------------------------------- #
class GenreOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = GenreOption


class ColorOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = ColorOption


class MediaTypeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = MediaTypeOption


class AspectRatioOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = AspectRatioOption


class OpticalFormatOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = OpticalFormatOption


class FormatOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = FormatOption


class InteriorExteriorOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = InteriorExteriorOption


class TimeOfDayOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = TimeOfDayOption


class NumberOfPeopleOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = NumberOfPeopleOption


class GenderOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = GenderOption


class AgeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = AgeOption


class EthnicityOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = EthnicityOption


class FrameSizeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = FrameSizeOption


class ShotTypeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = ShotTypeOption


class CompositionOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = CompositionOption


class LensSizeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = LensSizeOption


class LensTypeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = LensTypeOption


class LightingOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = LightingOption


class LightingTypeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = LightingTypeOption


class CameraTypeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = CameraTypeOption


class ResolutionOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = ResolutionOption


class FrameRateOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = FrameRateOption


class MovieOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = MovieOption
        fields = ['id', 'value', 'slug', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ActorOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = ActorOption


class CameraOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = CameraOption


class LensOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = LensOption


class LocationOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = LocationOption


class SettingOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = SettingOption


class FilmStockOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = FilmStockOption


class ShotTimeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = ShotTimeOption


class DescriptionOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = DescriptionOption


class VfxBackingOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = VfxBackingOption


class DirectorOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = DirectorOption
        fields = ['id', 'value', 'slug', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CinematographerOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = CinematographerOption
        fields = ['id', 'value', 'slug', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EditorOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = EditorOption
        fields = ['id', 'value', 'slug', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ColoristOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = ColoristOption
        fields = ['id', 'value', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CostumeDesignerOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = CostumeDesignerOption
        fields = ['id', 'value', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductionDesignerOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = ProductionDesignerOption
        fields = ['id', 'value', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ShadeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = ShadeOption
        fields = ['id', 'value', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ArtistOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = ArtistOption
        fields = ['id', 'value', 'slug', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class FilmingLocationOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = FilmingLocationOption
        fields = ['id', 'value', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class LocationTypeOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = LocationTypeOption
        fields = ['id', 'value', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class YearOptionSerializer(BaseOptionSerializer):
    class Meta(BaseOptionSerializer.Meta):
        model = YearOption
        fields = ['id', 'value', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# Alias for backward compatibility (if needed in views)
OptionSerializer = GenreOptionSerializer


# --------------------------------------------------------------------------- #
#  SIMPLE SERIALIZERS
# --------------------------------------------------------------------------- #
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'slug', 'name']
        read_only_fields = ['slug']


class MovieSerializer(serializers.ModelSerializer):
    director_value = serializers.CharField(source='director.value', read_only=True)
    director_slug = serializers.CharField(source='director.slug', read_only=True)
    cinematographer_value = serializers.CharField(source='cinematographer.value', read_only=True)
    cinematographer_slug = serializers.CharField(source='cinematographer.slug', read_only=True)
    editor_value = serializers.CharField(source='editor.value', read_only=True)
    editor_slug = serializers.CharField(source='editor.slug', read_only=True)
    colorist_value = serializers.CharField(source='colorist', read_only=True)
    costume_designer_value = serializers.CharField(source='costume_designer', read_only=True)
    production_designer_value = serializers.CharField(source='production_designer', read_only=True)

    class Meta:
        model = Movie
        fields = [
            'id', 'slug', 'title', 'description', 'year', 'genre',
            'director', 'director_value', 'director_slug',
            'cinematographer', 'cinematographer_value', 'cinematographer_slug',
            'editor', 'editor_value', 'editor_slug',
            'colorist', 'colorist_value',
            'costume_designer', 'costume_designer_value',
            'production_designer', 'production_designer_value',
            'cast', 'duration', 'country', 'language', 'image_count'
        ]
        read_only_fields = ['id', 'slug', 'image_count']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for f in [
            'director_value', 'director_slug', 'cinematographer_value', 'cinematographer_slug',
            'editor_value', 'editor_slug', 'colorist_value',
            'costume_designer_value', 'production_designer_value'
        ]:
            rep.setdefault(f, "")
        for f in ['description', 'genre', 'cast', 'country', 'language']:
            rep.setdefault(f, "")
        return rep


class HealthSerializer(serializers.Serializer):
    """Explicit serializer for HealthCheckView – silences the drf-spectacular warning."""
    status = serializers.CharField()
    database = serializers.CharField()
    image_count = serializers.IntegerField()
    timestamp = serializers.DateTimeField()


class FilterResponseSerializer(serializers.Serializer):
    """Explicit serializer for FiltersView – silences the drf-spectacular warning."""
    success = serializers.BooleanField(required=False)
    count = serializers.IntegerField(required=False)
    results = serializers.ListField(child=serializers.DictField(), required=False)
    message = serializers.CharField(required=False)


# --------------------------------------------------------------------------- #
#  IMAGE SERIALIZERS (now safe to reference GenreOptionSerializer)
# --------------------------------------------------------------------------- #
class ImageListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)

    # ---- value fields ------------------------------------------------------ #
    media_type_value = serializers.SerializerMethodField()
    color_value = serializers.SerializerMethodField()
    movie_value = serializers.CharField(source='movie.title', read_only=True)
    movie_slug = serializers.CharField(source='movie.slug', read_only=True)

    actor_value = serializers.CharField(source='actor.value', read_only=True, allow_null=True)
    camera_value = serializers.CharField(source='camera.value', read_only=True, allow_null=True)
    cinematographer_value = serializers.CharField(source='cinematographer.value', read_only=True, allow_null=True)
    director_value = serializers.CharField(source='director.value', read_only=True, allow_null=True)
    lens_value = serializers.CharField(source='lens.value', read_only=True, allow_null=True)
    film_stock_value = serializers.CharField(source='film_stock.value', read_only=True, allow_null=True)
    setting_value = serializers.CharField(source='setting.value', read_only=True, allow_null=True)
    location_value = serializers.CharField(source='location.value', read_only=True, allow_null=True)
    filming_location_value = serializers.CharField(source='filming_location.value', read_only=True, allow_null=True)
    aspect_ratio_value = serializers.CharField(source='aspect_ratio.value', read_only=True, allow_null=True)
    time_period_value = serializers.CharField(source='time_period.value', read_only=True, allow_null=True)
    time_of_day_value = serializers.CharField(source='time_of_day.value', read_only=True, allow_null=True)
    interior_exterior_value = serializers.CharField(source='interior_exterior.value', read_only=True, allow_null=True)
    frame_size_value = serializers.CharField(source='frame_size.value', read_only=True, allow_null=True)
    shot_type_value = serializers.CharField(source='shot_type.value', read_only=True, allow_null=True)
    composition_value = serializers.CharField(source='composition.value', read_only=True, allow_null=True)
    lens_type_value = serializers.CharField(source='lens_type.value', read_only=True, allow_null=True)
    lighting_value = serializers.CharField(source='lighting.value', read_only=True, allow_null=True)
    lighting_type_value = serializers.CharField(source='lighting_type.value', read_only=True, allow_null=True)
    shade_value = serializers.CharField(source='shade.value', read_only=True, allow_null=True)
    artist_value = serializers.CharField(source='artist.value', read_only=True, allow_null=True)
    location_type_value = serializers.CharField(source='location_type.value', read_only=True, allow_null=True)

    class Meta:
        model = Image
        fields = [
            'slug', 'title', 'image_url', 'id' ,                    # ← UUID
            'tags', 'release_year', 'media_type', 'media_type_value',
            'color', 'color_value', 'movie', 'movie_value', 'movie_slug',
            'actor', 'actor_value', 'camera', 'camera_value',
            'cinematographer', 'cinematographer_value',
            'director', 'director_value', 'lens', 'lens_value',
            'film_stock', 'film_stock_value', 'setting', 'setting_value',
            'location', 'location_value', 'filming_location', 'filming_location_value',
            'aspect_ratio', 'aspect_ratio_value', 'time_period', 'time_period_value',
            'time_of_day', 'time_of_day_value', 'interior_exterior', 'interior_exterior_value',
            'frame_size', 'frame_size_value', 'shot_type', 'shot_type_value',
            'composition', 'composition_value', 'lens_type', 'lens_type_value',
            'lighting', 'lighting_value', 'lighting_type', 'lighting_type_value',
            'shade', 'shade_value', 'artist', 'artist_value',
            'location_type', 'location_type_value',
            'created_at', 'updated_at'
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_media_type_value(self, obj):
        return obj.media_type.value if obj.media_type else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_color_value(self, obj):
        return obj.color.value if obj.color else None

    # ------------------------------------------------------------------- #
    #  Full URL + file-existence helper
    # ------------------------------------------------------------------- #
    def _absolute_image_url(self, rel_url):
        request = self.context.get('request')
        if request:
            try:
                return request.build_absolute_uri(rel_url)
            except Exception:
                return f"{request.scheme}://{request.get_host()}{rel_url}"

        public = getattr(settings, 'PUBLIC_BASE_URL', None)
        if public:
            return f"{public.rstrip('/')}{rel_url}"
        return f"http://localhost:51009{rel_url}"

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        if instance.image_url and instance.image_url.startswith('/media/'):
            full = self._absolute_image_url(instance.image_url)

            # check existence
            import os
            file_path = safe_join(settings.MEDIA_ROOT, instance.image_url.lstrip('/'))
            rep['image_available'] = os.path.exists(file_path)
            rep['image_url'] = full
        return rep


class MovieImageSerializer(serializers.ModelSerializer):
    """Very lightweight – used when listing images per movie."""
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    movie_slug = serializers.CharField(source='movie.slug', read_only=True)
    color_value = serializers.CharField(source='color.value', read_only=True, allow_null=True)
    media_type_value = serializers.CharField(source='media_type.value', read_only=True, allow_null=True)
    tags_count = serializers.SerializerMethodField()
    genre_count = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = [
            'id', 'slug', 'title', 'description', 'image_url',   # ← UUID
            'movie_title', 'movie_slug', 'color_value', 'media_type_value',
            'tags_count', 'genre_count', 'release_year',
            'dominant_colors', 'primary_color_hex', 'created_at'
        ]

    def get_tags_count(self, obj):
        return obj.tags.count()

    def get_genre_count(self, obj):
        return obj.genre.count()

    def to_representation(self, instance):
        rep = {
            'id': instance.uuid,
            'slug': instance.slug,
            'title': instance.title,
            'description': instance.description,
            'movie_title': instance.movie.title if instance.movie else None,
            'movie_slug': instance.movie.slug if instance.movie else None,
            'color_value': instance.color.value if instance.color else None,
            'media_type_value': instance.media_type.value if instance.media_type else None,
            'tags_count': instance.tags.count(),
            'genre_count': instance.genre.count(),
            'release_year': instance.release_year,
            'dominant_colors': instance.dominant_colors,
            'primary_color_hex': instance.primary_color_hex,
            'created_at': instance.created_at
        }

        if instance.image_url:
            if instance.image_url.startswith('/media/'):
                request = self.context.get('request')
                if request:
                    try:
                        rep['image_url'] = request.build_absolute_uri(instance.image_url)
                    except Exception:
                        rep['image_url'] = f"{request.scheme}://{request.get_host()}{instance.image_url}"
                else:
                    public = getattr(settings, 'PUBLIC_BASE_URL', None)
                    if public:
                        rep['image_url'] = f"{public.rstrip('/')}{instance.image_url}"
                    else:
                        rep['image_url'] = f"http://localhost:51009{instance.image_url}"
            else:
                rep['image_url'] = instance.image_url
        return rep


class ImageSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), source='tags', many=True, write_only=True, required=False
    )
    genre = GenreOptionSerializer(many=True, read_only=True)

    # ---- value fields ------------------------------------------------------ #
    media_type_value = serializers.SerializerMethodField()
    color_value = serializers.SerializerMethodField()
    frame_size_value = serializers.SerializerMethodField()
    shot_type_value = serializers.SerializerMethodField()
    lighting_value = serializers.SerializerMethodField()

    aspect_ratio_value = serializers.CharField(source='aspect_ratio.value', read_only=True, allow_null=True)
    optical_format_value = serializers.CharField(source='optical_format.value', read_only=True, allow_null=True)
    format_value = serializers.CharField(source='format.value', read_only=True, allow_null=True)
    interior_exterior_value = serializers.CharField(source='interior_exterior.value', read_only=True, allow_null=True)
    time_of_day_value = serializers.CharField(source='time_of_day.value', read_only=True, allow_null=True)
    composition_value = serializers.CharField(source='composition.value', read_only=True, allow_null=True)
    lens_type_value = serializers.CharField(source='lens_type.value', read_only=True, allow_null=True)
    lighting_type_value = serializers.CharField(source='lighting_type.value', read_only=True, allow_null=True)
    time_period_value = serializers.CharField(source='time_period.value', read_only=True, allow_null=True)

    movie_value = serializers.CharField(source='movie.title', read_only=True)
    movie_slug = serializers.CharField(source='movie.slug', read_only=True)
    actor_value = serializers.CharField(source='actor.value', read_only=True, allow_null=True)
    camera_value = serializers.CharField(source='camera.value', read_only=True, allow_null=True)
    lens_value = serializers.CharField(source='lens.value', read_only=True, allow_null=True)
    location_value = serializers.CharField(source='location.value', read_only=True, allow_null=True)
    setting_value = serializers.CharField(source='setting.value', read_only=True, allow_null=True)
    film_stock_value = serializers.CharField(source='film_stock.value', read_only=True, allow_null=True)
    vfx_backing_value = serializers.CharField(source='vfx_backing.value', read_only=True, allow_null=True)

    director_value = serializers.CharField(source='director.value', read_only=True, allow_null=True)
    cinematographer_value = serializers.CharField(source='cinematographer.value', read_only=True, allow_null=True)
    editor_value = serializers.CharField(source='editor.value', read_only=True, allow_null=True)
    colorist_value = serializers.CharField(source='colorist.value', read_only=True, allow_null=True)
    costume_designer_value = serializers.CharField(source='costume_designer.value', read_only=True, allow_null=True)
    production_designer_value = serializers.CharField(source='production_designer.value', read_only=True, allow_null=True)
    shade_value = serializers.CharField(source='shade.value', read_only=True, allow_null=True)
    artist_value = serializers.CharField(source='artist.value', read_only=True, allow_null=True)
    filming_location_value = serializers.CharField(source='filming_location.value', read_only=True, allow_null=True)
    location_type_value = serializers.CharField(source='location_type.value', read_only=True, allow_null=True)

    class Meta:
        model = Image
        fields = [
            'uuid', 'slug', 'title', 'image_url',                     # ← UUID
            'tags', 'tag_ids',
            'release_year', 'media_type', 'media_type_value', 'genre',
            'color', 'color_value', 'aspect_ratio', 'aspect_ratio_value',
            'optical_format', 'optical_format_value', 'format', 'format_value',
            'interior_exterior', 'interior_exterior_value', 'time_of_day', 'time_of_day_value',
            'frame_size', 'frame_size_value', 'shot_type', 'shot_type_value',
            'composition', 'composition_value', 'lens_type', 'lens_type_value',
            'lighting', 'lighting_value', 'lighting_type', 'lighting_type_value',
            'time_period', 'time_period_value',
            'movie', 'movie_value', 'movie_slug',
            'director', 'director_value', 'cinematographer', 'cinematographer_value',
            'editor', 'editor_value', 'colorist', 'colorist_value',
            'costume_designer', 'costume_designer_value', 'production_designer', 'production_designer_value',
            'actor', 'actor_value', 'camera', 'camera_value', 'lens', 'lens_value',
            'location', 'location_value', 'setting', 'setting_value',
            'film_stock', 'film_stock_value', 'vfx_backing', 'vfx_backing_value',
            'shade', 'shade_value', 'artist', 'artist_value',
            'filming_location', 'filming_location_value', 'location_type', 'location_type_value',
            'exclude_nudity', 'exclude_violence',
            'dominant_colors', 'primary_color_hex', 'primary_colors', 'secondary_color_hex',
            'color_palette', 'color_samples', 'color_histogram', 'color_search_terms',
            'color_temperature', 'hue_range',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'slug', 'created_at', 'updated_at']

    # ------------------------------------------------------------------- #
    #  SerializerMethodFields
    # ------------------------------------------------------------------- #
    @extend_schema_field(OpenApiTypes.STR)
    def get_media_type_value(self, obj):
        return obj.media_type.value if obj.media_type else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_color_value(self, obj):
        return obj.color.value if obj.color else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_frame_size_value(self, obj):
        return obj.frame_size.value if obj.frame_size else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_shot_type_value(self, obj):
        return obj.shot_type.value if obj.shot_type else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_lighting_value(self, obj):
        return obj.lighting.value if obj.lighting else None

    # ------------------------------------------------------------------- #
    #  Full URL + file-existence helper (same as ImageListSerializer)
    # ------------------------------------------------------------------- #
    def _absolute_image_url(self, rel_url):
        request = self.context.get('request')
        if request:
            try:
                return request.build_absolute_uri(rel_url)
            except Exception:
                return f"{request.scheme}://{request.get_host()}{rel_url}"
        public = getattr(settings, 'PUBLIC_BASE_URL', None)
        if public:
            return f"{public.rstrip('/')}{rel_url}"
        return f"http://localhost:51009{rel_url}"

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        # ----- image URL handling ------------------------------------------ #
        if instance.image_url:
            if instance.image_url.startswith('/media/'):
                full = self._absolute_image_url(instance.image_url)
                import os
                file_path = safe_join(settings.MEDIA_ROOT, instance.image_url.lstrip('/'))
                rep['image_available'] = os.path.exists(file_path)
                rep['image_url'] = full
            elif 'localhost:' in instance.image_url:
                # fix old localhost URLs that may still be stored
                path = instance.image_url.split('/media/', 1)[-1] if '/media/' in instance.image_url else None
                if path:
                    rep['image_url'] = self._absolute_image_url(f"/media/{path}")

        # ----- sane defaults for empty collections / nulls ---------------- #
        for f in [
            'media_type_value', 'color_value', 'aspect_ratio_value',
            'optical_format_value', 'format_value', 'interior_exterior_value',
            'time_of_day_value', 'frame_size_value', 'shot_type_value',
            'composition_value', 'lens_type_value', 'lighting_value',
            'lighting_type_value', 'time_period_value',
            'movie_value', 'actor_value', 'camera_value', 'lens_value',
            'location_value', 'setting_value', 'film_stock_value',
            'vfx_backing_value', 'director_value', 'cinematographer_value',
            'editor_value', 'colorist_value', 'costume_designer_value',
            'production_designer_value', 'shade_value', 'artist_value',
            'filming_location_value', 'location_type_value'
        ]:
            if rep.get(f) is None and f not in ['movie_value', 'director_value',
                                                'cinematographer_value', 'editor_value']:
                rep[f] = ""

        rep.setdefault('tags', [])
        rep.setdefault('genre', [])

        for f in [
            'dominant_colors', 'primary_colors', 'color_palette',
            'color_samples', 'color_histogram', 'color_search_terms'
        ]:
            rep.setdefault(f, [])
        for f in [
            'primary_color_hex', 'secondary_color_hex',
            'color_temperature', 'hue_range'
        ]:
            rep.setdefault(f, "")

        rep.setdefault('description', "")
        if rep.get('release_year') is None:
            rep['release_year'] = None

        return rep

    # ------------------------------------------------------------------- #
    #  Messaging on create / update
    # ------------------------------------------------------------------- #
    def create(self, validated_data):
        instance = super().create(validated_data)
        send_event('image_created', self.to_representation(instance))
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        send_event('image_updated', self.to_representation(instance))
        return instance