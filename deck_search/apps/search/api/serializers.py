from rest_framework import serializers

class TagDocumentSerializer(serializers.Serializer):
    slug = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)

class MovieDocumentSerializer(serializers.Serializer):
    slug = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    year = serializers.IntegerField(read_only=True)

class ImageSearchResultSerializer(serializers.Serializer):
    _id = serializers.CharField(source='meta.id', read_only=True)
    _score = serializers.FloatField(source='meta.score', read_only=True)

    id = serializers.IntegerField(read_only=True)
    slug = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    image_url = serializers.URLField(read_only=True)
    release_year = serializers.IntegerField(read_only=True, allow_null=True)
    
    movie = MovieDocumentSerializer(read_only=True, allow_null=True)
    tags = TagDocumentSerializer(many=True, read_only=True)
    
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

class ColorSamplesSerializer(serializers.Serializer):
    """Serializer for color samples response"""
    colors = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of hex color codes extracted from the image"
    )
    dominant_color = serializers.CharField(
        help_text="Most dominant color in hex format"
    )
    color_count = serializers.IntegerField(
        help_text="Number of unique colors found"
    )

class ColorSearchSerializer(serializers.Serializer):
    """Serializer for color search response"""
    results = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of matching images"
    )
    count = serializers.IntegerField(
        help_text="Total number of matching images"
    )