from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.cache import cache
import logging
from PIL import Image as PILImage
import colorsys
from collections import Counter
import requests
from io import BytesIO
from pathlib import Path
from elasticsearch_dsl import Q, Search, connections
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from .serializers import ImageSearchResultSerializer, ColorSamplesSerializer, ColorSearchSerializer
from apps.common.serializers import Error404Serializer
from deck_search_utils.utils import cache_search_result
from deck_search_utils.user_api import user_api

logger = logging.getLogger(__name__)

# Helper function to create selectable options
def create_options_list(option_strings):
    """Convert list of strings to list of selectable option objects"""
    return [{"value": opt, "label": opt} for opt in option_strings]

# Filter configuration - defines all available filters and their options
FILTER_CONFIG = {
    "filters": [
        {
            "filter": "search",
            "options": [],
            "name": "Search",
            "format": "Text",
            "type": "text"
        },
        {
            "filter": "tags",
            "options": [],
            "name": "Tags",
            "format": "Comma-separated list of tag names",
            "type": "multi_select"
        },
        {
            "filter": "movie",
            "options": [],
            "name": "Movie",
            "format": "Comma-separated list of movie titles",
            "type": "multi_select",
            "has_slugs": True
        },
        {
            "filter": "media_type",
            "options": create_options_list(["Movie", "TV", "Trailer", "Music Video", "Commercial"]),
            "name": "Media Type",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "genre",
            "options": create_options_list([
                "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
                "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
                "Romance", "Science Fiction", "Thriller", "War", "Western"
            ]),
            "name": "Genre",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "time_period",
            "options": create_options_list([
                "Future", "2020s", "2010s", "2000s", "1990s", "1980s", "1970s",
                "1960s", "1950s", "1940s", "1930s", "1920s", "1910s", "1900s",
                "1800s", "1700s", "Renaissance: 1400-1700", "Medieval: 500-1400",
                "Ancient: 2000BC-500AD", "Stone Age: pre-2000BC"
            ]),
            "name": "Time Period",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "color",
            "options": create_options_list([
                "Warm", "Cool", "Mixed", "Saturated", "Desaturated", "Red", "Orange",
                "Yellow", "Green", "Cyan", "Blue", "Purple", "Magenta", "Pink",
                "White", "Sepia", "Black and White"
            ]),
            "name": "Color",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "shade",
            "options": [],
            "name": "Color Picker",
            "format": "HEX_COLOR~COLOR_DISTANCE~PROPORTION",
            "type": "color_picker"
        },
        {
            "filter": "aspect_ratio",
            "options": create_options_list([
                "9:16", "1 - square", "1.20", "1.33", "1.37", "1.43", "1.66",
                "1.78", "1.85", "1.90", "2.00", "2.20", "2.35", "2.39", "2.55",
                "2.67", "2.76+"
            ]),
            "name": "Aspect Ratio",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "optical_format",
            "options": create_options_list([
                "Anamorphic", "Spherical", "Super 35", "3 perf", "2 perf",
                "Open Gate", "3D"
            ]),
            "name": "Optical Format",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "lab_process",
            "options": create_options_list([
                "Bleach Bypass", "Cross Process", "Flashing"
            ]),
            "name": "Lab Process",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "format",
            "options": create_options_list([
                "Film - 35mm", "Film - 16mm", "Film - Super 8mm", "Film - 65mm / 70mm",
                "Film - IMAX", "Tape", "Digital", "Digital - Large Format", "Animation"
            ]),
            "name": "Format",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "int_ext",
            "options": create_options_list([
                "Interior", "Exterior"
            ]),
            "name": "Interior/Exterior",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "time_of_day",
            "options": create_options_list([
                "Day", "Night", "Dusk", "Dawn", "Sunrise", "Sunset"
            ]),
            "name": "Time of Day",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "numpeople",
            "options": create_options_list([
                "None", "1", "2", "3", "4", "5", "6+"
            ]),
            "name": "Number of People",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "gender",
            "options": create_options_list([
                "Male", "Female", "Trans"
            ]),
            "name": "Gender",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "subject_age",
            "options": create_options_list([
                "Baby", "Toddler", "Child", "Teenager", "Young Adult", "Mid-adult",
                "Middle age", "Senior"
            ]),
            "name": "Age",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "subject_ethnicity",
            "options": create_options_list([
                "Black", "White", "Latinx", "Middle Eastern", "South-East Asian",
                "East Asian", "South Asian", "Indigenous Peoples", "Mixed-race"
            ]),
            "name": "Ethnicity",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "frame_size",
            "options": create_options_list([
                "Extreme Wide", "Wide", "Medium Wide", "Medium", "Medium Close Up",
                "Close Up", "Extreme Close Up"
            ]),
            "name": "Frame Size",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "shot_type",
            "options": create_options_list([
                "Aerial", "Overhead", "High angle", "Low angle", "Dutch angle",
                "Establishing shot", "Over the shoulder", "Clean single", "2 shot",
                "3 shot", "Group shot", "Insert"
            ]),
            "name": "Shot Type",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "composition",
            "options": create_options_list([
                "Center", "Left heavy", "Right heavy", "Balanced", "Symmetrical", "Short side"
            ]),
            "name": "Composition",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "lens_type",
            "options": create_options_list([
                "Ultra Wide / Fisheye", "Wide", "Medium", "Long Lens", "Telephoto"
            ]),
            "name": "Lens Size",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "lighting",
            "options": create_options_list([
                "Soft light", "Hard light", "High contrast", "Low contrast",
                "Silhouette", "Top light", "Underlight", "Side light", "Backlight", "Edge light"
            ]),
            "name": "Lighting",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        },
        {
            "filter": "lighting_type",
            "options": create_options_list([
                "Daylight", "Sunny", "Overcast", "Moonlight", "Artificial light",
                "Practical light", "Fluorescent", "Firelight", "Mixed light"
            ]),
            "name": "Lighting Type",
            "format": "One or more options separated by underscores",
            "type": "multi_select"
        }
    ]
}


