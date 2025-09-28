from elasticsearch_dsl import Document, Date, Keyword, Text, Integer, Boolean, Object, Nested

class ImageDocument(Document):
    id = Integer()
    slug = Keyword()
    title = Text(fields={'raw': Keyword()})
    description = Text()
    image_url = Keyword()
    release_year = Integer()

    movie = Object(properties={
        'slug': Keyword(),
        'title': Text(fields={'raw': Keyword()}),
        'year': Integer(),
    })

    tags = Nested(properties={
        'slug': Keyword(),
        'name': Keyword(),
    })

    media_type = Keyword()
    genre = Keyword()
    color = Keyword()
    aspect_ratio = Keyword()
    optical_format = Keyword()
    format = Keyword()
    interior_exterior = Keyword()
    time_of_day = Keyword()
    number_of_people = Keyword()
    gender = Keyword()
    age = Keyword()
    ethnicity = Keyword()
    frame_size = Keyword()
    shot_type = Keyword()
    composition = Keyword()
    lens_size = Keyword()
    lens_type = Keyword()
    lighting = Keyword()
    lighting_type = Keyword()
    camera_type = Keyword()
    resolution = Keyword()
    frame_rate = Keyword()
    exclude_nudity = Boolean()
    exclude_violence = Boolean()

    # Color analysis fields
    dominant_colors = Nested(properties={
        'rgb': Keyword(),
        'hex': Keyword(),
        'percentage': Integer(),
        'hsl': Object(properties={
            'hue': Integer(),
            'saturation': Integer(),
            'lightness': Integer()
        }),
        'color_name': Keyword()
    })
    primary_color_hex = Keyword()
    secondary_color_hex = Keyword()
    color_palette = Object(properties={
        'dominant': Nested(),
        'brightness': Object(properties={
            'average': Integer(),
            'category': Keyword()
        }),
        'saturation': Object(properties={
            'average': Integer(),
            'category': Keyword()
        }),
        'color_temperature': Keyword()
    })

    # Additional color analysis fields
    color_samples = Nested(properties={
        'position': Integer(),
        'coordinates': Object(properties={
            'x': Integer(),
            'y': Integer()
        }),
        'rgb': Keyword(),
        'hex': Keyword(),
        'hsl': Object(properties={
            'hue': Integer(),
            'saturation': Integer(),
            'lightness': Integer()
        }),
        'color_name': Keyword()
    })

    color_histogram = Object(properties={
        'red': Keyword(),  # Array of integers
        'green': Keyword(),  # Array of integers
        'blue': Keyword(),  # Array of integers
        'bins': Keyword(),  # Array of integers
        'total_pixels': Integer()
    })

    # Enhanced primary colors with similar colors
    primary_colors = Nested(properties={
        'rank': Integer(),
        'hex': Keyword(),
        'percentage': Integer(),
        'rgb': Keyword(),
        'hsl': Object(properties={
            'hue': Integer(),
            'saturation': Integer(),
            'lightness': Integer()
        }),
        'color_name': Keyword(),
        'is_main': Boolean(),
        'search_boost': Integer(),
        'similar_hexes': Keyword(multi=True),  # Array of similar hex codes
        'similar_colors': Nested(properties={
            'hex': Keyword(),
            'rgb': Keyword(),
            'distance': Integer()
        })
    })

    color_search_terms = Keyword(multi=True)  # Array of search terms

    created_at = Date()
    updated_at = Date()

    class Index:
        name = 'images'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }
