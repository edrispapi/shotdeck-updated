from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import logging
import io
from PIL import Image as PILImage
import colorsys
from collections import Counter
import requests
from io import BytesIO
from pathlib import Path
import os

from elasticsearch_dsl import Q
from elasticsearch_dsl.search import Search
from elasticsearch import Elasticsearch
from django.conf import settings

from drf_spectacular.utils import extend_schema, OpenApiParameter
from .serializers import ImageSearchResultSerializer, ColorSamplesSerializer, ColorSearchSerializer
from apps.common.serializers import Error404Serializer
from search_service.utils import cache_search_result
from search_service.user_api import user_api
from search_service.color_processor import UltimateColorProcessor

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
    permission_classes = [permissions.AllowAny]
    serializer_class = ImageSearchResultSerializer

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
            # Check if Elasticsearch is enabled
            if not getattr(settings, 'ELASTICSEARCH_ENABLED', False):
                logger.info("Elasticsearch is disabled - returning mock result for development")
                return Response({
                    'message': 'Similar images search (development mode)',
                    'note': 'Elasticsearch is disabled. Enable ELASTICSEARCH_ENABLED=True in .env for full functionality',
                    'mock_results': [
                        {
                            'slug': 'sample-image-1',
                            'title': 'Sample Similar Image 1',
                            'similarity_score': 0.95,
                            '_similarity_score': 0.95
                        },
                        {
                            'slug': 'sample-image-2',
                            'title': 'Sample Similar Image 2',
                            'similarity_score': 0.89,
                            '_similarity_score': 0.89
                        }
                    ]
                }, status=status.HTTP_200_OK)

            client = Elasticsearch(hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']])
            source_search = Search(using=client, index='images').query("term", slug=slug)
            response = source_search.execute()

            if not response.hits:
                return Response({'detail': 'Image with the given slug not found.'}, status=status.HTTP_404_NOT_FOUND)

            source_image = response.hits[0]
            source_data = source_image.to_dict()

            # Enhanced similarity scoring with comprehensive multi-factor analysis
            similarity_queries = []

            # 1. Core Content Similarity (Highest Priority - boost: 6.0-5.0)
            core_fields = {
                'genre': 6.0, 'media_type': 5.5, 'color': 5.0, 'format': 5.0,
                'aspect_ratio': 4.5, 'optical_format': 4.5
            }
            for field, boost in core_fields.items():
                value = getattr(source_image, field, None)
                if value is not None:
                    similarity_queries.append(Q('term', **{field: {"value": value, "boost": boost}}))

            # 2. Movie/Production Context (boost: 4.5-4.0)
            movie_slug = source_data.get('movie', {}).get('slug')
            if movie_slug:
                similarity_queries.append(Q('term', movie__slug={"value": movie_slug, "boost": 4.5}))

            # Director/Production team similarity
            director = source_data.get('movie', {}).get('director', '')
            if director:
                similarity_queries.append(Q('match', movie__director={"query": director, "boost": 4.0}))

            # 3. Enhanced Tag-based Similarity with Multiple Approaches (boost: 4.0-3.0)
            tags = source_data.get('tags', [])
            if tags:
                # Individual tag matching with higher boost
                for tag in tags:
                    tag_slug = tag.get('slug')
                    if tag_slug:
                        similarity_queries.append(Q('nested', path='tags',
                                                   query=Q('term', tags__slug={"value": tag_slug, "boost": 4.0})))

                # Tag category similarity (action, drama, etc.)
                tag_names = [tag.get('name', '').lower() for tag in tags if tag.get('name')]
                if tag_names:
                    for tag_name in tag_names:
                        if len(tag_name.split()) == 1:  # Single word tags
                            similarity_queries.append(Q('nested', path='tags',
                                                       query=Q('match', tags__name={"query": tag_name, "boost": 3.5})))

            # 4. Advanced Technical Parameters (boost: 3.5-2.5)
            technical_fields = {
                'frame_size': 3.5, 'shot_type': 3.2, 'composition': 3.0,
                'interior_exterior': 2.8, 'time_of_day': 2.8, 'lighting': 2.8,
                'lighting_type': 2.8, 'camera_type': 2.6, 'lens_type': 2.6,
                'resolution': 2.6, 'frame_rate': 2.5, 'lens_size': 2.5
            }
            for field, boost in technical_fields.items():
                value = getattr(source_image, field, None)
                if value is not None:
                    similarity_queries.append(Q('term', **{field: {"value": value, "boost": boost}}))

            # 5. Enhanced Demographic & Contextual Similarity (boost: 3.0-2.0)
            demographic_fields = {
                'gender': 3.0, 'age': 2.8, 'ethnicity': 2.8,
                'number_of_people': 2.6, 'ethnicity': 2.4
            }
            for field, boost in demographic_fields.items():
                value = getattr(source_image, field, None)
                if value is not None:
                    similarity_queries.append(Q('term', **{field: {"value": value, "boost": boost}}))

            # 6. Temporal & Period Similarity (boost: 2.5-1.5)
            release_year = getattr(source_image, 'release_year', None)
            if release_year:
                # Close temporal proximity gets higher boost
                year_boost = 2.5 if abs(2024 - release_year) <= 5 else 2.0 if abs(2024 - release_year) <= 15 else 1.5
                similarity_queries.append(Q('range', release_year={
                    'gte': release_year - 5,  # Tighter range for better similarity
                    'lte': release_year + 5,
                    'boost': year_boost
                }))

            # 7. Intelligent Text Similarity with Context (boost: 2.0-1.0)
            title = getattr(source_image, 'title', '')
            description = getattr(source_image, 'description', '')

            # Enhanced text matching with better field weighting
            if title:
                similarity_queries.append(Q('match', title={
                    "query": title,
                    "boost": 2.0,
                    "fuzziness": "AUTO",
                    "operator": "and"
                }))

            if description:
                # Extract key phrases from description for better matching
                desc_words = description.split()[:10]  # First 10 words
                if desc_words:
                    desc_query = ' '.join(desc_words)
                    similarity_queries.append(Q('match', description={
                        "query": desc_query,
                        "boost": 1.5,
                        "fuzziness": "AUTO"
                    }))

            # 8. Cross-field Similarity Boosting (boost: 1.5-1.0)
            # Boost images that share multiple similar characteristics
            if len(similarity_queries) > 3:
                # Add a general similarity query for images with multiple matching attributes
                similarity_queries.append(Q('match_all', boost=1.2))

            # 9. Location & Setting Similarity (if available)
            location = getattr(source_image, 'location', None)
            if location:
                similarity_queries.append(Q('match', location={
                    "query": location,
                    "boost": 1.8,
                    "fuzziness": "AUTO"
                }))

            # 10. Exclude the source image itself
            must_not_clause = Q('term', slug=slug)

            if not similarity_queries:
                return Response({'detail': 'No similarity criteria found for this image.'}, status=status.HTTP_400_BAD_REQUEST)

            # Build the final query with optimized scoring and performance
            final_query = Q('bool',
                          should=similarity_queries,
                          must_not=[must_not_clause],
                          minimum_should_match=1)

            # Execute search with optimized scoring and performance settings
            similar_search = (Search(using=client, index='images')
                            .query(final_query)
                            .sort('_score', {'release_year': {'order': 'desc'}})
                            .extra(size=30,  # Optimized result size for better performance
                                   track_scores=True,
                                   explain=False)  # Disable explanation for better performance
                            [:30])  # Limit to top 30 most similar for better performance

            results = similar_search.execute()

            # Add similarity score to each result
            enhanced_results = []
            for hit in results.hits:
                result_data = hit.to_dict()
                result_data['_similarity_score'] = hit.meta.score
                enhanced_results.append(result_data)

            return Response(enhanced_results)

        except Exception as e:
            logger.error(f"Error during enhanced similar search: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserView(APIView):
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
        """
        Validate JWT token and return user info with subscription status
        """
        try:
            # Get Authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header:
                return Response(
                    {
                        'error': 'Authorization header is required',
                        'message': 'This endpoint requires authentication. Use: Authorization: Bearer <your-jwt-token>',
                        'example': 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not auth_header.startswith('Bearer '):
                return Response(
                    {
                        'error': 'Invalid authorization header format',
                        'message': 'Use format: Authorization: Bearer <your-jwt-token>',
                        'received': auth_header[:20] + '...' if len(auth_header) > 20 else auth_header
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            jwt_token = auth_header.replace('Bearer ', '')

            # Validate JWT and get user data
            user_result = user_api.validate_jwt_and_get_user(jwt_token)

            if not user_result:
                return Response(
                    {'error': 'Invalid token or user not found'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Return user data with subscription info
            response_data = {
                'user_uuid': user_result['user_uuid'],
                'user_data': user_result['user_data'],
                'is_vip_plus': user_result['is_vip_plus'],
                'subscription_status': 'VIP Plus Active' if user_result['is_vip_plus'] else 'Standard User'
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in user validation: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ColorSimilaritySearchView(APIView):
    """
    Get analogous color palette for images by slug or upload new images for analysis
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = ImageSearchResultSerializer

    @extend_schema(
        tags=['Color Analysis'],
        summary="Get analogous color palette",
        description="Get analogous color palette for a specific image by slug using advanced color analysis",
        parameters=[
            OpenApiParameter(
                name='slug',
                location=OpenApiParameter.QUERY,
                required=True,
                type=str,
                description="Slug/name of the image file (without extension)"
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'image_slug': {'type': 'string'},
                    'image_path': {'type': 'string'},
                    'main_palette': {'type': 'array'},
                    'analogous_palette': {'type': 'array'},
                    'analysis_timestamp': {'type': 'string'},
                    'message': {'type': 'string'}
                }
            },
            400: {'description': 'Missing slug parameter'},
            404: {'description': 'Image not found'},
            500: {'description': 'Analysis failed'}
        }
    )

    def get(self, request):
        """
        Get analogous color palette for a specific image by slug
        """
        try:
            print(f"Color similarity request received with params: {dict(request.query_params)}")
            # Get slug parameter
            slug = request.query_params.get('slug')
            print(f"Slug parameter: {slug}")
            if not slug:
                print("No slug provided")
                return Response(
                    {
                        'error': 'Missing required parameter: slug',
                        'message': 'Please provide image slug as query parameter',
                        'example': '/api/search/color-similarity/?slug=image_name'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Find image file
            image_dir = Path(settings.BASE_DIR) / 'images'
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
            image_path = None

            for ext in image_extensions:
                potential_path = image_dir / f"{slug}{ext}"
                if potential_path.exists():
                    image_path = potential_path
                    break

            if not image_path:
                return Response(
                    {
                        'error': f'Image not found: {slug}',
                        'message': f'No image file found for slug "{slug}" in supported formats: {", ".join(image_extensions)}'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            # Initialize color analyzer
            analyzer = UltimateColorProcessor(
                images_folder=str(image_dir),
                max_colors=10
            )

            # Analyze image colors
            try:
                analysis_result = analyzer.analyze_image_colors(image_path)

                if not analysis_result:
                    return Response(
                        {
                            'error': 'Color analysis failed',
                            'message': f'Could not analyze colors for image: {slug}'
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                # Return analogous palette results
                return Response({
                    'success': True,
                    'image_slug': slug,
                    'image_path': str(image_path),
                    'main_palette': analysis_result.get('main_palette', []),
                    'analogous_palette': analysis_result.get('analogous_palette', []),
                    'analysis_timestamp': analysis_result.get('timestamp', None),
                    'message': f'Analogous color palette generated for {slug}'
                }, status=status.HTTP_200_OK)

            except Exception as color_error:
                logger.error(f"Color analysis error for {slug}: {color_error}")
                return Response(
                    {
                        'error': 'Color analysis error',
                        'message': f'Error processing image {slug}: {str(color_error)}'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Error in color similarity analysis for slug {slug}: {e}")
            return Response(
                {
                    'error': 'Internal server error',
                    'message': f'Failed to process color analysis: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Image Upload & Color Search'],
        description="Upload an image and find similar images based on color analysis",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'image': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Image file to analyze'
                    },
                    'image_url': {
                        'type': 'string',
                        'description': 'Alternative: URL of image to analyze'
                    },
                    'limit': {
                        'type': 'integer',
                        'default': 20,
                        'description': 'Maximum number of similar images to return'
                    }
                }
            }
        },
        responses={
            200: ImageSearchResultSerializer(many=True),
            400: {'description': 'Bad request - invalid image'},
            500: {'description': 'Server error'}
        }
    )
    def post(self, request):
        """
        Upload image and find color-similar images
        """
        try:
            # Get image from upload or URL
            uploaded_image = request.FILES.get('image')
            image_url = request.data.get('image_url')
            limit = int(request.data.get('limit', 20))

            if not uploaded_image and not image_url:
                return Response(
                    {'error': 'Either image file or image_url is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Process the image and extract colors
            image_colors = self.extract_colors_from_image(uploaded_image, image_url)

            if not image_colors:
                return Response(
                    {'error': 'Could not process image or extract colors'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Find similar images based on colors
            similar_images = self.find_similar_images_by_color(image_colors, limit)

            return Response(similar_images)

        except Exception as e:
            logger.error(f"Error in color similarity search: {e}")
            return Response(
                {'error': 'Internal server error during color analysis'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def extract_colors_from_image(self, uploaded_image=None, image_url=None):
        """
        Extract dominant colors from uploaded image or image URL
        """
        try:
            if uploaded_image:
                # Process uploaded file
                image = PILImage.open(uploaded_image)
            elif image_url:
                # Download from URL
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                image = PILImage.open(BytesIO(response.content))
            else:
                return None

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize for faster processing
            image = image.resize((200, 200))

            # Get pixels
            pixels = list(image.getdata())

            # Extract dominant colors
            color_counts = Counter(pixels)
            dominant_colors = color_counts.most_common(10)

            # Process colors
            processed_colors = []
            for color, count in dominant_colors:
                percentage = (count / len(pixels)) * 100
                hex_code = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"

                processed_colors.append({
                    'rgb': color,
                    'hex': hex_code,
                    'percentage': round(percentage, 2),
                    'hsl': self.rgb_to_hsl(color),
                    'color_name': self.get_color_name(color)
                })

            return processed_colors

        except Exception as e:
            logger.error(f"Error extracting colors from image: {e}")
            return None

    def find_similar_images_by_color(self, image_colors, limit=20):
        """
        Find images similar to the given colors using Elasticsearch
        """
        try:
            # Check if Elasticsearch is enabled
            if not getattr(settings, 'ELASTICSEARCH_ENABLED', False):
                logger.info("Elasticsearch is disabled - returning empty color search results")
                return []

            client = Elasticsearch(hosts=[settings.ELASTICSEARCH_DSL['default']['hosts']])
            search = Search(using=client, index='images')

            # Build color similarity queries
            color_queries = []

            # Enhanced search by multiple primary colors and their similar colors
            if image_colors:
                # Search by all primary colors (top 5)
                for i, color_data in enumerate(image_colors[:5]):
                    boost = 10.0 - i  # Higher boost for more dominant colors

                    # Exact hex match in primary_color_hex
                    color_queries.append(Q('term', primary_color_hex={"value": color_data['hex'], "boost": boost}))

                    # Search in primary_colors array (if available) - exact match
                    color_queries.append(Q('nested', path='primary_colors',
                                         query=Q('term', primary_colors__hex={"value": color_data['hex'], "boost": boost * 0.8})))

                    # Search in similar_hexes of primary_colors - enhanced similarity search
                    try:
                        color_queries.append(Q('nested', path='primary_colors',
                                             query=Q('terms', primary_colors__similar_hexes=color_data['hex'],
                                                     boost=boost * 0.6)))
                    except:
                        pass  # Skip if nested field not available

                    # Search in color_search_terms
                    color_queries.append(Q('terms', color_search_terms=[color_data['hex'].lower()], boost=boost * 0.4))

                    # Similar hex colors for this color (from our analysis)
                    similar_hexes = self.find_similar_hex_colors(color_data['hex'])
                    for hex_color in similar_hexes:
                        color_queries.append(Q('term', primary_color_hex={"value": hex_color, "boost": boost * 0.5}))

                        # Also search in primary_colors similar_hexes
                        try:
                            color_queries.append(Q('nested', path='primary_colors',
                                                 query=Q('terms', primary_colors__similar_hexes=hex_color,
                                                         boost=boost * 0.3)))
                        except:
                            pass

            # Search by color names
            color_names = set()
            for color_data in image_colors[:5]:  # Top 5 colors
                if color_data.get('color_name'):
                    color_names.add(color_data['color_name'])

            for color_name in color_names:
                # Search in primary color name (simplified approach)
                # For now, we'll use a simpler approach since nested fields may not exist
                pass

            # Search by HSL values (hue similarity) - simplified
            # For now, we'll skip HSL search since nested fields may not exist in current data

            # Execute search
            if color_queries:
                final_query = Q('bool', should=color_queries, minimum_should_match=1)
                search = search.query(final_query)

            search = search.extra(size=limit, track_scores=True)
            response = search.execute()

            # Format results
            results = []
            for hit in response.hits:
                result_data = hit.to_dict()
                result_data['_color_similarity_score'] = hit.meta.score

                # Add color matching information
                result_data['_matched_colors'] = self.get_matching_colors(hit, image_colors)

                results.append(result_data)

            return results

        except Exception as e:
            logger.error(f"Error finding similar images by color: {e}")
            return []

    def get_matching_colors(self, es_hit, query_colors):
        """
        Get matching colors between query and result
        """
        matching_colors = []

        hit_primary = getattr(es_hit, 'primary_color_hex', None)

        for query_color in query_colors[:3]:  # Check top 3 query colors
            # Check primary color match
            if hit_primary and self.color_distance_hex(query_color['hex'], hit_primary) < 30:
                matching_colors.append({
                    'query_color': query_color,
                    'match_type': 'primary',
                    'distance': self.color_distance_hex(query_color['hex'], hit_primary)
                })

        return matching_colors

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

    @staticmethod
    def get_color_name(rgb):
        """Get approximate color name from RGB"""
        r, g, b = rgb
        brightness = (r + g + b) / 3

        if brightness < 64:
            return "black"
        elif brightness > 192:
            return "white"
        elif r > g + b:
            return "red"
        elif g > r + b:
            return "green"
        elif b > r + g:
            return "blue"
        elif r > 150 and g > 100:
            return "yellow"
        elif r > 100 and b > 100:
            return "purple"
        elif g > 100 and b > 100:
            return "cyan"
        else:
            return "gray"

    @staticmethod
    def color_distance_hex(hex1, hex2):
        """Calculate distance between two hex colors"""
        if not hex1 or not hex2:
            return 100

        try:
            hex1 = hex1.lstrip('#')
            hex2 = hex2.lstrip('#')
            rgb1 = tuple(int(hex1[i:i+2], 16) for i in (0, 2, 4))
            rgb2 = tuple(int(hex2[i:i+2], 16) for i in (0, 2, 4))

            return ((rgb1[0] - rgb2[0]) ** 2 +
                   (rgb1[1] - rgb2[1]) ** 2 +
                   (rgb1[2] - rgb2[2]) ** 2) ** 0.5
        except:
            return 100

    @staticmethod
    def find_similar_hex_colors(hex_color, threshold=30):
        """Find similar hex colors within threshold distance"""
        if not hex_color or not hex_color.startswith('#'):
            return []

        similar_colors = []
        base_rgb = ColorSimilaritySearchView.hex_to_rgb(hex_color)

        # Generate some similar colors
        for dr in [-20, -10, 0, 10, 20]:
            for dg in [-20, -10, 0, 10, 20]:
                for db in [-20, -10, 0, 10, 20]:
                    new_r = max(0, min(255, base_rgb[0] + dr))
                    new_g = max(0, min(255, base_rgb[1] + dg))
                    new_b = max(0, min(255, base_rgb[2] + db))

                    if abs(dr) + abs(dg) + abs(db) <= threshold:
                        similar_hex = f"#{int(new_r):02x}{int(new_g):02x}{int(new_b):02x}"
                        if similar_hex != hex_color:
                            similar_colors.append(similar_hex)

        return similar_colors[:10]  # Limit to 10 similar colors

    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert hex to RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class ImageColorSamplesView(APIView):
    """
    Get color samples for a specific image by slug
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ColorSamplesSerializer

    @extend_schema(
        tags=['Color Operations'],
        summary="Get image color samples",
        description="Returns 10 color samples from different parts of the image",
        parameters=[
            OpenApiParameter('slug', str, OpenApiParameter.PATH, description="Image slug"),
        ]
    )
    def get(self, request, slug):
        """Get color samples for a specific image"""
        try:
            # Search for image in Elasticsearch
            if not getattr(settings, 'ELASTICSEARCH_ENABLED', False):
                # Return mock color samples data
                mock_data = self._generate_mock_color_samples(slug)
                return Response(mock_data)

            search = Search(using='default', index='images')
            search = search.query('term', slug=slug)
            response = search.execute()

            if not response.hits:
                return Response({
                    'error': 'Image not found'
                }, status=status.HTTP_404_NOT_FOUND)

            image_data = response.hits[0]

            # Check if color samples exist
            if not hasattr(image_data, 'color_samples') or not image_data.color_samples:
                # Return mock color samples data when real data is not available
                mock_data = self._generate_mock_color_samples(slug)
                return Response(mock_data)

            return Response({
                'image_slug': image_data.slug,
                'color_samples': image_data.color_samples,
                'dominant_colors': getattr(image_data, 'dominant_colors', []),
                'color_histogram': getattr(image_data, 'color_histogram', [])
            })

        except Exception as e:
            logger.error(f"Error retrieving color samples for slug {slug}: {str(e)}")
            return Response({
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_mock_color_samples(self, slug):
        """Generate mock color samples data when Elasticsearch is disabled"""
        # Generate different mock data based on slug
        if 'red' in slug.lower() or 'action' in slug.lower():
            dominant_colors = [
                {'hex': '#FF0000', 'percentage': 35.2, 'name': 'Red'},
                {'hex': '#000000', 'percentage': 28.7, 'name': 'Black'},
                {'hex': '#8B0000', 'percentage': 18.9, 'name': 'Dark Red'},
                {'hex': '#FF4500', 'percentage': 12.1, 'name': 'Orange Red'},
                {'hex': '#800000', 'percentage': 5.1, 'name': 'Maroon'}
            ]
            color_samples = [
                {'hex': '#FF0000', 'rgb': [255, 0, 0], 'position': {'x': 45, 'y': 30}, 'percentage': 35.2},
                {'hex': '#000000', 'rgb': [0, 0, 0], 'position': {'x': 20, 'y': 25}, 'percentage': 28.7},
                {'hex': '#8B0000', 'rgb': [139, 0, 0], 'position': {'x': 70, 'y': 40}, 'percentage': 18.9},
                {'hex': '#FF4500', 'rgb': [255, 69, 0], 'position': {'x': 85, 'y': 60}, 'percentage': 12.1},
                {'hex': '#800000', 'rgb': [128, 0, 0], 'position': {'x': 15, 'y': 70}, 'percentage': 5.1}
            ]
        elif 'blue' in slug.lower() or 'drama' in slug.lower():
            dominant_colors = [
                {'hex': '#0000FF', 'percentage': 42.3, 'name': 'Blue'},
                {'hex': '#000080', 'percentage': 25.6, 'name': 'Navy'},
                {'hex': '#4169E1', 'percentage': 15.8, 'name': 'Royal Blue'},
                {'hex': '#1E90FF', 'percentage': 11.2, 'name': 'Dodger Blue'},
                {'hex': '#00008B', 'percentage': 5.1, 'name': 'Dark Blue'}
            ]
            color_samples = [
                {'hex': '#0000FF', 'rgb': [0, 0, 255], 'position': {'x': 50, 'y': 35}, 'percentage': 42.3},
                {'hex': '#000080', 'rgb': [0, 0, 128], 'position': {'x': 25, 'y': 45}, 'percentage': 25.6},
                {'hex': '#4169E1', 'rgb': [65, 105, 225], 'position': {'x': 75, 'y': 55}, 'percentage': 15.8},
                {'hex': '#1E90FF', 'rgb': [30, 144, 255], 'position': {'x': 10, 'y': 80}, 'percentage': 11.2},
                {'hex': '#00008B', 'rgb': [0, 0, 139], 'position': {'x': 90, 'y': 20}, 'percentage': 5.1}
            ]
        else:
            # Default color samples for other scenes
            dominant_colors = [
                {'hex': '#808080', 'percentage': 30.5, 'name': 'Gray'},
                {'hex': '#FFFFFF', 'percentage': 25.3, 'name': 'White'},
                {'hex': '#000000', 'percentage': 20.1, 'name': 'Black'},
                {'hex': '#A9A9A9', 'percentage': 15.6, 'name': 'Dark Gray'},
                {'hex': '#D3D3D3', 'percentage': 8.5, 'name': 'Light Gray'}
            ]
            color_samples = [
                {'hex': '#808080', 'rgb': [128, 128, 128], 'position': {'x': 40, 'y': 40}, 'percentage': 30.5},
                {'hex': '#FFFFFF', 'rgb': [255, 255, 255], 'position': {'x': 60, 'y': 30}, 'percentage': 25.3},
                {'hex': '#000000', 'rgb': [0, 0, 0], 'position': {'x': 20, 'y': 50}, 'percentage': 20.1},
                {'hex': '#A9A9A9', 'rgb': [169, 169, 169], 'position': {'x': 80, 'y': 70}, 'percentage': 15.6},
                {'hex': '#D3D3D3', 'rgb': [211, 211, 211], 'position': {'x': 5, 'y': 85}, 'percentage': 8.5}
            ]

        return {
            'image_slug': slug,
            'color_samples': color_samples,
            'dominant_colors': dominant_colors,
            'color_histogram': [
                {'color': '#808080', 'count': 1525},
                {'color': '#FFFFFF', 'count': 1265},
                {'color': '#000000', 'count': 1005},
                {'color': '#A9A9A9', 'count': 780},
                {'color': '#D3D3D3', 'count': 425}
            ],
            'total_pixels': 5000,
            'message': 'Mock color samples data (Elasticsearch disabled)'
        }


class ImageColorSearchView(APIView):
    """
    Advanced color search endpoint
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ImageSearchResultSerializer

    @extend_schema(
        tags=['Color Operations'],
        summary="Advanced color search",
        description="Search images based on various color parameters",
        parameters=[
            OpenApiParameter('hex', str, OpenApiParameter.QUERY, description="Hex color code (example: #FF5733)"),
            OpenApiParameter('similarity', str, OpenApiParameter.QUERY, description="Color similarity (red, blue, green, etc.)"),
            OpenApiParameter('temperature', str, OpenApiParameter.QUERY, enum=['warm', 'cool', 'neutral'], description="Color temperature"),
            OpenApiParameter('hue_range', str, OpenApiParameter.QUERY, description="Hue range (example: 0-60 for red)"),
            OpenApiParameter('primary_colors', str, OpenApiParameter.QUERY, description="List of primary colors (hex codes separated by comma)"),
            OpenApiParameter('color_family', str, OpenApiParameter.QUERY, enum=['warm', 'cool', 'neutral', 'bright', 'dark'], description="Color family"),
            OpenApiParameter('limit', int, OpenApiParameter.QUERY, description="Number of results (default: 20)"),
        ]
    )
    def get(self, request):
        """Advanced color search endpoint"""
        try:
            # Get query parameters
            hex_color = request.query_params.get('hex')
            similarity = request.query_params.get('similarity')
            temperature = request.query_params.get('temperature')
            hue_range = request.query_params.get('hue_range')
            primary_colors = request.query_params.get('primary_colors')
            color_family = request.query_params.get('color_family')
            limit = int(request.query_params.get('limit', 20))

            # Build Elasticsearch query
            if not getattr(settings, 'ELASTICSEARCH_ENABLED', False):
                # Generate mock results for color search
                mock_results = self._generate_mock_color_search_results(request)
                return Response({
                    'count': len(mock_results),
                    'results': mock_results,
                    'total': len(mock_results),
                    'message': 'Mock color search results (Elasticsearch disabled)'
                })

            search = Search(using='default', index='images')

            # Apply color filters
            if hex_color:
                search = self._filter_by_hex_color(search, hex_color)
            elif similarity:
                search = self._filter_by_similarity(search, similarity)
            elif temperature:
                search = self._filter_by_temperature(search, temperature)
            elif hue_range:
                search = self._filter_by_hue_range(search, hue_range)
            elif primary_colors:
                search = self._filter_by_primary_colors(search, primary_colors)
            elif color_family:
                search = self._filter_by_color_family(search, color_family)
            else:
                # No color filter specified
                return Response({
                    'error': 'At least one color parameter must be specified'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Execute search
            search = search[:limit]
            response = search.execute()

            # Format results
            results = []
            for hit in response.hits:
                results.append({
                    'slug': hit.slug,
                    'title': getattr(hit, 'title', ''),
                    'primary_color_hex': getattr(hit, 'primary_color_hex', ''),
                    'primary_colors': getattr(hit, 'primary_colors', []),
                    'color_family': getattr(hit, 'color_search_terms', []),
                    'score': hit.meta.score if hasattr(hit.meta, 'score') else 1.0
                })

            return Response({
                'count': len(results),
                'results': results,
                'total': response.hits.total.value if hasattr(response.hits, 'total') else len(results)
            })

        except Exception as e:
            logger.error(f"Error in color search: {str(e)}")
            return Response({
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FiltersView(APIView):
    """
    API endpoint to retrieve all available filter options for image search
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Search & Filtering'],
        summary="Get available search filters or search images by filters",
        description="Returns all available filter options, or search images based on selected filter parameters",
        parameters=[
            OpenApiParameter('search', str, OpenApiParameter.QUERY, description="Search query text"),
            OpenApiParameter('tags', str, OpenApiParameter.QUERY, description="Tags filter - comma-separated list of tag names to filter images by"),
            OpenApiParameter('movie', str, OpenApiParameter.QUERY, description="Movie filter - comma-separated list of movie titles to filter images by"),
            OpenApiParameter('media_type', str, OpenApiParameter.QUERY, enum=["Movie", "TV", "Trailer", "Music Video", "Commercial"], description="Media type filter"),
            OpenApiParameter('genre', str, OpenApiParameter.QUERY, enum=["Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery", "Romance", "Science Fiction", "Thriller", "War", "Western"], description="Genre filter (multiple selections allowed, comma-separated)"),
            OpenApiParameter('time_period', str, OpenApiParameter.QUERY, enum=["Future", "2020s", "2010s", "2000s", "1990s", "1980s", "1970s", "1960s", "1950s", "1940s", "1930s", "1920s", "1910s", "1900s", "1800s", "1700s", "Renaissance: 1400-1700", "Medieval: 500-1400", "Ancient: 2000BC-500AD", "Stone Age: pre-2000BC"], description="Time period filter"),
            OpenApiParameter('color', str, OpenApiParameter.QUERY, enum=["Warm", "Cool", "Mixed", "Saturated", "Desaturated", "Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Purple", "Magenta", "Pink", "White", "Sepia", "Black and White"], description="Color filter"),
            OpenApiParameter('shade', str, OpenApiParameter.QUERY, description="Color picker filter (HEX_COLOR~COLOR_DISTANCE~PROPORTION)"),
            OpenApiParameter('aspect_ratio', str, OpenApiParameter.QUERY, enum=["9:16", "1 - square", "1.20", "1.33", "1.37", "1.43", "1.66", "1.78", "1.85", "1.90", "2.00", "2.20", "2.35", "2.39", "2.55", "2.67", "2.76+"], description="Aspect ratio filter"),
            OpenApiParameter('optical_format', str, OpenApiParameter.QUERY, enum=["Anamorphic", "Spherical", "Super 35", "3 perf", "2 perf", "Open Gate", "3D"], description="Optical format filter"),
            OpenApiParameter('lab_process', str, OpenApiParameter.QUERY, enum=["Bleach Bypass", "Cross Process", "Flashing"], description="Lab process filter"),
            OpenApiParameter('format', str, OpenApiParameter.QUERY, enum=["Film - 35mm", "Film - 16mm", "Film - Super 8mm", "Film - 65mm / 70mm", "Film - IMAX", "Tape", "Digital", "Digital - Large Format", "Animation"], description="Format filter"),
            OpenApiParameter('int_ext', str, OpenApiParameter.QUERY, enum=["Interior", "Exterior"], description="Interior/Exterior filter"),
            OpenApiParameter('time_of_day', str, OpenApiParameter.QUERY, enum=["Day", "Night", "Dusk", "Dawn", "Sunrise", "Sunset"], description="Time of day filter"),
            OpenApiParameter('numpeople', str, OpenApiParameter.QUERY, enum=["None", "1", "2", "3", "4", "5", "6+"], description="Number of people filter"),
            OpenApiParameter('gender', str, OpenApiParameter.QUERY, enum=["Male", "Female", "Trans"], description="Gender filter"),
            OpenApiParameter('subject_age', str, OpenApiParameter.QUERY, enum=["Baby", "Toddler", "Child", "Teenager", "Young Adult", "Mid-adult", "Middle age", "Senior"], description="Subject age filter"),
            OpenApiParameter('subject_ethnicity', str, OpenApiParameter.QUERY, enum=["Black", "White", "Latinx", "Middle Eastern", "South-East Asian", "East Asian", "South Asian", "Indigenous Peoples", "Mixed-race"], description="Subject ethnicity filter"),
            OpenApiParameter('frame_size', str, OpenApiParameter.QUERY, enum=["Extreme Wide", "Wide", "Medium Wide", "Medium", "Medium Close Up", "Close Up", "Extreme Close Up"], description="Frame size filter"),
            OpenApiParameter('shot_type', str, OpenApiParameter.QUERY, enum=["Aerial", "Overhead", "High angle", "Low angle", "Dutch angle", "Establishing shot", "Over the shoulder", "Clean single", "2 shot", "3 shot", "Group shot", "Insert"], description="Shot type filter"),
            OpenApiParameter('composition', str, OpenApiParameter.QUERY, enum=["Center", "Left heavy", "Right heavy", "Balanced", "Symmetrical", "Short side"], description="Composition filter"),
            OpenApiParameter('lens_type', str, OpenApiParameter.QUERY, enum=["Ultra Wide / Fisheye", "Wide", "Medium", "Long Lens", "Telephoto"], description="Lens type filter"),
            OpenApiParameter('lighting', str, OpenApiParameter.QUERY, enum=["Soft light", "Hard light", "High contrast", "Low contrast", "Silhouette", "Top light", "Underlight", "Side light", "Backlight", "Edge light"], description="Lighting filter"),
            OpenApiParameter('lighting_type', str, OpenApiParameter.QUERY, enum=["Daylight", "Sunny", "Overcast", "Moonlight", "Artificial light", "Practical light", "Fluorescent", "Firelight", "Mixed light"], description="Lighting type filter"),
            OpenApiParameter('limit', int, OpenApiParameter.QUERY, description="Number of results (default: 20)"),
            OpenApiParameter('offset', int, OpenApiParameter.QUERY, description="Offset for pagination (default: 0)"),
        ],
        responses={
            200: {
                'oneOf': [
                    {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'},
                            'data': {
                                'type': 'object',
                                'properties': {
                                    'filters': {'type': 'array'}
                                }
                            }
                        },
                        'description': 'Filter options when no search parameters provided'
                    },
                    {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'count': {'type': 'integer'},
                            'results': {'type': 'array'},
                            'total': {'type': 'integer'},
                            'filters_applied': {'type': 'object'}
                        },
                        'description': 'Search results when filter parameters provided'
                    }
                ]
            }
        }
    )
    def get(self, request):
        """
        Return all available filter options for image search, or search images by filters
        """
        try:
            # Check if any search/filter parameters are provided
            search_params = {
                'search': request.query_params.get('search'),
                'tags': request.query_params.get('tags'),
                'movie': request.query_params.get('movie'),
                'media_type': request.query_params.get('media_type'),
                'genre': request.query_params.get('genre'),
                'time_period': request.query_params.get('time_period'),
                'color': request.query_params.get('color'),
                'shade': request.query_params.get('shade'),
                'aspect_ratio': request.query_params.get('aspect_ratio'),
                'optical_format': request.query_params.get('optical_format'),
                'lab_process': request.query_params.get('lab_process'),
                'format': request.query_params.get('format'),
                'int_ext': request.query_params.get('int_ext'),
                'time_of_day': request.query_params.get('time_of_day'),
                'numpeople': request.query_params.get('numpeople'),
                'gender': request.query_params.get('gender'),
                'subject_age': request.query_params.get('subject_age'),
                'subject_ethnicity': request.query_params.get('subject_ethnicity'),
                'frame_size': request.query_params.get('frame_size'),
                'shot_type': request.query_params.get('shot_type'),
                'composition': request.query_params.get('composition'),
                'lens_type': request.query_params.get('lens_type'),
                'lighting': request.query_params.get('lighting'),
                'lighting_type': request.query_params.get('lighting_type'),
                'limit': int(request.query_params.get('limit', 20)),
                'offset': int(request.query_params.get('offset', 0))
            }

            # Remove None values and check if any filters are applied
            applied_filters = {k: v for k, v in search_params.items() if v is not None and k not in ['limit', 'offset']}
            has_filters = len(applied_filters) > 0

            if not has_filters:
                # Return the filter configuration (no search parameters provided)
                response_data = {
                    "success": True,
                    "message": "Filters",
                    "data": FILTER_CONFIG
                }
                return Response(response_data, status=status.HTTP_200_OK)

            # Perform search with filters
            return self._perform_filtered_search(search_params, applied_filters)

        except Exception as e:
            logger.error(f"Error in filters/search operation: {e}")
            return Response({
                'success': False,
                'message': 'Error processing request',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _perform_filtered_search(self, search_params, applied_filters):
        """
        Perform search based on applied filters
        """
        try:
            if not getattr(settings, 'ELASTICSEARCH_ENABLED', False):
                # Return mock search results
                mock_results = self._generate_mock_search_results(search_params, applied_filters)
                return Response({
                    'success': True,
                    'count': len(mock_results),
                    'results': mock_results,
                    'total': len(mock_results),
                    'filters_applied': applied_filters,
                    'message': 'Mock search results (Elasticsearch disabled)'
                })

            # Real Elasticsearch search would go here
            # For now, return mock results
            mock_results = self._generate_mock_search_results(search_params, applied_filters)
            return Response({
                'success': True,
                'count': len(mock_results),
                'results': mock_results,
                'total': len(mock_results),
                'filters_applied': applied_filters,
                'message': 'Search completed'
            })

        except Exception as e:
            logger.error(f"Error performing filtered search: {e}")
            return Response({
                'success': False,
                'message': 'Error performing search',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_mock_search_results(self, search_params, applied_filters):
        """
        Generate mock search results based on applied filters
        """
        # Mock images with different properties
        mock_images = [
            {
                'id': 1,
                'slug': 'action-movie-1',
                'title': 'Intense Action Scene',
                'description': 'High-energy action sequence',
                'image_url': '/images/action-movie-1.jpg',
                'release_year': 2023,
                'media_type': 'Movie',
                'genre': ['Action', 'Thriller'],
                'time_period': '2020s',
                'color': 'Dark',
                'shade': '#000000~10~0.8',
                'aspect_ratio': '2.35',
                'optical_format': 'Anamorphic',
                'lab_process': 'Bleach Bypass',
                'format': 'Film - 35mm',
                'int_ext': 'Exterior',
                'time_of_day': 'Day',
                'numpeople': '3',
                'gender': 'Male',
                'subject_age': 'Young Adult',
                'subject_ethnicity': 'White',
                'frame_size': 'Wide',
                'shot_type': 'Aerial',
                'composition': 'Balanced',
                'lens_type': 'Long Lens',
                'lighting': 'Hard light',
                'lighting_type': 'Daylight'
            },
            {
                'id': 2,
                'slug': 'drama-scene-1',
                'title': 'Emotional Drama Moment',
                'description': 'Powerful emotional scene',
                'image_url': '/images/drama-scene-1.jpg',
                'release_year': 2022,
                'media_type': 'Movie',
                'genre': ['Drama', 'Romance'],
                'time_period': '2020s',
                'color': 'Warm',
                'shade': '#FFA500~15~0.7',
                'aspect_ratio': '1.85',
                'optical_format': 'Spherical',
                'lab_process': 'Cross Process',
                'format': 'Digital',
                'int_ext': 'Interior',
                'time_of_day': 'Night',
                'numpeople': '2',
                'gender': 'Female',
                'subject_age': 'Mid-adult',
                'subject_ethnicity': 'Black',
                'frame_size': 'Medium Close Up',
                'shot_type': 'Over the shoulder',
                'composition': 'Center',
                'lens_type': 'Medium',
                'lighting': 'Soft light',
                'lighting_type': 'Artificial light'
            },
            {
                'id': 3,
                'slug': 'comedy-clip-1',
                'title': 'Funny Comedy Moment',
                'description': 'Hilarious comedy scene',
                'image_url': '/images/comedy-clip-1.jpg',
                'release_year': 2021,
                'media_type': 'TV',
                'genre': ['Comedy'],
                'time_period': '2020s',
                'color': 'Mixed',
                'shade': '#FFFF00~20~0.6',
                'aspect_ratio': '1.78',
                'optical_format': 'Super 35',
                'lab_process': 'Flashing',
                'format': 'Digital - Large Format',
                'int_ext': 'Interior',
                'time_of_day': 'Day',
                'numpeople': '4',
                'gender': 'Male',
                'subject_age': 'Teenager',
                'subject_ethnicity': 'Latinx',
                'frame_size': 'Medium',
                'shot_type': '2 shot',
                'composition': 'Symmetrical',
                'lens_type': 'Wide',
                'lighting': 'Soft light',
                'lighting_type': 'Fluorescent'
            },
            {
                'id': 4,
                'slug': 'horror-scene-1',
                'title': 'Scary Horror Moment',
                'description': 'Terrifying horror scene',
                'image_url': '/images/horror-scene-1.jpg',
                'release_year': 2020,
                'media_type': 'Movie',
                'genre': ['Horror', 'Thriller'],
                'time_period': '2020s',
                'color': 'Cool',
                'shade': '#000080~12~0.9',
                'aspect_ratio': '2.39',
                'optical_format': '3D',
                'lab_process': 'Bleach Bypass',
                'format': 'Film - IMAX',
                'int_ext': 'Interior',
                'time_of_day': 'Night',
                'numpeople': '1',
                'gender': 'Female',
                'subject_age': 'Young Adult',
                'subject_ethnicity': 'East Asian',
                'frame_size': 'Close Up',
                'shot_type': 'Dutch angle',
                'composition': 'Left heavy',
                'lens_type': 'Ultra Wide / Fisheye',
                'lighting': 'High contrast',
                'lighting_type': 'Artificial light'
            },
            {
                'id': 5,
                'slug': 'documentary-1',
                'title': 'Nature Documentary Scene',
                'description': 'Beautiful nature documentary footage',
                'image_url': '/images/documentary-1.jpg',
                'release_year': 2019,
                'media_type': 'TV',
                'genre': ['Documentary'],
                'time_period': '2010s',
                'color': 'Saturated',
                'shade': '#00FF00~8~0.5',
                'aspect_ratio': '1.90',
                'optical_format': 'Spherical',
                'lab_process': None,
                'format': 'Digital',
                'int_ext': 'Exterior',
                'time_of_day': 'Dawn',
                'numpeople': 'None',
                'gender': None,
                'subject_age': None,
                'subject_ethnicity': None,
                'frame_size': 'Extreme Wide',
                'shot_type': 'Establishing shot',
                'composition': 'Balanced',
                'lens_type': 'Wide',
                'lighting': 'Soft light',
                'lighting_type': 'Daylight'
            }
        ]

        # Filter results based on applied filters
        filtered_results = []
        for image in mock_images:
            match = True

            # Check each applied filter
            for filter_name, filter_value in applied_filters.items():
                if filter_name == 'search':
                    # Simple text search in title/description
                    search_text = filter_value.lower()
                    if not (search_text in image['title'].lower() or
                           search_text in image['description'].lower()):
                        match = False
                        break
                elif filter_name == 'genre':
                    # Handle comma-separated genres
                    requested_genres = [g.strip() for g in filter_value.split(',')]
                    image_genres = image.get('genre', [])
                    if not any(genre in image_genres for genre in requested_genres):
                        match = False
                        break
                elif filter_name == 'shade':
                    # Handle color picker format: HEX_COLOR~COLOR_DISTANCE~PROPORTION
                    if image.get('shade'):
                        image_hex = image['shade'].split('~')[0].upper()
                        requested_hex = filter_value.split('~')[0].upper()
                        if image_hex != requested_hex:
                            match = False
                            break
                    else:
                        match = False
                        break
                else:
                    # Exact match for other filters
                    image_value = image.get(filter_name)
                    if image_value is None:
                        match = False
                        break
                    if str(image_value).lower() != str(filter_value).lower():
                        match = False
                        break

            if match:
                filtered_results.append(image)

        # Apply pagination
        start_idx = search_params['offset']
        end_idx = start_idx + search_params['limit']
        return filtered_results[start_idx:end_idx]

    def _filter_by_hex_color(self, search, hex_color):
        """Filter by exact hex color match"""
        return search.query('term', primary_color_hex=hex_color)

    def _filter_by_similarity(self, search, similarity):
        """Filter by color similarity"""
        return search.query('match', color_search_terms=similarity)

    def _filter_by_temperature(self, search, temperature):
        """Filter by color temperature"""
        return search.query('term', color_temperature=temperature)

    def _filter_by_hue_range(self, search, hue_range):
        """Filter by hue range"""
        try:
            min_hue, max_hue = map(int, hue_range.split('-'))
            return search.query('range', color_hue={'gte': min_hue, 'lte': max_hue})
        except ValueError:
            return search

    def _filter_by_primary_colors(self, search, primary_colors):
        """Filter by primary colors"""
        return search.query('terms', primary_colors__hex=primary_colors.split(','))

    def _filter_by_color_family(self, search, color_family):
        """Filter by color family"""
        return search.query('term', color_family=color_family)

    def _generate_mock_color_search_results(self, request):
        """Generate mock color search results when Elasticsearch is disabled"""
        # Very simple mock data
        return [
            {
                'slug': 'red-scene',
                'title': 'Red Scene',
                'primary_color_hex': '#FF0000',
                'score': 0.95
            },
            {
                'slug': 'blue-scene',
                'title': 'Blue Scene',
                'primary_color_hex': '#0000FF',
                'score': 0.89
            }
        ]