class SimilarImagesView(APIView):
    """Find similar images based on comprehensive multi-factor analysis"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ImageSearchResultSerializer
   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
       
        # Initialize Elasticsearch connection
        try:
            connections.create_connection(
                alias='default',
                hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']],
                timeout=20
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Elasticsearch connection: {e}", exc_info=True)

    @extend_schema(
        tags=['Search & Filtering'],
        description="Find similar images based on an image slug with Redis caching.",
        parameters=[
            OpenApiParameter(
                name='slug',
                location=OpenApiParameter.PATH,
                required=True,
                type=str,
                description="Slug of reference image for finding similar images"
            )
        ],
        responses={
            200: ImageSearchResultSerializer(many=True),
            404: Error404Serializer,
        }
    )
    def get(self, request, slug, *args, **kwargs):
        try:
            # Try to get cached results first
            cache_key = f'similar_images_{slug}'
            cached_results = cache.get(cache_key)
           
            if cached_results is not None:
                logger.info(f"Returning cached similar images for slug: {slug}")
                return Response(cached_results)

            # Find source image
            try:
                source_search = Search(index='images').query("term", slug=slug)
                response = source_search.execute()
                
                if not response.hits:
                    return Response(
                        {'detail': 'Image with the given slug not found.'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            except es_exceptions.ConnectionError:
                self.logger.error("Failed to connect to Elasticsearch", exc_info=True)
                return Response(
                    {'detail': 'Search service is temporarily unavailable. Please try again later.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            source_image = response.hits[0]
            source_data = source_image.to_dict()
            
            # Build similarity queries
            similarity_queries = []
            
            # 1. Core Content Similarity (boost: 6.0-4.5)
            core_fields = {
                'genre': 6.0, 'media_type': 5.5, 'color': 5.0, 'format': 5.0,
                'aspect_ratio': 4.5, 'optical_format': 4.5
            }
            
            for field, boost in core_fields.items():
                value = source_data.get(field)
                if value is not None and value != '' and value != []:
                    # ✅ Handle both string and array values
                    if isinstance(value, list):
                        if len(value) > 0:
                            # Use 'terms' query for arrays (like genre)
                            similarity_queries.append(Q('terms', **{field: value, "boost": boost}))
                    else:
                        # Use 'term' query for single values
                        similarity_queries.append(Q('term', **{field: {"value": value, "boost": boost}}))
            
            # 2. Movie/Production Context (boost: 4.5-4.0)
            movie_slug = source_data.get('movie', {}).get('slug')
            if movie_slug:
                similarity_queries.append(Q('term', **{'movie.slug': {"value": movie_slug, "boost": 4.5}}))
            
            # 3. Tag-based Similarity (boost: 4.0-3.5)
            tags = source_data.get('tags', [])
            if tags:
                for tag in tags[:5]:  # Top 5 tags
                    tag_slug = tag.get('slug')
                    if tag_slug:
                        similarity_queries.append(
                            Q('nested', path='tags',
                              query=Q('term', **{'tags.slug': {"value": tag_slug, "boost": 4.0}}))
                        )
            
            # 4. Technical Parameters (boost: 3.5-2.5)
            technical_fields = {
                'frame_size': 3.5, 'shot_type': 3.2, 'composition': 3.0,
                'interior_exterior': 2.8, 'time_of_day': 2.8, 'lighting': 2.8,
                'lighting_type': 2.8, 'camera_type': 2.6, 'lens_type': 2.6
            }
            
            for field, boost in technical_fields.items():
                value = source_data.get(field)
                if value is not None and value != '':
                    similarity_queries.append(Q('term', **{field: {"value": value, "boost": boost}}))
            
            # 5. Demographic fields (boost: 3.0-2.4)
            demographic_fields = {
                'gender': 3.0, 'age': 2.8, 'ethnicity': 2.8, 'number_of_people': 2.6
            }
            
            for field, boost in demographic_fields.items():
                value = source_data.get(field)
                if value is not None and value != '':
                    similarity_queries.append(Q('term', **{field: {"value": value, "boost": boost}}))
            
            # 6. Temporal Similarity (boost: 2.5-1.5)
            release_year = source_data.get('release_year')
            if release_year:
                year_boost = 2.5 if abs(2024 - release_year) <= 5 else 2.0 if abs(2024 - release_year) <= 15 else 1.5
                similarity_queries.append(Q('range', release_year={
                    'gte': release_year - 5,
                    'lte': release_year + 5,
                    'boost': year_boost
                }))
            
            # Exclude source image
            must_not_clause = Q('term', slug=slug)
            
            if not similarity_queries:
                return Response(
                    {'detail': 'No similarity criteria found for this image.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Build and execute final query
            final_query = Q('bool',
                          should=similarity_queries,
                          must_not=[must_not_clause],
                          minimum_should_match=1)
            
            similar_search = (Search(index='images')
                            .query(final_query)
                            .sort('_score', {'release_year': {'order': 'desc'}})
                            .extra(size=30, track_scores=True, explain=False)
                            [:30])
            
            results = similar_search.execute()
            
            # Format results
            enhanced_results = []
            for hit in results.hits:
                result_data = hit.to_dict()
                filtered_result = {
                    'slug': result_data.get('slug'),
                    'title': result_data.get('title'),
                    'description': result_data.get('description'),
                    'image_url': result_data.get('image_url'),
                    'movie': result_data.get('movie'),
                    'tags': result_data.get('tags', []),
                    'release_year': result_data.get('release_year'),
                    '_similarity_score': hit.meta.score
                }
                enhanced_results.append(filtered_result)
            
            # Cache for 1 hour
            cache.set(cache_key, enhanced_results, timeout=3600)
           
            return Response(enhanced_results)
            
        except Exception as e:
            logger.error(f"Error during similar search: {e}", exc_info=True)
            return Response(
                {'detail': 'An unexpected error occurred while processing your request.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserView(APIView):
    """Validate JWT token and check user subscription status"""
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    @extend_schema(
        tags=['User Management'],
        description="Validate JWT token and check user subscription status",
        parameters=[
            OpenApiParameter(
                'Authorization',
                location=OpenApiParameter.HEADER,
                required=True,
                type=str,
                description="JWT token in format: Bearer <token>"
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'user_uuid': {'type': 'string'},
                    'user_data': {'type': 'object'},
                    'is_vip_plus': {'type': 'boolean'},
                    'subscription_status': {'type': 'string'}
                }
            },
            401: {'description': 'Invalid or missing token'},
            500: {'description': 'Server error'}
        }
    )
    def get(self, request):
        try:
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header:
                return Response(
                    {'error': 'Authorization header is required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if not auth_header.startswith('Bearer '):
                return Response(
                    {'error': 'Invalid authorization header format'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            jwt_token = auth_header.replace('Bearer ', '')
            user_result = user_api.validate_jwt_and_get_user(jwt_token)
            
            if not user_result:
                return Response(
                    {'error': 'Invalid token or user not found'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            return Response({
                'user_uuid': user_result['user_uuid'],
                'user_data': user_result['user_data'],
                'is_vip_plus': user_result['is_vip_plus'],
                'subscription_status': 'VIP Plus Active' if user_result['is_vip_plus'] else 'Standard User'
            })
            
        except Exception as e:
            logger.error(f"Error in user validation: {e}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ColorSimilaritySearchView(APIView):
    """Get color information from Elasticsearch and find similar images"""
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = ImageSearchResultSerializer

    @extend_schema(
        tags=['Color Analysis'],
        summary="Get color information and find similar images",
        description="Get color information from indexed images and optionally find similar images by color",
        parameters=[
            OpenApiParameter(
                name='slug',
                location=OpenApiParameter.QUERY,
                required=True,
                type=str,
                description="Image slug to get color information"
            ),
            OpenApiParameter(
                name='find_similar',
                location=OpenApiParameter.QUERY,
                required=False,
                type=bool,
                description="If true, find similar images by color (default: false)"
            ),
            OpenApiParameter(
                name='limit',
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="Number of similar images to return (default: 20)"
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'image_slug': {'type': 'string'},
                    'color_analysis': {'type': 'object'},
                    'similar_images': {'type': 'array'}
                }
            },
            404: {'description': 'Image not found'},
            500: {'description': 'Server error'}
        }
    )
    def get(self, request):
        """Get color information from Elasticsearch"""
        try:
            slug = request.query_params.get('slug')
            find_similar = request.query_params.get('find_similar', 'false').lower() == 'true'
            limit = int(request.query_params.get('limit', 20))

            if not slug:
                return Response(
                    {'error': 'Missing required parameter: slug'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Search for image in Elasticsearch
            search = Search(index='images')
            search = search.query('term', slug=slug)
            response = search.execute()

            if not response.hits:
                return Response(
                    {'error': f'Image not found in index: {slug}'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get image data
            image_data = response.hits[0].to_dict()

            # Extract color information
            color_info = {
                'success': True,
                'image_slug': slug,
                'image_title': image_data.get('title'),
                'image_url': image_data.get('image_url'),
                'color_analysis': {
                    'primary_color_hex': image_data.get('primary_color_hex'),
                    'dominant_colors': image_data.get('dominant_colors', []),
                    'primary_colors': image_data.get('primary_colors', []),
                    'color_palette': image_data.get('color_palette', {}),
                    'color_samples': image_data.get('color_samples', []),
                    'color_temperature': image_data.get('color_temperature'),
                    'hue_range': image_data.get('hue_range'),
                    'color_search_terms': image_data.get('color_search_terms', [])
                }
            }

            # Find similar images by color if requested
            if find_similar and image_data.get('primary_color_hex'):
                similar_images = self._find_similar_by_color(
                    image_data.get('primary_colors', []),
                    image_data.get('primary_color_hex'),
                    limit,
                    exclude_slug=slug
                )
                color_info['similar_images'] = similar_images
                color_info['similar_count'] = len(similar_images)

            return Response(color_info)

        except Exception as e:
            logger.error(f"Error in color similarity GET: {e}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _find_similar_by_color(self, primary_colors, main_hex, limit, exclude_slug):
        """Find images with similar colors"""
        try:
            client = Elasticsearch(hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']])
            search = Search(using=client, index='images')
            
            color_queries = []
            
            # Search by primary color
            if main_hex:
                color_queries.append(Q('term', primary_color_hex={"value": main_hex, "boost": 10.0}))
            
            # Search by primary colors array
            if primary_colors:
                for i, color in enumerate(primary_colors[:5]):
                    boost = 8.0 - i
                    if isinstance(color, dict):
                        hex_color = color.get('hex')
                        if hex_color:
                            color_queries.append(Q('term', primary_color_hex={"value": hex_color, "boost": boost}))
            
            # Exclude source image
            if color_queries:
                final_query = Q('bool', 
                              should=color_queries, 
                              must_not=[Q('term', slug=exclude_slug)],
                              minimum_should_match=1)
                search = search.query(final_query)
            
            search = search.extra(size=limit, track_scores=True)
            response = search.execute()
            
            # Format results
            results = []
            for hit in response.hits:
                results.append({
                    'slug': hit.slug,
                    'title': getattr(hit, 'title', ''),
                    'image_url': getattr(hit, 'image_url', ''),
                    'primary_color_hex': getattr(hit, 'primary_color_hex', ''),
                    'color_similarity_score': hit.meta.score
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar colors: {e}", exc_info=True)
            return []

    @extend_schema(
        tags=['Image Upload & Color Search'],
        description="Upload an image and find similar images based on color analysis",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'image': {'type': 'string', 'format': 'binary'},
                    'image_url': {'type': 'string'},
                    'limit': {'type': 'integer', 'default': 20}
                }
            }
        },
        responses={
            200: ImageSearchResultSerializer(many=True),
            400: {'description': 'Bad request'},
            500: {'description': 'Server error'}
        },
        examples=[
            OpenApiExample(
                'Upload Image File',
                summary='Upload image file for color analysis',
                description='Upload an image file to extract colors and find similar images',
                value={
                    'image': 'binary file data',
                    'limit': 20
                }
            )
        ]
    )
    def post(self, request):
        """Upload image and find color-similar images"""
        try:
            uploaded_image = request.FILES.get('image')
            image_url = request.data.get('image_url')
            limit = int(request.data.get('limit', 20))

            if not uploaded_image and not image_url:
                return Response(
                    {'error': 'Either image file or image_url is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract colors from uploaded/URL image
            image_colors = self.extract_colors_from_image(uploaded_image, image_url)
            
            if not image_colors:
                return Response(
                    {'error': 'Could not process image or extract colors'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Find similar images
            similar_images = self.find_similar_images_by_color(image_colors, limit)
            
            return Response({
                'success': True,
                'extracted_colors': image_colors[:5],
                'similar_images': similar_images,
                'count': len(similar_images)
            })

        except Exception as e:
            logger.error(f"Error in color similarity POST: {e}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def extract_colors_from_image(self, uploaded_image=None, image_url=None):
        """Extract colors using UltimateColorProcessor"""
        import tempfile
        import shutil
        from apps.color_ai.color_processor import UltimateColorProcessor
        
        try:
            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            temp_path = None
            
            try:
                # Save uploaded image to temp file
                if uploaded_image:
                    temp_path = Path(temp_dir) / 'upload.jpg'
                    image = PILImage.open(uploaded_image)
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    image.save(temp_path, 'JPEG')
                    
                elif image_url:
                    response = requests.get(image_url, timeout=10)
                    response.raise_for_status()
                    temp_path = Path(temp_dir) / 'url_image.jpg'
                    image = PILImage.open(BytesIO(response.content))
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    image.save(temp_path, 'JPEG')
                else:
                    return None

                # Use UltimateColorProcessor for high-quality color extraction
                processor = UltimateColorProcessor(images_folder=temp_dir, max_colors=15)
                analysis_result = processor.analyze_image_colors(temp_path)
                
                if not analysis_result or not analysis_result.get('main_palette'):
                    logger.warning("UltimateColorProcessor returned no colors")
                    return None

                # Convert to our format
                main_palette = analysis_result['main_palette']
                processed_colors = []
                
                for color in main_palette:
                    processed_colors.append({
                        'rgb': color['rgb'],
                        'hex': color['hex'],
                        'percentage': color.get('count', 0),
                        'hsl': {
                            'hue': color.get('hue', 0),
                            'saturation': color.get('saturation', 0),
                            'lightness': color.get('lightness', 0)
                        },
                        'color_name': self._get_color_name_from_hue(color.get('hue', 0))
                    })
                
                logger.info(f"Extracted {len(processed_colors)} colors using UltimateColorProcessor")
                return processed_colors
                
            finally:
                # Cleanup temp files
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            logger.error(f"Error extracting colors with UltimateColorProcessor: {e}", exc_info=True)
            return None

    def _get_color_name_from_hue(self, hue):
        """Get color name from hue value"""
        if hue < 30 or hue >= 330:
            return 'red'
        elif 30 <= hue < 60:
            return 'orange'
        elif 60 <= hue < 90:
            return 'yellow'
        elif 90 <= hue < 150:
            return 'green'
        elif 150 <= hue < 210:
            return 'cyan'
        elif 210 <= hue < 270:
            return 'blue'
        elif 270 <= hue < 330:
            return 'purple'
        else:
            return 'neutral'

    def find_similar_images_by_color(self, image_colors, limit=20):
        """Find images with similar colors"""
        try:
            client = Elasticsearch(hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']])
            search = Search(using=client, index='images')
            
            color_queries = []
            
            for i, color_data in enumerate(image_colors[:5]):
                boost = 10.0 - i
                hex_color = color_data['hex']
                color_queries.append(Q('term', primary_color_hex={"value": hex_color, "boost": boost}))
            
            if color_queries:
                final_query = Q('bool', should=color_queries, minimum_should_match=1)
                search = search.query(final_query)
            
            search = search.extra(size=limit, track_scores=True)
            response = search.execute()
            
            results = []
            for hit in response.hits:
                result_data = hit.to_dict()
                result_data['_color_similarity_score'] = hit.meta.score
                results.append(result_data)
            
            return results

        except Exception as e:
            logger.error(f"Error finding similar images: {e}", exc_info=True)
            return []

    @staticmethod
    def rgb_to_hsl(rgb):
        """Convert RGB to HSL"""
        r, g, b = rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return {
            'hue': round(h * 360, 1),
            'saturation': round(s * 100, 1),
            'lightness': round(l * 100, 1)
        }


class ImageColorSamplesView(APIView):
    """Get color samples for a specific image"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ColorSamplesSerializer

    @extend_schema(
        tags=['Color Operations'],
        summary="Get image color samples",
        description="Returns color samples from indexed image",
        parameters=[
            OpenApiParameter('slug', str, OpenApiParameter.PATH, description="Image slug"),
        ]
    )
    def get(self, request, slug):
        try:
            search = Search(using='default', index='images')
            search = search.query('term', slug=slug)
            response = search.execute()

            if not response.hits:
                return Response(
                    {'error': 'Image not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            image_data = response.hits[0]

            return Response({
                'image_slug': image_data.slug,
                'color_samples': getattr(image_data, 'color_samples', []),
                'dominant_colors': getattr(image_data, 'dominant_colors', []),
                'color_histogram': getattr(image_data, 'color_histogram', {})
            })

        except Exception as e:
            logger.error(f"Error retrieving color samples: {e}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ImageColorSearchView(APIView):
    """Advanced color search endpoint"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ImageSearchResultSerializer

    @extend_schema(
        tags=['Color Operations'],
        summary="Advanced color search",
        description="Search images based on various color parameters",
        parameters=[
            OpenApiParameter('hex', str, OpenApiParameter.QUERY, description="Hex color code"),
            OpenApiParameter('temperature', str, OpenApiParameter.QUERY, enum=['warm', 'cool', 'neutral']),
            OpenApiParameter('limit', int, OpenApiParameter.QUERY, description="Number of results"),
        ]
    )
    def get(self, request):
        try:
            hex_color = request.query_params.get('hex')
            temperature = request.query_params.get('temperature')
            limit = int(request.query_params.get('limit', 20))

            search = Search(using='default', index='images')

            if hex_color:
                search = search.query('term', primary_color_hex=hex_color)
            elif temperature:
                search = search.query('term', color_temperature=temperature)
            else:
                return Response(
                    {'error': 'At least one color parameter must be specified'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            search = search[:limit]
            response = search.execute()

            results = []
            for hit in response.hits:
                results.append({
                    'slug': hit.slug,
                    'title': getattr(hit, 'title', ''),
                    'primary_color_hex': getattr(hit, 'primary_color_hex', ''),
                    'score': hit.meta.score if hasattr(hit.meta, 'score') else 1.0
                })

            return Response({
                'count': len(results),
                'results': results
            })

        except Exception as e:
            logger.error(f"Error in color search: {e}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FiltersView(APIView):
    """Get filter options or search images"""
    permission_classes = [permissions.AllowAny]

    def _safe_int_param(self, value, default):
        if value is None or value == '':
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @extend_schema(
        tags=['Search & Filtering'],
        summary="Get filters or search images",
        description="Returns filter options or search results",
        parameters=[
            OpenApiParameter('search', str, OpenApiParameter.QUERY),
            OpenApiParameter('color', str, OpenApiParameter.QUERY),
            OpenApiParameter('media_type', str, OpenApiParameter.QUERY),
            OpenApiParameter('genre', str, OpenApiParameter.QUERY),
            OpenApiParameter('limit', int, OpenApiParameter.QUERY),
            OpenApiParameter('offset', int, OpenApiParameter.QUERY),
        ]
    )
    def get(self, request):
        try:
            search_params = {
                'search': request.query_params.get('search'),
                'tags': request.query_params.get('tags'),
                'movie': request.query_params.get('movie'),
                'media_type': request.query_params.get('media_type'),
                'genre': request.query_params.get('genre'),
                'color': request.query_params.get('color'),
                'time_of_day': request.query_params.get('time_of_day'),
                'interior_exterior': request.query_params.get('int_ext'),
                'limit': self._safe_int_param(request.query_params.get('limit'), 20),
                'offset': self._safe_int_param(request.query_params.get('offset'), 0)
            }

            applied_filters = {k: v for k, v in search_params.items() if v is not None and k not in ['limit', 'offset']}

            if not applied_filters:
                return Response({
                    "success": True,
                    "message": "Filters",
                    "data": FILTER_CONFIG
                })

            return self._perform_elasticsearch_search(search_params, applied_filters)

        except Exception as e:
            logger.error(f"Error in filters: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _perform_elasticsearch_search(self, search_params, applied_filters):
        """Perform Elasticsearch search with given parameters"""
        try:
            client = Elasticsearch(hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']])
            search = Search(using=client, index='images')

            filter_queries = []

            # Text search
            if search_params.get('search'):
                search_text = search_params['search'].strip()
                logger.info(f"Adding text search query for: {search_text}")
                filter_queries.append(
                    Q('multi_match', 
                      query=search_text, 
                      fields=['title^3', 'description^2', 'tags.name'],
                      fuzziness='AUTO')
                )

            # Color filter - بدون .keyword چون field از قبل keyword است
            if search_params.get('color'):
                color_value = search_params['color'].strip()
                logger.info(f"Adding color filter: {color_value}")
                # استفاده از term بدون .keyword
                filter_queries.append(Q('term', color=color_value))

            # Media type filter
            if search_params.get('media_type'):
                media_type = search_params['media_type'].strip()
                logger.info(f"Adding media_type filter: {media_type}")
                filter_queries.append(Q('term', media_type=media_type))

            # Genre filter
            if search_params.get('genre'):
                genres = [g.strip() for g in search_params['genre'].split(',')]
                logger.info(f"Adding genre filter: {genres}")
                filter_queries.append(Q('terms', genre=genres))

            # Time of day filter
            if search_params.get('time_of_day'):
                filter_queries.append(Q('term', time_of_day=search_params['time_of_day'].strip()))

            # Interior/Exterior filter
            if search_params.get('interior_exterior'):
                filter_queries.append(Q('term', interior_exterior=search_params['interior_exterior'].strip()))

            # Apply filters
            if filter_queries:
                search = search.query(Q('bool', must=filter_queries))
            else:
                search = search.query('match_all')

            # Pagination
            limit = min(int(search_params.get('limit', 20)), 100)
            offset = int(search_params.get('offset', 0))

            logger.info(f"Executing search with {len(filter_queries)} filters, limit={limit}, offset={offset}")

            # Execute search
            response = search[offset:offset + limit].execute()

            # Format results
            results = []
            for hit in response:
                data = hit.to_dict()
                results.append({
                    'id': data.get('id'),
                    'slug': data.get('slug'),
                    'title': data.get('title'),
                    'description': data.get('description'),
                    'image_url': data.get('image_url'),
                    'movie': data.get('movie'),
                    'tags': data.get('tags', []),
                    'color': data.get('color'),
                    'media_type': data.get('media_type'),
                    'genre': data.get('genre'),
                    'time_of_day': data.get('time_of_day'),
                    'interior_exterior': data.get('interior_exterior')
                })

            total_count = response.hits.total.value if hasattr(response.hits.total, 'value') else len(response.hits)

            logger.info(f"Search completed: found {total_count} total, returning {len(results)} results")

            return Response({
                'success': True,
                'count': len(results),
                'total': total_count,
                'results': results,
                'filters_applied': applied_filters,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + limit) < total_count
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Elasticsearch search error: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': 'Search failed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )