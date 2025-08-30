from rest_framework import serializers

# سریالایزر برای نمایش آبجکت تگ در نتایج
class TagDocumentSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)

# سریالایزر برای نمایش آبجکت فیلم در نتایج
class MovieDocumentSerializer(serializers.Serializer):
    title = serializers.CharField(read_only=True)
    year = serializers.IntegerField(read_only=True)

# سریالایزر اصلی برای هر "hit" یا نتیجه جستجو از Elasticsearch
class ImageSearchResultSerializer(serializers.Serializer):
    # فیلدهای meta از Elasticsearch
    _id = serializers.CharField(source='meta.id', read_only=True)
    _score = serializers.FloatField(source='meta.score', read_only=True)

    # فیلدهای اصلی داکیومنت
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    image_url = serializers.URLField(read_only=True)
    release_year = serializers.IntegerField(read_only=True, allow_null=True)
    
    # فیلدهای مرتبط
    movie = MovieDocumentSerializer(read_only=True, allow_null=True)
    tags = TagDocumentSerializer(many=True, read_only=True)
    
    # تمام فیلدهای فیلترینگ
    media_type = serializers.CharField(read_only=True, allow_null=True)
    genre = serializers.CharField(read_only=True, allow_null=True)
    color = serializers.CharField(read_only=True, allow_null=True)
    aspect_ratio = serializers.CharField(read_only=True, allow_null=True)
    optical_format = serializers.CharField(read_only=True, allow_null=True)
    format = serializers.CharField(read_only=True, allow_null=True)
    interior_exterior = serializers.CharField(read_only=True, allow_null=True)
    time_of_day = serializers.CharField(read_only=True, allow_null=True)
    number_of_people = serializers.CharField(read_only=True, allow_null=True)
    gender = serializers.CharField(read_only=True, allow_null=True)
    age = serializers.CharField(read_only=True, allow_null=True)
    ethnicity = serializers.CharField(read_only=True, allow_null=True)
    frame_size = serializers.CharField(read_only=True, allow_null=True)
    shot_type = serializers.CharField(read_only=True, allow_null=True)
    composition = serializers.CharField(read_only=True, allow_null=True)
    lens_size = serializers.CharField(read_only=True, allow_null=True)
    lens_type = serializers.CharField(read_only=True, allow_null=True)
    lighting = serializers.CharField(read_only=True, allow_null=True)
    lighting_type = serializers.CharField(read_only=True, allow_null=True)
    camera_type = serializers.CharField(read_only=True, allow_null=True)
    resolution = serializers.CharField(read_only=True, allow_null=True)
    frame_rate = serializers.CharField(read_only=True, allow_null=True)
    exclude_nudity = serializers.BooleanField(read_only=True)
    exclude_violence = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)