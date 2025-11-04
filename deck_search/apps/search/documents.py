# apps/search/documents.py
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from apps.images.models import Image


@registry.register_document
class ImageDocument(Document):
    """Elasticsearch document for Image model with complete color support"""
    
    # Basic fields
    id = fields.IntegerField()
    slug = fields.KeywordField()
    title = fields.TextField(fields={'raw': fields.KeywordField()})
    description = fields.TextField()
    image_url = fields.KeywordField()
    release_year = fields.IntegerField()

    # Relationships
    movie = fields.ObjectField(properties={
        'slug': fields.KeywordField(),
        'title': fields.TextField(),
        'year': fields.IntegerField(),
    })

    tags = fields.NestedField(properties={
        'slug': fields.KeywordField(),
        'name': fields.KeywordField(),
    })

    # All option fields as Keywords
    media_type = fields.KeywordField()
    genre = fields.KeywordField()
    color = fields.KeywordField()
    aspect_ratio = fields.KeywordField()
    optical_format = fields.KeywordField()
    format = fields.KeywordField()
    interior_exterior = fields.KeywordField()
    time_of_day = fields.KeywordField()
    number_of_people = fields.KeywordField()
    gender = fields.KeywordField()
    age = fields.KeywordField()
    ethnicity = fields.KeywordField()
    frame_size = fields.KeywordField()
    shot_type = fields.KeywordField()
    composition = fields.KeywordField()
    lens_size = fields.KeywordField()
    lens_type = fields.KeywordField()
    lighting = fields.KeywordField()
    lighting_type = fields.KeywordField()
    camera_type = fields.KeywordField()
    resolution = fields.KeywordField()
    frame_rate = fields.KeywordField()
    exclude_nudity = fields.BooleanField()
    exclude_violence = fields.BooleanField()

    # Color analysis fields (stored as-is from JSON fields)
    primary_color_hex = fields.KeywordField()
    secondary_color_hex = fields.KeywordField()
    color_temperature = fields.KeywordField()
    dominant_colors = fields.ObjectField(enabled=True)
    primary_colors = fields.ObjectField(enabled=True)
    color_palette = fields.ObjectField(enabled=True)
    color_samples = fields.ObjectField(enabled=True)
    color_histogram = fields.ObjectField(enabled=True)
    color_search_terms = fields.KeywordField(multi=True)

    created_at = fields.DateField()
    updated_at = fields.DateField()

    class Index:
        name = 'images'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Image
        fields = []
        related_models = ['movie', 'tags']

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Image):
            return related_instance
        return related_instance.image_set.all()

    # Helper to extract value from option objects
    def _extract_value(self, obj):
        """Extract string value from option object"""
        if obj is None:
            return None
        if hasattr(obj, 'value'):
            return obj.value
        if isinstance(obj, str):
            return obj
        if isinstance(obj, int):
            return str(obj)
        return str(obj)

    # Prepare methods for ALL option fields
    def prepare_media_type(self, instance):
        return self._extract_value(instance.media_type)

    def prepare_genre(self, instance):
        """Genre is ManyToMany"""
        try:
            genre_qs = instance.genre.all()
            return [self._extract_value(g) for g in genre_qs]
        except:
            return []

    def prepare_color(self, instance):
        """Special handling for color field"""
        if not instance.color:
            return None
        
        # Color mapping for integer values
        COLOR_MAP = {
            1: 'Warm', 2: 'Cool', 3: 'Mixed',
            4: 'Saturated', 5: 'Desaturated',
            6: 'Red', 7: 'Orange', 8: 'Yellow',
            9: 'Green', 10: 'Cyan', 11: 'Blue',
            12: 'Purple', 13: 'Magenta', 14: 'Pink',
            15: 'White', 16: 'Sepia', 17: 'Black and White',
            48: 'Warm'
        }
        
        # Handle integer color
        if isinstance(instance.color, int):
            return COLOR_MAP.get(instance.color, str(instance.color))
        
        # Handle object with value
        return self._extract_value(instance.color)

    def prepare_aspect_ratio(self, instance):
        return self._extract_value(instance.aspect_ratio)

    def prepare_optical_format(self, instance):
        return self._extract_value(instance.optical_format)

    def prepare_format(self, instance):
        return self._extract_value(instance.format)

    def prepare_interior_exterior(self, instance):
        return self._extract_value(instance.interior_exterior)

    def prepare_time_of_day(self, instance):
        return self._extract_value(instance.time_of_day)

    def prepare_number_of_people(self, instance):
        return self._extract_value(instance.number_of_people)

    def prepare_gender(self, instance):
        return self._extract_value(instance.gender)

    def prepare_age(self, instance):
        return self._extract_value(instance.age)

    def prepare_ethnicity(self, instance):
        return self._extract_value(instance.ethnicity)

    def prepare_frame_size(self, instance):
        return self._extract_value(instance.frame_size)

    def prepare_shot_type(self, instance):
        return self._extract_value(instance.shot_type)

    def prepare_composition(self, instance):
        return self._extract_value(instance.composition)

    def prepare_lens_size(self, instance):
        return self._extract_value(instance.lens_size)

    def prepare_lens_type(self, instance):
        return self._extract_value(instance.lens_type)

    def prepare_lighting(self, instance):
        return self._extract_value(instance.lighting)

    def prepare_lighting_type(self, instance):
        return self._extract_value(instance.lighting_type)

    def prepare_camera_type(self, instance):
        return self._extract_value(instance.camera_type)

    def prepare_resolution(self, instance):
        return self._extract_value(instance.resolution)

    def prepare_frame_rate(self, instance):
        return self._extract_value(instance.frame_rate)

    def prepare_movie(self, instance):
        if not instance.movie:
            return None
        return {
            'slug': instance.movie.slug,
            'title': instance.movie.title,
            'year': getattr(instance.movie, 'year', instance.release_year)
        }

    def prepare_tags(self, instance):
        return [
            {'slug': tag.slug, 'name': tag.name}
            for tag in instance.tags.all()
        ]

    # Color analysis fields - get from JSONField or attributes
    def prepare_primary_color_hex(self, instance):
        return getattr(instance, 'primary_color_hex', None)

    def prepare_secondary_color_hex(self, instance):
        return getattr(instance, 'secondary_color_hex', None)

    def prepare_color_temperature(self, instance):
        return getattr(instance, 'color_temperature', None)

    def prepare_dominant_colors(self, instance):
        val = getattr(instance, 'dominant_colors', None)
        # Return as-is if it's dict/list, otherwise empty dict
        if val and isinstance(val, (dict, list)):
            return val
        return {}

    def prepare_primary_colors(self, instance):
        val = getattr(instance, 'primary_colors', None)
        if val and isinstance(val, (dict, list)):
            return val
        return {}

    def prepare_color_palette(self, instance):
        val = getattr(instance, 'color_palette', None)
        if val and isinstance(val, (dict, list)):
            return val
        return {}

    def prepare_color_samples(self, instance):
        val = getattr(instance, 'color_samples', None)
        if val and isinstance(val, (dict, list)):
            return val
        return {}

    def prepare_color_histogram(self, instance):
        val = getattr(instance, 'color_histogram', None)
        if val and isinstance(val, (dict, list)):
            return val
        return {}

    def prepare_color_search_terms(self, instance):
        val = getattr(instance, 'color_search_terms', None)
        if val and isinstance(val, list):
            return val
        return []