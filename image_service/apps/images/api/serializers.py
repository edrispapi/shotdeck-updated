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
    DirectorOption, CinematographerOption, EditorOption,
    ColoristOption, CostumeDesignerOption, ProductionDesignerOption,
    # New models
    ShadeOption, ArtistOption, FilmingLocationOption, LocationTypeOption, YearOption
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
        representation = super().to_representation(instance)

        # Handle null values for nested fields - convert null to empty strings
        nested_value_fields = [
            'director_value', 'director_slug', 'cinematographer_value', 'cinematographer_slug',
            'editor_value', 'editor_slug', 'colorist_value',
            'costume_designer_value', 'production_designer_value'
        ]

        for field in nested_value_fields:
            if representation.get(field) is None:
                representation[field] = ""

        # Handle other potentially null fields
        text_fields = ['description', 'genre', 'cast', 'country', 'language']
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
    Comprehensive serializer for list views - includes all filter fields
    """
    tags = TagSerializer(many=True, read_only=True)

    # All filter value fields
    media_type_value = serializers.SerializerMethodField()
    color_value = serializers.SerializerMethodField()
    movie_value = serializers.CharField(source='movie.title', read_only=True)
    movie_slug = serializers.CharField(source='movie.slug', read_only=True)
    
    # All the missing fields
    actor_value = serializers.CharField(source='actor.value', read_only=True)
    camera_value = serializers.CharField(source='camera.value', read_only=True)
    cinematographer_value = serializers.CharField(source='cinematographer.value', read_only=True)
    director_value = serializers.CharField(source='director.value', read_only=True)
    lens_value = serializers.CharField(source='lens.value', read_only=True)
    film_stock_value = serializers.CharField(source='film_stock.value', read_only=True)
    setting_value = serializers.CharField(source='setting.value', read_only=True)
    location_value = serializers.CharField(source='location.value', read_only=True)
    filming_location_value = serializers.CharField(source='filming_location.value', read_only=True)
    aspect_ratio_value = serializers.CharField(source='aspect_ratio.value', read_only=True)
    time_period_value = serializers.CharField(source='time_period.value', read_only=True)
    time_of_day_value = serializers.CharField(source='time_of_day.value', read_only=True)
    interior_exterior_value = serializers.CharField(source='interior_exterior.value', read_only=True)
    frame_size_value = serializers.CharField(source='frame_size.value', read_only=True)
    shot_type_value = serializers.CharField(source='shot_type.value', read_only=True)
    composition_value = serializers.CharField(source='composition.value', read_only=True)
    lens_type_value = serializers.CharField(source='lens_type.value', read_only=True)
    lighting_value = serializers.CharField(source='lighting.value', read_only=True)
    lighting_type_value = serializers.CharField(source='lighting_type.value', read_only=True)
    shade_value = serializers.CharField(source='shade.value', read_only=True)
    artist_value = serializers.CharField(source='artist.value', read_only=True)
    location_type_value = serializers.CharField(source='location_type.value', read_only=True)

    class Meta:
        model = Image
        fields = [
            'id', 'slug', 'title', 'image_url',
            'tags', 'release_year', 'media_type', 'media_type_value',
            'color', 'color_value', 'movie', 'movie_value', 'movie_slug',
            # All the missing fields
            'actor', 'actor_value', 'camera', 'camera_value', 'cinematographer', 'cinematographer_value',
            'director', 'director_value', 'lens', 'lens_value', 'film_stock', 'film_stock_value',
            'setting', 'setting_value', 'location', 'location_value', 'filming_location', 'filming_location_value',
            'aspect_ratio', 'aspect_ratio_value', 'time_period', 'time_period_value',
            'time_of_day', 'time_of_day_value', 'interior_exterior', 'interior_exterior_value',
            'frame_size', 'frame_size_value', 'shot_type', 'shot_type_value', 'composition', 'composition_value',
            'lens_type', 'lens_type_value', 'lighting', 'lighting_value', 'lighting_type', 'lighting_type_value',
            'shade', 'shade_value', 'artist', 'artist_value', 'location_type', 'location_type_value',
            'created_at', 'updated_at'
        ]

    def get_media_type_value(self, obj):
        return obj.media_type.value if obj.media_type else None

    def get_color_value(self, obj):
        return obj.color.value if obj.color else None

    def to_representation(self, instance):
        """Convert relative image URLs to full URLs for clickable links"""
        representation = super().to_representation(instance)

        # Handle image URL conversion
        if instance.image_url and instance.image_url.startswith('/media/'):
            request = self.context.get('request')
            if request:
                try:
                    full_url = request.build_absolute_uri(instance.image_url)
                except Exception:
                    full_url = f"{request.scheme}://{request.get_host()}{instance.image_url}"
            else:
                # Fallbacks when request is unavailable
                public_base = getattr(settings, 'PUBLIC_BASE_URL', None)
                if public_base:
                    full_url = f"{public_base.rstrip('/')}{instance.image_url}"
                else:
                    # Final fallback to localhost with image_service port
                    full_url = f"http://localhost:51009{instance.image_url}"

            # Check if the image file actually exists
            import os
            from django.conf import settings
            media_root = getattr(settings, 'MEDIA_ROOT', '/app/media')
            relative_path = instance.image_url.replace('/media/', '')
            file_path = os.path.join(media_root, relative_path)

            if os.path.exists(file_path):
                representation['image_url'] = full_url
                representation['image_available'] = True
            else:
                representation['image_url'] = full_url
                representation['image_available'] = False

        return representation


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
                    try:
                        full_url = request.build_absolute_uri(instance.image_url)
                    except Exception:
                        full_url = f"{request.scheme}://{request.get_host()}{instance.image_url}"
                    representation['image_url'] = full_url
                else:
                    public_base = getattr(settings, 'PUBLIC_BASE_URL', None)
                    if public_base:
                        representation['image_url'] = f"{public_base.rstrip('/')}{instance.image_url}"
                    else:
                        # Use the correct port for the image service (51009)
                        representation['image_url'] = f"http://localhost:51009{instance.image_url}"
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
    # genre_value removed - Image model has ManyToMany genre field, not on movie
    aspect_ratio_value = serializers.CharField(source='aspect_ratio.value', read_only=True)
    optical_format_value = serializers.CharField(source='optical_format.value', read_only=True)
    format_value = serializers.CharField(source='format.value', read_only=True)
    interior_exterior_value = serializers.CharField(source='interior_exterior.value', read_only=True)
    time_of_day_value = serializers.CharField(source='time_of_day.value', read_only=True)
    composition_value = serializers.CharField(source='composition.value', read_only=True)
    lens_type_value = serializers.CharField(source='lens_type.value', read_only=True)
    lighting_type_value = serializers.CharField(source='lighting_type.value', read_only=True)
    time_period_value = serializers.CharField(source='time_period.value', read_only=True)

    # New filter value fields
    movie_value = serializers.CharField(source='movie.title', read_only=True)
    movie_slug = serializers.CharField(source='movie.slug', read_only=True)
    actor_value = serializers.CharField(source='actor.value', read_only=True)
    camera_value = serializers.CharField(source='camera.value', read_only=True)
    lens_value = serializers.CharField(source='lens.value', read_only=True)
    location_value = serializers.CharField(source='location.value', read_only=True)
    setting_value = serializers.CharField(source='setting.value', read_only=True)
    film_stock_value = serializers.CharField(source='film_stock.value', read_only=True)
    vfx_backing_value = serializers.CharField(source='vfx_backing.value', read_only=True)

    # Additional filter value fields for complete dataset
    director_value = serializers.CharField(source='director.value', read_only=True)
    cinematographer_value = serializers.CharField(source='cinematographer.value', read_only=True)
    editor_value = serializers.CharField(source='editor.value', read_only=True)
    colorist_value = serializers.CharField(source='colorist.value', read_only=True)
    costume_designer_value = serializers.CharField(source='costume_designer.value', read_only=True)
    production_designer_value = serializers.CharField(source='production_designer.value', read_only=True)
    shade_value = serializers.CharField(source='shade.value', read_only=True)
    artist_value = serializers.CharField(source='artist.value', read_only=True)
    filming_location_value = serializers.CharField(source='filming_location.value', read_only=True)
    location_type_value = serializers.CharField(source='location_type.value', read_only=True)

    class Meta:
        model = Image
        fields = [
            'id', 'slug', 'title', 'image_url',
            'tags', 'tag_ids',
            'release_year', 'media_type', 'media_type_value', 'genre',
            'color', 'color_value', 'aspect_ratio', 'aspect_ratio_value',
            'optical_format', 'optical_format_value', 'format', 'format_value',
            'interior_exterior', 'interior_exterior_value', 'time_of_day', 'time_of_day_value',
            'frame_size', 'frame_size_value', 'shot_type', 'shot_type_value', 'composition', 'composition_value',
            'lens_type', 'lens_type_value', 'lighting', 'lighting_value', 'lighting_type', 'lighting_type_value',
            'time_period', 'time_period_value',
            # Movie and crew fields
            'movie', 'movie_value', 'movie_slug',
            'director', 'director_value', 'cinematographer', 'cinematographer_value',
            'editor', 'editor_value', 'colorist', 'colorist_value',
            'costume_designer', 'costume_designer_value', 'production_designer', 'production_designer_value',
            # Actor and technical fields
            'actor', 'actor_value', 'camera', 'camera_value', 'lens', 'lens_value',
            'location', 'location_value', 'setting', 'setting_value',
            'film_stock', 'film_stock_value', 'vfx_backing', 'vfx_backing_value',
            # New filter fields
            'shade', 'shade_value', 'artist', 'artist_value',
            'filming_location', 'filming_location_value', 'location_type', 'location_type_value',
            # Additional flags
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
        # Temporarily disable tag serialization for debugging
        # representation['tags'] = TagSerializer(instance.tags.all(), many=True).data

        # Fix image URL to use proper host and port
        if instance.image_url:
            # If it's a relative URL (starts with /media/), construct full URL
            if instance.image_url.startswith('/media/'):
                request = self.context.get('request')
                if request:
                    try:
                        full_url = request.build_absolute_uri(instance.image_url)
                    except Exception:
                        base_url = f"{request.scheme}://{request.get_host()}"
                        full_url = f"{base_url}{instance.image_url}"
                else:
                    public_base = getattr(settings, 'PUBLIC_BASE_URL', None)
                    if public_base:
                        full_url = f"{public_base.rstrip('/')}{instance.image_url}"
                    else:
                        # Last fallback - use localhost and correct port
                        full_url = f"http://localhost:51009{instance.image_url}"

                # Check if the image file actually exists
                import os
                from django.conf import settings
                media_root = getattr(settings, 'MEDIA_ROOT', '/app/media')
                relative_path = instance.image_url.replace('/media/', '')
                file_path = os.path.join(media_root, relative_path)

                if os.path.exists(file_path):
                    representation['image_url'] = full_url
                    representation['image_available'] = True
                else:
                    representation['image_url'] = full_url
                    representation['image_available'] = False
            # If it's already an absolute URL but with wrong host/port, try to fix it
            elif 'localhost:' in instance.image_url:
                request = self.context.get('request')
                path_part = None
                if '/media/' in instance.image_url:
                    try:
                        path_part = instance.image_url.split('/media/', 1)[1]
                    except Exception:
                        path_part = None
                if request and path_part:
                    try:
                        representation['image_url'] = request.build_absolute_uri(f"/media/{path_part}")
                    except Exception:
                        base_url = f"{request.scheme}://{request.get_host()}"
                        representation['image_url'] = f"{base_url}/media/{path_part}"
                elif path_part:
                    public_base = getattr(settings, 'PUBLIC_BASE_URL', None)
                    if public_base:
                        representation['image_url'] = f"{public_base.rstrip('/')}/media/{path_part}"
                    else:
                        representation['image_url'] = f"http://localhost:51009/media/{path_part}"

        # Handle null/empty values for filter fields - provide meaningful defaults or remove empty fields
        # Only process fields that are actually in the response and have meaningful data
        filter_value_fields = [
            'media_type_value', 'color_value', 'aspect_ratio_value',
            'optical_format_value', 'format_value', 'interior_exterior_value', 'time_of_day_value',
            'frame_size_value', 'shot_type_value', 'composition_value',
            'lens_type_value', 'lighting_value', 'lighting_type_value',
            'time_period_value',
            'movie_value', 'actor_value', 'camera_value', 'lens_value', 'location_value',
            'setting_value', 'film_stock_value', 'vfx_backing_value', 'director_value', 'cinematographer_value', 'editor_value',
            'colorist_value', 'costume_designer_value', 'production_designer_value',
            'shade_value', 'artist_value', 'filming_location_value', 'location_type_value'
        ]

        # Keep null values as null instead of converting to empty strings
        # Only convert specific fields that should have defaults
        nullable_fields = ['movie_value', 'director_value', 'cinematographer_value', 'editor_value']
        for field in filter_value_fields:
            if field not in nullable_fields and representation.get(field) is None:
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