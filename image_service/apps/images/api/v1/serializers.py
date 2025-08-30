from rest_framework import serializers
from apps.images.models import Image, Movie, Tag

# --- تغییر کلیدی: ایمپورت از پکیج جدید messaging ---
from messaging.producers import send_event

class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ['id', 'title', 'year']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class ImageSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    movie_id = serializers.PrimaryKeyRelatedField(
        queryset=Movie.objects.all(), source='movie', write_only=True, required=False, allow_null=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), source='tags', many=True, write_only=True, required=False
    )

    class Meta:
        model = Image
        fields = [
            'id', 'title', 'description', 'image_url', 
            'movie', 'tags', 'movie_id', 'tag_ids', 
            'release_year', 'media_type', 'genre', 'color', 'aspect_ratio', 
            'optical_format', 'format', 'interior_exterior', 'time_of_day', 
            'number_of_people', 'gender', 'age', 'ethnicity', 'frame_size', 
            'shot_type', 'composition', 'lens_size', 'lens_type', 'lighting', 
            'lighting_type', 'camera_type', 'resolution', 'frame_rate', 
            'exclude_nudity', 'exclude_violence', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.movie:
            representation['movie'] = MovieSerializer(instance.movie).data
        representation['tags'] = TagSerializer(instance.tags.all(), many=True).data
        return representation

    def create(self, validated_data):
        instance = super().create(validated_data)
        send_event('image_created', self.to_representation(instance))
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        send_event('image_updated', self.to_representation(instance))
        return instance