from rest_framework import serializers
from django.conf import settings
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
    DirectorOption, CinematographerOption, EditorOption
)
from messaging.producers import send_event


class MovieSerializer(serializers.ModelSerializer):
    # Nested serializers for option fields with slugs
    director_value = serializers.CharField(source='director.value', read_only=True)
    director_slug = serializers.CharField(source='director.slug', read_only=True)
    cinematographer_value = serializers.CharField(source='cinematographer.value', read_only=True)
    cinematographer_slug = serializers.CharField(source='cinematographer.slug', read_only=True)
    editor_value = serializers.CharField(source='editor.value', read_only=True)
    editor_slug = serializers.CharField(source='editor.slug', read_only=True)

    class Meta:
        model = Movie
        fields = [
            'id', 'slug', 'title', 'description', 'year', 'genre',
            'director', 'director_value', 'director_slug',
            'cinematographer', 'cinematographer_value', 'cinematographer_slug',
            'editor', 'editor_value', 'editor_slug',
            'cast', 'colorist', 'production_designer', 'costume_designer',
            'duration', 'country', 'language', 'image_count'
        ]
        read_only_fields = ['id', 'slug', 'image_count']

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Handle null values for nested fields - convert null to empty strings
        nested_value_fields = [
            'director_value', 'director_slug', 'cinematographer_value', 'cinematographer_slug',
            'editor_value', 'editor_slug'
        ]

        for field in nested_value_fields:
            if representation.get(field) is None:
                representation[field] = ""

        # Handle other potentially null fields
        text_fields = ['description', 'genre', 'cast', 'colorist', 'production_designer', 'costume_designer', 'country', 'language']
        for field in text_fields:
            if representation.get(field) is None:
                representation[field] = ""

        # Keep numeric fields as null if they're None (year, duration, image_count)
        # They should remain null rather than empty strings for proper API semantics

        return representation

class GenreOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenreOption
        fields = ['id', 'value']
        read_only_fields = ['id']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'slug', 'name']
        read_only_fields = ['slug']

class ImageListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views - optimized for performance
    """
    tags = TagSerializer(many=True, read_only=True)

    # Only include the most essential value fields
    media_type_value = serializers.SerializerMethodField()
    color_value = serializers.SerializerMethodField()
    movie_value = serializers.CharField(source='movie.title', read_only=True)
    movie_slug = serializers.CharField(source='movie.slug', read_only=True)

    class Meta:
        model = Image
        fields = [
            'id', 'slug', 'title', 'description', 'image_url',
            'tags', 'release_year', 'media_type', 'media_type_value',
            'color', 'color_value', 'movie', 'movie_value', 'movie_slug',
            'created_at', 'updated_at'
        ]

    def get_media_type_value(self, obj):
        return obj.media_type.value if obj.media_type else None

    def get_color_value(self, obj):
        return obj.color.value if obj.color else None


class MovieImageSerializer(serializers.ModelSerializer):
    """Memory-optimized serializer for movie images - minimal fields, lazy loading"""

    # Only essential fields to reduce memory usage
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    movie_slug = serializers.CharField(source='movie.slug', read_only=True)
    color_value = serializers.CharField(source='color.value', read_only=True)
    media_type_value = serializers.CharField(source='media_type.value', read_only=True)

    # Lazy tag and genre counts instead of full objects
    tags_count = serializers.SerializerMethodField()
    genre_count = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = [
            'id', 'slug', 'title', 'description', 'image_url',
            'movie_title', 'movie_slug', 'color_value', 'media_type_value',
            'tags_count', 'genre_count', 'release_year',
            'dominant_colors', 'primary_color_hex', 'created_at'
        ]

    def get_tags_count(self, obj):
        """Lazy load tag count instead of full objects"""
        return obj.tags.count()

    def get_genre_count(self, obj):
        """Lazy load genre count instead of full objects"""
        return obj.genre.count()

    def to_representation(self, instance):
        """Memory-efficient representation with simple URL handling"""
        representation = {
            'id': instance.id,
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

        # Simple URL handling
        if instance.image_url:
            if instance.image_url.startswith('/media/'):
                request = self.context.get('request')
                if request:
                    representation['image_url'] = f"{request.scheme}://{request.get_host()}{instance.image_url}"
                else:
                    representation['image_url'] = f"http://localhost:9000{instance.image_url}"
            else:
                representation['image_url'] = instance.image_url

        return representation


class ImageSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), source='tags', many=True, write_only=True, required=False)
    genre = GenreOptionSerializer(many=True, read_only=True)

    # Optimized nested serializers for option fields (using select_related)
    media_type_value = serializers.SerializerMethodField()
    color_value = serializers.SerializerMethodField()
    frame_size_value = serializers.SerializerMethodField()
    shot_type_value = serializers.SerializerMethodField()
    lighting_value = serializers.SerializerMethodField()

    # Keep other fields as-is for now (will be lazy-loaded)
    genre_value = serializers.CharField(source='movie.genre', read_only=True)
    aspect_ratio_value = serializers.CharField(source='aspect_ratio.value', read_only=True)
    optical_format_value = serializers.CharField(source='optical_format.value', read_only=True)
    format_value = serializers.CharField(source='format.value', read_only=True)
    interior_exterior_value = serializers.CharField(source='interior_exterior.value', read_only=True)
    time_of_day_value = serializers.CharField(source='time_of_day.value', read_only=True)
    number_of_people_value = serializers.CharField(source='number_of_people.value', read_only=True)
    gender_value = serializers.CharField(source='gender.value', read_only=True)
    age_value = serializers.CharField(source='age.value', read_only=True)
    ethnicity_value = serializers.CharField(source='ethnicity.value', read_only=True)
    composition_value = serializers.CharField(source='composition.value', read_only=True)
    lens_size_value = serializers.CharField(source='lens_size.value', read_only=True)
    lens_type_value = serializers.CharField(source='lens_type.value', read_only=True)
    lighting_type_value = serializers.CharField(source='lighting_type.value', read_only=True)
    camera_type_value = serializers.CharField(source='camera_type.value', read_only=True)
    resolution_value = serializers.CharField(source='resolution.value', read_only=True)
    frame_rate_value = serializers.CharField(source='frame_rate.value', read_only=True)
    time_period_value = serializers.CharField(source='time_period.value', read_only=True)
    lab_process_value = serializers.CharField(source='lab_process.value', read_only=True)

    # New filter value fields
    movie_value = serializers.CharField(source='movie.title', read_only=True)
    movie_slug = serializers.CharField(source='movie.slug', read_only=True)
    actor_value = serializers.CharField(source='actor.value', read_only=True)
    camera_value = serializers.CharField(source='camera.value', read_only=True)
    lens_value = serializers.CharField(source='lens.value', read_only=True)
    location_value = serializers.CharField(source='location.value', read_only=True)
    setting_value = serializers.CharField(source='setting.value', read_only=True)
    film_stock_value = serializers.CharField(source='film_stock.value', read_only=True)
    shot_time_value = serializers.CharField(source='shot_time.value', read_only=True)
    description_filter_value = serializers.CharField(source='description_filter.value', read_only=True)
    vfx_backing_value = serializers.CharField(source='vfx_backing.value', read_only=True)

    class Meta:
        model = Image
        fields = [
            'id', 'slug', 'title', 'description', 'image_url',
            'tags', 'tag_ids',
            'release_year', 'media_type', 'media_type_value', 'genre', 'genre_value',
            'color', 'color_value', 'aspect_ratio', 'aspect_ratio_value',
            'optical_format', 'optical_format_value', 'format', 'format_value',
            'interior_exterior', 'interior_exterior_value', 'time_of_day', 'time_of_day_value',
            'number_of_people', 'number_of_people_value', 'gender', 'gender_value',
            'age', 'age_value', 'ethnicity', 'ethnicity_value', 'frame_size', 'frame_size_value',
            'shot_type', 'shot_type_value', 'composition', 'composition_value',
            'lens_size', 'lens_size_value', 'lens_type', 'lens_type_value',
            'lighting', 'lighting_value', 'lighting_type', 'lighting_type_value',
            'camera_type', 'camera_type_value', 'resolution', 'resolution_value',
            'frame_rate', 'frame_rate_value', 'time_period', 'time_period_value',
            'lab_process', 'lab_process_value',
            # New filter fields
            'movie', 'movie_value', 'movie_slug', 'actor', 'actor_value', 'camera', 'camera_value', 'lens', 'lens_value',
            'location', 'location_value', 'setting', 'setting_value',
            'film_stock', 'film_stock_value', 'shot_time', 'shot_time_value',
            'description_filter', 'description_filter_value', 'vfx_backing', 'vfx_backing_value',
            'exclude_nudity', 'exclude_violence',
            # Enhanced color analysis fields
            'dominant_colors', 'primary_color_hex', 'primary_colors', 'secondary_color_hex',
            'color_palette', 'color_samples', 'color_histogram', 'color_search_terms',
            'color_temperature', 'hue_range',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_media_type_value(self, obj):
        return obj.media_type.value if obj.media_type else None

    def get_color_value(self, obj):
        return obj.color.value if obj.color else None

    def get_frame_size_value(self, obj):
        return obj.frame_size.value if obj.frame_size else None

    def get_shot_type_value(self, obj):
        return obj.shot_type.value if obj.shot_type else None

    def get_lighting_value(self, obj):
        return obj.lighting.value if obj.lighting else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(instance.tags.all(), many=True).data

        # Fix image URL to use proper host and port
        if instance.image_url:
            # If it's a relative URL (starts with /media/), construct full URL
            if instance.image_url.startswith('/media/'):
                request = self.context.get('request')
                if request:
                    base_url = f"{request.scheme}://{request.get_host()}"
                    representation['image_url'] = f"{base_url}{instance.image_url}"
                else:
                    # Fallback - try to construct URL with localhost and correct port
                    import os
                    try:
                        # Try to get port from environment or use 54634 as default for API server
                        port = os.environ.get('PORT', '54634')
                        representation['image_url'] = f"http://localhost:{port}{instance.image_url}"
                    except:
                        # Last fallback - keep original URL
                        pass
            # If it's already an absolute URL but with wrong host/port, try to fix it
            elif 'localhost:12001' in instance.image_url or 'localhost:' in instance.image_url:
                request = self.context.get('request')
                if request:
                    # Replace the hardcoded host/port with current request's host/port
                    base_url = f"{request.scheme}://{request.get_host()}"
                    path_part = instance.image_url.split('/media/')[1] if '/media/' in instance.image_url else instance.image_url.split('/')[-1]
                    representation['image_url'] = f"{base_url}/media/{path_part}"
                else:
                    # Fallback - replace with correct port
                    import os
                    try:
                        port = os.environ.get('PORT', '54634')
                        path_part = instance.image_url.split('/media/')[1] if '/media/' in instance.image_url else instance.image_url.split('/')[-1]
                        representation['image_url'] = f"http://localhost:{port}/media/{path_part}"
                    except:
                        pass

        # Handle null/empty values for filter fields - provide meaningful defaults or remove empty fields
        filter_value_fields = [
            'media_type_value', 'genre_value', 'color_value', 'aspect_ratio_value',
            'optical_format_value', 'format_value', 'interior_exterior_value', 'time_of_day_value',
            'number_of_people_value', 'gender_value', 'age_value', 'ethnicity_value',
            'frame_size_value', 'shot_type_value', 'composition_value', 'lens_size_value',
            'lens_type_value', 'lighting_value', 'lighting_type_value', 'camera_type_value',
            'resolution_value', 'frame_rate_value', 'time_period_value', 'lab_process_value',
            'movie_value', 'actor_value', 'camera_value', 'lens_value', 'location_value',
            'setting_value', 'film_stock_value', 'shot_time_value', 'description_filter_value',
            'vfx_backing_value'
        ]

        # Set empty strings for null _value fields instead of null
        for field in filter_value_fields:
            if representation.get(field) is None:
                representation[field] = ""

        # Handle empty collections
        if not representation.get('tags'):
            representation['tags'] = []

        # Handle empty genre (ManyToManyField)
        if not representation.get('genre'):
            representation['genre'] = []

        # Handle color analysis fields that might be null
        color_analysis_fields = [
            'dominant_colors', 'primary_color_hex', 'primary_colors', 'secondary_color_hex',
            'color_palette', 'color_samples', 'color_histogram', 'color_search_terms',
            'color_temperature', 'hue_range'
        ]

        for field in color_analysis_fields:
            if representation.get(field) is None:
                if field in ['dominant_colors', 'primary_colors', 'color_palette', 'color_samples', 'color_histogram', 'color_search_terms']:
                    representation[field] = []
                else:
                    representation[field] = ""

        # Handle other potentially null fields
        if representation.get('description') is None:
            representation['description'] = ""

        if representation.get('release_year') is None:
            representation['release_year'] = None  # Keep as null for year fields

        return representation

    def create(self, validated_data):
        instance = super().create(validated_data)
        send_event('image_created', self.to_representation(instance))
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        send_event('image_updated', self.to_representation(instance))
        return instance


# Base serializer for all option models
class BaseOptionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'value', 'display_order', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        model = None  # Will be set by subclasses


# Specific serializers for each filter type
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