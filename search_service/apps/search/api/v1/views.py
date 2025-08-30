from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from elasticsearch_dsl import Q
from elasticsearch_dsl.search import Search
from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.search.documents import ImageDocument
from .serializers import ImageSearchResultSerializer
from apps.common.serializers import Error404Serializer

class SearchView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ImageSearchResultSerializer

    @extend_schema(
        tags=['Search Operations'],
        description="جستجوی پیشرفته و فیلتر کردن تصاویر از طریق موتور جستجوی Elasticsearch.",
        parameters=[
            OpenApiParameter('q', str, OpenApiParameter.QUERY, description="متن جستجوی آزاد در عنوان، توضیحات، فیلم و تگ‌ها."),
            OpenApiParameter('tags', str, OpenApiParameter.QUERY, description="فیلتر بر اساس یک یا چند تگ (با کاما جدا شوند). مثال: sci-fi,night"),
            OpenApiParameter('genre', str, OpenApiParameter.QUERY, enum=['action', 'drama', 'comedy', 'horror', 'sci_fi', 'documentary', 'hip_hop', 'car']),
            OpenApiParameter('color', str, OpenApiParameter.QUERY, enum=['warm', 'cool', 'neutral', 'monochrome', 'vibrant']),
            OpenApiParameter('shot_type', str, OpenApiParameter.QUERY, enum=['aerial', 'high_angle', 'low_angle', 'eye_level']),
            OpenApiParameter('time_of_day', str, OpenApiParameter.QUERY, enum=['day', 'night', 'dusk', 'dawn']),
            OpenApiParameter('frame_size', str, OpenApiParameter.QUERY, enum=['close', 'medium', 'wide']),
        ],
        responses={200: ImageSearchResultSerializer(many=True)}
    )
    def get(self, request):
        try:
            search = ImageDocument.search()
            
            # 1. جستجوی متنی (Full-text Search)
            query = request.GET.get('q')
            if query:
                search = search.query(
                    "multi_match", 
                    query=query, 
                    fields=['title', 'description', 'movie.title', 'tags.name'],
                    fuzziness="AUTO"
                )

            # 2. فیلترهای دقیق (Term-level Filters)
            term_filters = [
                'media_type', 'genre', 'color', 'aspect_ratio', 'optical_format',
                'format', 'interior_exterior', 'time_of_day', 'number_of_people',
                'gender', 'age', 'ethnicity', 'frame_size', 'shot_type',
                'composition', 'lens_size', 'lens_type', 'lighting',
                'lighting_type', 'camera_type', 'resolution', 'frame_rate'
            ]
            for field in term_filters:
                value = request.GET.get(field)
                if value:
                    search = search.filter('term', **{field: value})

            # 3. فیلتر تگ‌ها (Nested Filter)
            tags_query = request.GET.get('tags')
            if tags_query:
                tag_list = [tag.strip() for tag in tags_query.split(',')]
                for tag_name in tag_list:
                    search = search.filter('nested', path='tags', query=Q('term', tags__name=tag_name))

            response = search.execute()
            # نتایج از Elasticsearch دارای فیلد meta هستند که باید به سریالایزر ارسال شود
            serializer = self.serializer_class(response.hits, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SimilarImagesView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ImageSearchResultSerializer

    @extend_schema(
        tags=['Search Operations'],
        description="پیدا کردن تصاویر مشابه بر اساس ID یک تصویر.",
        responses={
            200: ImageSearchResultSerializer(many=True),
            404: Error404Serializer,
        }
    )
    def get(self, request, pk, *args, **kwargs):
        try:
            search_by_id = Search(index='images').query("term", id=pk)
            response = search_by_id.execute()

            if not response.hits:
                return Response({'detail': 'Image with the given ID not found.'}, status=status.HTTP_404_NOT_FOUND)

            source_image = response.hits[0]
            
            should_clauses = []
            important_fields = ['genre', 'color', 'lighting', 'shot_type', 'composition']

            for field in important_fields:
                if hasattr(source_image, field) and getattr(source_image, field):
                    should_clauses.append({'term': {field: getattr(source_image, field)}})
            
            if hasattr(source_image, 'tags') and source_image.tags:
                for tag in source_image.tags:
                    should_clauses.append({'nested': {'path': 'tags', 'query': {'term': {'tags.name': tag.name}}}})

            if not should_clauses:
                return Response([])

            similar_search = ImageDocument.search().query('bool', should=should_clauses, minimum_should_match=1).exclude('term', id=pk)
            similar_results = similar_search[:10].execute()

            serializer = self.serializer_class(similar_results.hits, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)